import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from customer_agent.service import CustomerServiceAgent


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>外贸客服 Agent Demo</title>
  <style>
    body { margin:0; font-family:"Microsoft YaHei",sans-serif; background:#eef2ef; color:#16202f; }
    .shell { max-width:1440px; margin:0 auto; padding:18px; }
    .topbar,.panel { background:#fff; border:1px solid #dbe2dc; box-shadow:0 18px 52px rgba(26,38,34,.1); }
    .topbar { display:flex; justify-content:space-between; gap:16px; padding:16px 18px; margin-bottom:14px; }
    h1 { margin:0; font-size:24px; }
    .subline { margin:6px 0 0; color:#667385; font-size:13px; }
    .pill { display:inline-flex; align-items:center; min-height:34px; padding:0 11px; border:1px solid #dbe2dc; color:#12656d; font-size:12px; font-weight:700; }
    .grid { display:grid; grid-template-columns:300px minmax(0,1fr) 380px; gap:14px; }
    .head { padding:16px; border-bottom:1px solid #dbe2dc; }
    .head h2 { margin:0; font-size:16px; }
    .head p { margin:7px 0 0; color:#667385; font-size:12px; line-height:1.55; }
    .flow,.side { padding:14px; display:grid; gap:10px; }
    .step,.source,.follow { border:1px solid #dbe2dc; background:#fbfcfb; padding:10px; font-size:12px; line-height:1.5; }
    .examples { padding:14px 16px; border-bottom:1px solid #dbe2dc; background:#fbfcfb; }
    .example-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }
    .example { min-height:92px; padding:10px; border:1px solid #d5ddd8; background:#fff; text-align:left; }
    .example strong { display:block; margin-bottom:6px; }
    .example span { color:#667385; font-size:12px; line-height:1.35; }
    .chat { display:grid; grid-template-rows:auto minmax(470px,1fr) auto; min-height:780px; }
    .messages { overflow:auto; padding:20px; display:flex; flex-direction:column; gap:14px; background:#f7f8f4; }
    .bubble { max-width:86%; padding:14px 16px; line-height:1.72; white-space:pre-wrap; border:1px solid #dbe2dc; background:#fff; font-size:14px; }
    .user { align-self:flex-end; color:#fff; background:#b85d3f; border-color:#b85d3f; }
    .agent { align-self:flex-start; }
    .meta { display:flex; flex-wrap:wrap; gap:7px; margin-top:11px; }
    .meta span { padding:5px 9px; color:#12656d; background:#f2eee6; border:1px solid #e2d8c9; font-size:12px; }
    .composer { padding:16px; border-top:1px solid #dbe2dc; background:#fff; }
    .row { display:grid; grid-template-columns:150px 1fr 1fr; gap:9px; margin-bottom:9px; }
    label { display:grid; gap:6px; color:#12656d; font-size:12px; font-weight:800; }
    input,textarea { width:100%; border:1px solid #d9dfd8; padding:10px; box-sizing:border-box; }
    textarea { min-height:96px; resize:vertical; }
    .actions { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-top:10px; }
    .primary { min-height:40px; padding:0 16px; border:0; color:#fff; background:#b85d3f; font-weight:800; }
    .kv { display:grid; gap:7px; }
    .kv-row { display:grid; grid-template-columns:86px minmax(0,1fr); gap:8px; padding:8px 0; border-bottom:1px solid #edf0ec; font-size:12px; }
    .kv-row span:last-child { overflow-wrap:anywhere; font-weight:700; }
    .json { min-height:238px; max-height:360px; overflow:auto; padding:12px; margin:0; color:#d9fbe8; background:#111827; font-size:12px; line-height:1.52; white-space:pre-wrap; }
    @media (max-width:1100px){ .grid{grid-template-columns:1fr;} .example-grid{grid-template-columns:1fr 1fr;} .row{grid-template-columns:1fr;} }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div><h1>外贸独立站客服 Agent 控制台</h1><p class="subline">演示 LangGraph 分工路由、RAG 引用、线索抽取、模拟/真实模型模式和最终 JSON 输出。</p></div>
      <div><span class="pill" id="mode_badge">模式检测中</span> <span class="pill" id="status">就绪</span></div>
    </header>
    <section class="grid">
      <aside class="panel"><div class="head"><h2>业务闭环</h2><p>从访客咨询到可落地回复，每一步都能在右侧 JSON 中复盘。</p></div><div class="flow"><div class="step">1. 意图识别：产品、报价、物流、售后。</div><div class="step">2. 角色路由：主管分发给售前、物流、售后。</div><div class="step">3. RAG 检索：引用知识库。</div><div class="step">4. 结构化输出：回答、置信度、线索字段和追问。</div></div></aside>
      <section class="panel chat">
        <div class="examples"><strong>五条演示示例</strong><div class="example-grid">
          <button class="example" data-message="我想买金属支架类产品，怎么买？"><strong>金属支架怎么买</strong><span>购买路径和补充字段。</span></button>
          <button class="example" data-message="我们有不锈钢支架图纸，报价需要哪些资料？"><strong>有图纸报价</strong><span>定制件、材质、报价资料。</span></button>
          <button class="example" data-message="我不知道型号，标准机箱应该怎么选？"><strong>标准机箱选型</strong><span>标准品和型号追问。</span></button>
          <button class="example" data-message="如果先买样品，需要准备什么信息？"><strong>先买样品</strong><span>样品/小批量询盘。</span></button>
          <button class="example" data-message="500 个支架发德国，能估算物流方式吗？" data-country="Germany"><strong>德国物流估算</strong><span>物流路由和目的国。</span></button>
        </div></div>
        <div class="messages" id="message_list"><div class="bubble agent">你好，我是外贸独立站客服 Agent。你可以点击上方示例，也可以直接输入访客问题。<div class="meta"><span>流程编排</span><span>知识库检索</span><span>默认模拟模式</span></div></div></div>
        <div class="composer"><div class="row"><label>会话 ID<input id="session_id" value="demo-001"></label><label>访客国家<input id="country" value="Germany"></label><label>访客邮箱<input id="email" value="buyer@example.com"></label></div><label>访客消息<textarea id="message" placeholder="例如：我想买金属支架类产品，怎么买？"></textarea></label><div class="actions"><span>按 Ctrl + Enter 发送。模拟模式无需 API key。</span><button class="primary" id="send_btn">发送并生成 JSON</button></div></div>
      </section>
      <aside class="panel"><div class="head"><h2>结果与 JSON 输出</h2><p>重点看路由、引用、线索字段和是否需要人工跟进。</p></div><div class="side"><div class="kv" id="summary"><div class="kv-row"><span>路由</span><span>-</span></div><div class="kv-row"><span>语言</span><span>-</span></div><div class="kv-row"><span>置信度</span><span>-</span></div><div class="kv-row"><span>人工</span><span>-</span></div></div><strong>线索字段</strong><div class="kv" id="lead_fields"></div><strong>引用来源</strong><div id="sources"></div><strong>追问建议</strong><div id="followups"></div><strong>JSON 输出</strong><pre class="json" id="json_box">{ "status": "waiting" }</pre></div></aside>
    </section>
  </main>
  <script>
    const routeLabels={sales:"售前",logistics:"物流",support:"售后",general:"通用"};
    const langLabels={zh:"中文",en:"英文"};
    const modeLabels={mock:"模拟运行",remote:"真实模型",unknown:"未知"};
    const $=id=>document.getElementById(id);
    const esc=v=>String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    function bubble(text,type,meta=[]){const div=document.createElement("div");div.className=`bubble ${type}`;div.innerHTML=esc(text);if(meta.length)div.innerHTML+=`<div class="meta">${meta.map(x=>`<span>${esc(x)}</span>`).join("")}</div>`;$("message_list").appendChild(div);$("message_list").scrollTop=$("message_list").scrollHeight;}
    function render(data){$("summary").innerHTML=`<div class="kv-row"><span>路由</span><span>${esc(routeLabels[data.route]||data.route||"-")}</span></div><div class="kv-row"><span>语言</span><span>${esc(langLabels[data.language]||data.language||"-")}</span></div><div class="kv-row"><span>置信度</span><span>${esc(data.confidence??"-")}</span></div><div class="kv-row"><span>人工</span><span>${data.need_human?"需要跟进":"可自动回复"}</span></div>`;$("lead_fields").innerHTML=Object.entries(data.lead_fields||{}).map(([k,v])=>`<div class="kv-row"><span>${esc(k)}</span><span>${esc(v??"-")}</span></div>`).join("");$("sources").innerHTML=(data.sources||[]).map(s=>`<div class="source"><strong>${esc(s.id)}</strong><br>${esc(s.quote)}</div>`).join("")||"<div class='source'>暂无引用</div>";$("followups").innerHTML=(data.follow_up_questions||[]).map(x=>`<div class="follow">${esc(x)}</div>`).join("")||"<div class='follow'>暂无追问</div>";$("json_box").textContent=JSON.stringify(data,null,2);}
    async function loadMode(){try{const r=await fetch("/health");const d=await r.json();$("mode_badge").textContent=`模式：${modeLabels[d.llm_mode]||d.llm_mode||"未知"}`;}catch(e){$("mode_badge").textContent="模式：未知";}}
    async function send(){const msg=$("message").value.trim();if(!msg){$("status").textContent="请输入消息";return;}bubble(msg,"user");$("status").textContent="处理中";const payload={session_id:$("session_id").value||"demo-001",message:msg,visitor:{country:$("country").value,email:$("email").value}};try{const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok)throw new Error(d?.error?.message||"请求失败");bubble(d.answer||"(无回答)","agent",[`路由 ${routeLabels[d.route]||d.route||"-"}`,`语言 ${langLabels[d.language]||d.language||"-"}`,`置信度 ${d.confidence??"-"}`,d.need_human?"需人工跟进":"可自动回复"]);render(d);$("status").textContent="已完成";}catch(e){bubble(`请求失败：${e.message}`,"agent");$("status").textContent="请求失败";}}
    document.querySelectorAll("[data-message]").forEach(btn=>btn.addEventListener("click",()=>{$("message").value=btn.dataset.message||"";if(btn.dataset.country)$("country").value=btn.dataset.country;$("status").textContent="已载入示例";}));
    $("send_btn").addEventListener("click",send);$("message").addEventListener("keydown",e=>{if(e.key==="Enter"&&(e.ctrlKey||e.metaKey))send();});loadMode();
  </script>
</body>
</html>
"""


class ChatHandler(BaseHTTPRequestHandler):
    agent: CustomerServiceAgent | None = None
    agent_init_error: str | None = None

    @classmethod
    def _get_agent(cls) -> CustomerServiceAgent:
        if cls.agent:
            return cls.agent
        if cls.agent_init_error:
            raise RuntimeError(cls.agent_init_error)
        try:
            cls.agent = CustomerServiceAgent()
            if cls.agent.initialization_error:
                raise RuntimeError(cls.agent.initialization_error)
            return cls.agent
        except Exception as exc:
            cls.agent_init_error = f"{type(exc).__name__}: {exc}"
            raise RuntimeError(cls.agent_init_error) from exc

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            try:
                agent = self._get_agent()
                self._send_json({"status": "ok", "llm_mode": agent.settings.llm_mode, "mock_mode": agent.settings.llm_mode != "remote"})
            except RuntimeError as exc:
                self._send_json({"status": "degraded", "error": str(exc), "llm_mode": "unknown", "mock_mode": True}, HTTPStatus.SERVICE_UNAVAILABLE)
            return
        self._send_json({"error": {"code": "NOT_FOUND", "message": "Supported routes: GET /, GET /health, POST /chat."}}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._send_json({"error": {"code": "NOT_FOUND", "message": "Only POST /chat is supported."}}, HTTPStatus.NOT_FOUND)
            return
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8")
            payload = json.loads(raw) if raw else {}
        except (ValueError, json.JSONDecodeError):
            self._send_json({"error": {"code": "INVALID_JSON", "message": "Request body must be valid JSON."}}, HTTPStatus.BAD_REQUEST)
            return
        try:
            agent = self._get_agent()
            response = agent.chat(str(payload.get("session_id") or "web-demo"), str(payload.get("message") or ""), payload.get("visitor") if isinstance(payload.get("visitor"), dict) else {})
            self._send_json(response)
        except RuntimeError as exc:
            self._send_json({"error": {"code": "SERVICE_UNAVAILABLE", "message": str(exc)}}, HTTPStatus.SERVICE_UNAVAILABLE)


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), ChatHandler)
    print(f"Customer agent server running at http://{host}:{port}")
    server.serve_forever()
