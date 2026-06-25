# 外贸独立站客服 Agent

这是一个最小可运行的外贸独立站客服 Agent。它基于内置知识库回答制造业访客关于 OEM/定制、MOQ、图纸报价、材料、交期、样品、物流和售后等问题；信息不足时不会编造，而是收集线索并建议人工跟进。

## 功能

- CLI、HTTP API、本地 Demo 页面。
- 使用 `knowledge/company_knowledge.json` 做 RAG 检索，并返回知识库 `id` 和引用片段。
- 使用 LangGraph 搭建 Supervisor、Sales、Logistics、Support、General 多角色流程。
- 输出稳定 JSON：`answer`、`language`、`confidence`、`sources`、`need_human`、`lead_fields`、`follow_up_questions`、`trace_id`。
- 默认 mock 模式，无需 API key 也能跑通。
- 可选 remote 模式接入真实大模型；失败或非法 JSON 会降级到本地输出。
- 记录 `logs/app.log` 和 `logs/traces.jsonl`，真实日志不提交到 GitHub。

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 环境变量

不要提交真实 API key。复制示例文件：

```bash
copy .env.example .env
```

默认：

```env
LLM_MODE=mock
LLM_API_KEY=
```

真实大模型仅在本地 `.env` 中配置：

```env
LLM_MODE=remote
LLM_BASE_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
```

## 启动

CLI：

```bash
python app.py "Can you make custom stainless steel brackets based on my drawing?" --session-id demo-001 --country Germany
```

HTTP 和页面：

```bash
python app.py --serve --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000/
```

API：

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"demo-001\",\"message\":\"Can you make custom stainless steel brackets based on my drawing?\",\"visitor\":{\"country\":\"Germany\",\"email\":\"\"}}"
```

## 测试

```bash
python tests/run_cases.py
```

测试覆盖明确答案、MOQ、知识库不覆盖、中文购买引导、物流、空输入。

## 日志

运行后生成：

```text
logs/app.log
logs/traces.jsonl
```

每条 trace 记录输入、检索片段、LLM/mock 原始输出、最终 JSON、错误信息和是否降级。

## AI coding 工具

使用 Codex 协助完成重构、页面、README、测试和验收修复。

## 已知限制

- RAG 是轻量关键词检索，不是生产级向量检索。
- 会话线索保存在进程内，重启后不持久化。
- 物流只判断方式，不计算真实运价。
- Demo 页面用于本地演示，不包含登录、权限和数据库后台。
