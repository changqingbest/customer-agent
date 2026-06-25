import copy
import re
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from customer_agent.config import get_settings
from customer_agent.knowledge_base_v2 import KnowledgeBase
from customer_agent.lead_extractor import detect_language, extract_lead_fields
from customer_agent.llm_v2 import LLMClient
from customer_agent.logger import append_jsonl, build_logger
from customer_agent.models import KnowledgeItem, RetrievalResult
from customer_agent.role_prompts_v2 import ROLE_DEFINITIONS
from customer_agent.sessions import SessionStore


class AgentState(TypedDict, total=False):
    session_id: str
    trace_id: str
    message: str
    visitor: dict[str, Any]
    language: str
    lead_fields: dict[str, Any]
    intents: set[str]
    role: str
    route_reason: str
    retrieved: list[RetrievalResult]
    selected_items: list[KnowledgeItem]
    answer: str
    confidence: float
    sources: list[dict[str, Any]]
    need_human: bool
    follow_up_questions: list[str]


class CustomerServiceAgent:
    _session_store = SessionStore()

    def __init__(self):
        self.initialization_error: str | None = None
        self.settings = get_settings()
        self.logger = build_logger(self.settings.app_log_path)
        try:
            self.kb = KnowledgeBase(self.settings.knowledge_path)
            self.llm = LLMClient(self.settings)
            self.graph = self._build_graph()
        except Exception as exc:
            self.initialization_error = f"{type(exc).__name__}: {exc}"
            self.kb = None
            self.llm = None
            self.graph = None
            self.logger.exception("CustomerServiceAgent initialization failed")

    def chat(self, session_id: str, message: str, visitor: dict[str, Any] | None = None) -> dict:
        trace_id = f"trace-{session_id}-{uuid.uuid4().hex[:10]}"
        visitor = visitor or {}
        raw_llm_output = ""
        errors: list[str] = []

        if self.initialization_error:
            response = self._error_response("AGENT_INIT_FAILED", trace_id, visitor, message)
            self._write_trace(trace_id, session_id, message, visitor, [], raw_llm_output, response, ["AGENT_INIT_FAILED"], True)
            return response

        if not message or not message.strip():
            language = detect_language(message or "")
            response = {
                "answer": "请发送你的产品、报价、物流或售后问题，我们会按对应角色处理。" if language == "zh" else "Please send your product, quotation, shipping, or support question.",
                "language": language,
                "route": "general",
                "confidence": 0.0,
                "sources": [],
                "need_human": True,
                "lead_fields": self._default_lead_fields(visitor),
                "follow_up_questions": ["你想咨询哪类产品？", "是否有图纸、样品或规格参数？"] if language == "zh" else ["What product are you looking for?", "Do you have drawings, samples, or specifications?"],
                "trace_id": trace_id,
                "error": {"code": "EMPTY_INPUT", "message": "Visitor message is empty."},
            }
            self._write_trace(trace_id, session_id, message, visitor, [], raw_llm_output, response, ["EMPTY_INPUT"], False)
            return response

        try:
            language = detect_language(message)
            lead_fields = self._session_store.merge(session_id, extract_lead_fields(message, visitor))
            intents = self._detect_intents(message, lead_fields)
            state = self.graph.invoke(
                {
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "message": message,
                    "visitor": visitor,
                    "language": language,
                    "lead_fields": lead_fields,
                    "intents": intents,
                }
            )
            payload = {
                "answer": state["answer"],
                "language": language,
                "route": state["role"],
                "confidence": state["confidence"],
                "sources": state["sources"],
                "need_human": state["need_human"],
                "lead_fields": copy.deepcopy(lead_fields),
                "follow_up_questions": state["follow_up_questions"],
                "trace_id": trace_id,
            }
            llm_response, raw_llm_output, degraded = self.llm.generate_structured_response(payload)
            response = self._sanitize(llm_response or payload)
            response["route"] = state["role"]
            if llm_response is None:
                errors.append("LLM_OUTPUT_INVALID")
            self._write_trace(trace_id, session_id, message, visitor, state.get("retrieved", []), raw_llm_output, response, errors, degraded)
            return response
        except Exception as exc:
            self.logger.exception("Chat processing failed")
            response = self._error_response("INTERNAL_ERROR", trace_id, visitor, message)
            self._write_trace(trace_id, session_id, message, visitor, [], str(exc), response, ["INTERNAL_ERROR"], True)
            return response

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("supervisor", self._supervisor)
        graph.add_node("sales", self._sales)
        graph.add_node("logistics", self._logistics)
        graph.add_node("support", self._support)
        graph.add_node("general", self._general)
        graph.set_entry_point("supervisor")
        graph.add_conditional_edges("supervisor", lambda state: state["role"], {key: key for key in ROLE_DEFINITIONS})
        for role in ROLE_DEFINITIONS:
            graph.add_edge(role, END)
        return graph.compile()

    def _supervisor(self, state: AgentState) -> AgentState:
        role = self._select_role(state["intents"])
        return {"role": role, "route_reason": ROLE_DEFINITIONS[role]["prompt"]}

    def _sales(self, state: AgentState) -> AgentState:
        retrieved = self._search(state)
        items = [result.item for result in retrieved]
        need_human = not retrieved or self._is_ambiguous(state["message"], state["lead_fields"])
        answer = self._compose_sales(state["language"], state["lead_fields"], state["intents"], items, need_human)
        return self._node_result(state, retrieved, items, answer, need_human)

    def _logistics(self, state: AgentState) -> AgentState:
        retrieved = self._search(state)
        items = [result.item for result in retrieved]
        qty = self._quantity_value(state["lead_fields"].get("quantity"))
        country = state["lead_fields"].get("country") or "目的国"
        country_label = self._country_label(country, state["language"])
        need_human = not state["lead_fields"].get("country") or qty is None
        if state["language"] == "zh":
            answer = f"物流这边先给你一个方向：发往{country_label}可以按快递、空运、海运三类方式比较。"
            answer += "如果是 500 个这类批量订单，通常先看海运是否更经济，再用空运或快递满足紧急交期。"
            answer += "准确估算还需要包装尺寸、毛重、是否到门以及期望到货时间。"
        else:
            answer = f"For shipping to {country}, we can compare express, air, and sea shipment based on package size, gross weight, urgency, and delivery terms."
            if qty and qty >= 100:
                answer += " For a larger batch, sea shipment is usually compared first, then air or express if timing is urgent."
        return self._node_result(state, retrieved, items, answer, need_human)

    def _support(self, state: AgentState) -> AgentState:
        if state["language"] == "zh":
            answer = "售后这边请先提供订单号、问题描述、受影响数量，以及现场照片或视频。尺寸不对时我们会先核对图纸/确认样、测量方式和公差，再判断补发、退换货或返工方案。"
        else:
            answer = "Please share the order number, issue description, affected quantity, and photos or video. We will check drawings, approved samples, measurement method, and tolerance before deciding replacement, return, or rework."
        return self._node_result(state, self._search(state), [], answer, True)

    def _general(self, state: AgentState) -> AgentState:
        if state["language"] == "zh":
            answer = "你好，请告诉我你想咨询产品选型、报价、物流还是售后问题，我会转给对应角色继续处理。"
        else:
            answer = "Hello. Please tell me whether you need help with products, quotation, shipping, or after-sales support."
        return self._node_result(state, [], [], answer, False)

    def _node_result(self, state: AgentState, retrieved: list[RetrievalResult], items: list[KnowledgeItem], answer: str, need_human: bool) -> AgentState:
        return {
            "retrieved": retrieved,
            "selected_items": items,
            "answer": answer,
            "confidence": self._confidence(retrieved[0].score if retrieved else 0.0, state["lead_fields"], need_human),
            "sources": self._sources(retrieved),
            "need_human": need_human,
            "follow_up_questions": self._followups(state["role"], state["language"], state["lead_fields"], need_human),
        }

    def _search(self, state: AgentState) -> list[RetrievalResult]:
        query = " ".join([state["message"], " ".join(state["intents"]), str(state["lead_fields"].get("product") or "")])
        return [item for item in self.kb.search(query, self.settings.top_k) if item.score >= self.settings.min_relevance_score]

    def _detect_intents(self, message: str, lead_fields: dict[str, Any]) -> set[str]:
        lower = message.lower()
        intents: set[str] = set()
        if any(token in lower for token in ["ship", "shipping", "freight", "delivery", "sea", "air", "express"]) or any(token in message for token in ["物流", "运费", "海运", "空运", "快递", "发德国", "发往", "运输"]):
            intents.add("shipping")
        if any(token in lower for token in ["return", "refund", "damaged", "after-sales", "after sales", "order"]) or any(token in message for token in ["售后", "退货", "换货", "退换", "损坏", "尺寸不对", "订单"]):
            intents.add("support")
        if any(token in lower for token in ["moq", "quote", "quotation", "price"]) or any(token in message for token in ["报价", "价格", "起订量", "多少钱"]):
            intents.add("quotation")
        if any(token in lower for token in ["custom", "oem", "drawing", "sample", "step"]) or any(token in message for token in ["定制", "按图", "来图", "图纸", "样品"]):
            intents.add("capability")
        if any(token in lower for token in ["how to buy", "how can i buy", "how to choose"]) or any(token in message for token in ["怎么买", "怎么购买", "怎么选", "下单", "采购"]):
            intents.add("buying_guidance")
        if any(token in message for token in ["主要产品", "做什么产品", "产品方向", "产品范围"]):
            intents.add("company_products")
        if lead_fields.get("product") or "product" in lower or "产品" in message:
            intents.add("product")
        return intents or {"general"}

    def _select_role(self, intents: set[str]) -> str:
        if "support" in intents:
            return "support"
        if "shipping" in intents:
            return "logistics"
        if intents - {"general"}:
            return "sales"
        return "general"

    def _compose_sales(self, language: str, lead_fields: dict[str, Any], intents: set[str], items: list[KnowledgeItem], need_human: bool) -> str:
        if language == "zh":
            if "company_products" in intents:
                return "我们主要覆盖金属支架、钣金外壳、机箱机柜、箱体、面板、底板、安装板，以及冲压件、折弯件、焊接装配件。标准品可按型号确认库存，定制产品建议提供图纸、样品、材质、数量和目的国后报价。"
            if "buying_guidance" in intents:
                answer = "购买金属支架类产品建议先确认是标准品还是定制件：标准品按型号、尺寸和数量查询库存；定制件需要图纸或样品、材质、表面处理、数量和目的国后再报价。"
            elif "capability" in intents or "quotation" in intents:
                product = lead_fields.get("product") or "金属件"
                answer = f"{product}可以按图纸、样品或 3D 文件评估定制。报价前请补充材质、关键尺寸、数量、表面处理和目的国；信息齐全后可给出阶梯报价和交期方向。"
            elif items:
                answer = f"售前判断：{items[0].content}"
            else:
                return "当前知识库没有足够信息确认该问题，建议补充产品名称、图纸/样品、材质、数量和目的国后由人工跟进。"
            if need_human:
                answer += " 当前信息还不完整，建议由人工进一步确认关键规格。"
            return answer

        if "company_products" in intents:
            return "We mainly cover metal brackets, sheet-metal enclosures, cabinets, boxes, panels, base plates, mounting plates, stamped parts, bent parts, and welded assemblies."
        if "buying_guidance" in intents:
            answer = "To buy metal brackets, first separate standard products from custom work, then confirm model, dimensions, material, quantity, surface treatment, and destination country."
        elif "capability" in intents or "quotation" in intents:
            answer = "We can evaluate custom metal parts based on drawings, samples, or 3D files. For quotation, please provide material, key dimensions, quantity, surface treatment, and destination country."
        elif items:
            answer = f"From the sales side, {items[0].content}"
        else:
            return "I cannot confirm this from the current knowledge base. Please share product name, drawing/sample, material, quantity, and destination country for human follow-up."
        if need_human:
            answer += " The information is incomplete, so human follow-up is recommended."
        return answer

    def _sources(self, retrieved: list[RetrievalResult]) -> list[dict[str, Any]]:
        return [{"id": result.item.id, "quote": result.item.quote, "source_file": result.item.source_path} for result in retrieved]

    def _followups(self, role: str, language: str, lead_fields: dict[str, Any], need_human: bool) -> list[str]:
        if role == "logistics":
            return ["请提供包装尺寸、毛重、贸易条款和期望到货时间。"] if language == "zh" else ["Could you share carton dimensions, gross weight, trade terms, and target delivery time?"]
        if role == "support":
            return ["请提供订单号、照片/视频和受影响数量。"] if language == "zh" else ["Please share order number, photos/video, and affected quantity."]
        questions = []
        if not lead_fields.get("product"):
            questions.append("具体产品名称、型号或应用场景是什么？" if language == "zh" else "What product name, model, or application is this for?")
        if not lead_fields.get("quantity"):
            questions.append("大概需要多少数量？" if language == "zh" else "What quantity do you need?")
        if not lead_fields.get("country"):
            questions.append("货物发往哪个国家？" if language == "zh" else "Which country will the goods ship to?")
        return questions or (["如方便，请提供更多规格细节。"] if language == "zh" else ["Please share more specification details if available."])

    def _confidence(self, best_score: float, lead_fields: dict[str, Any], need_human: bool) -> float:
        filled = sum(1 for value in lead_fields.values() if value not in (None, "", False))
        score = min(best_score * 0.75 + (filled / 6) * 0.25, 0.98)
        if need_human:
            score *= 0.72
        return round(score, 2)

    def _is_ambiguous(self, message: str, lead_fields: dict[str, Any]) -> bool:
        if detect_language(message) == "zh":
            return len(message.strip()) <= 6 and not lead_fields.get("product")
        return len(message.split()) <= 2 and not lead_fields.get("product")

    def _quantity_value(self, quantity: str | None) -> int | None:
        if not quantity:
            return None
        match = re.search(r"\d[\d,]*", quantity)
        return int(match.group(0).replace(",", "")) if match else None

    def _country_label(self, country: str, language: str) -> str:
        if language != "zh":
            return country
        return {"Germany": "德国", "USA": "美国", "Canada": "加拿大", "UK": "英国", "France": "法国", "Japan": "日本"}.get(country, country)

    def _default_lead_fields(self, visitor: dict[str, Any]) -> dict[str, Any]:
        return {"product": None, "quantity": None, "country": visitor.get("country") or None, "email": visitor.get("email") or None, "material": None, "drawing_available": False}

    def _error_response(self, code: str, trace_id: str, visitor: dict[str, Any], message: str) -> dict:
        language = detect_language(message or "")
        answer = "系统暂时不可用，请稍后再试或留下邮箱由人工跟进。" if language == "zh" else "The system is temporarily unavailable. Please try again later or leave your email for human follow-up."
        return {"answer": answer, "language": language, "route": "general", "confidence": 0.0, "sources": [], "need_human": True, "lead_fields": self._default_lead_fields(visitor), "follow_up_questions": [], "trace_id": trace_id, "error": {"code": code}}

    def _sanitize(self, raw: dict) -> dict:
        return {
            "answer": str(raw.get("answer", "")),
            "language": raw.get("language") if raw.get("language") in {"en", "zh"} else "en",
            "route": raw.get("route") or "general",
            "confidence": max(0.0, min(float(raw.get("confidence", 0.0)), 1.0)),
            "sources": raw.get("sources") if isinstance(raw.get("sources"), list) else [],
            "need_human": bool(raw.get("need_human", False)),
            "lead_fields": raw.get("lead_fields") if isinstance(raw.get("lead_fields"), dict) else {},
            "follow_up_questions": raw.get("follow_up_questions") if isinstance(raw.get("follow_up_questions"), list) else [],
            "trace_id": str(raw.get("trace_id", "")),
        }

    def _write_trace(self, trace_id: str, session_id: str, message: str, visitor: dict[str, Any], retrieved: list[RetrievalResult], raw_llm_output: str, response: dict, errors: list[str], degraded: bool) -> None:
        append_jsonl(
            self.settings.trace_log_path,
            {
                "trace_id": trace_id,
                "session_id": session_id,
                "input": {"message": message, "visitor": visitor},
                "retrieved": [{"id": item.item.id, "score": item.score, "quote": item.item.quote} for item in retrieved],
                "llm_raw_output": raw_llm_output,
                "final_output": response,
                "errors": errors,
                "degraded": degraded,
            },
        )
        self.logger.info("trace_id=%s degraded=%s errors=%s", trace_id, degraded, errors)
