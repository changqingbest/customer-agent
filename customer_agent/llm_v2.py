import json
import urllib.error
import urllib.request


class LLMClient:
    def __init__(self, settings):
        self.settings = settings

    def generate_structured_response(self, payload: dict) -> tuple[dict | None, str, bool]:
        if self.settings.llm_mode != "remote":
            raw = json.dumps(payload, ensure_ascii=False)
            return payload, raw, False

        if not self.settings.llm_base_url or not self.settings.llm_api_key:
            return None, "Missing remote LLM configuration.", True

        request_payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": "Return valid JSON only. Preserve schema and evidence."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            self.settings.llm_base_url,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            content = parsed.get("choices", [{}])[0].get("message", {}).get("content", raw)
            return json.loads(content), raw, False
        except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as exc:
            return None, f"Remote LLM failed: {exc}", True
