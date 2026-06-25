from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from customer_agent.service import CustomerServiceAgent


def load_cases() -> list[dict]:
    return json.loads((ROOT / "tests" / "test_cases.json").read_text(encoding="utf-8"))


def main() -> int:
    agent = CustomerServiceAgent()
    cases = load_cases()
    failures: list[str] = []

    for case in cases:
        result = agent.chat(
            session_id=f"test-{case['id']}",
            message=case["message"],
            visitor={"country": "Germany", "email": "buyer@example.com"},
        )
        answer = result.get("answer", "")
        route = result.get("route", "")
        missing = [kw for kw in case["expect_keywords"] if kw not in answer]
        ok = route == case["expected_route"] and not missing
        print(
            json.dumps(
                {
                    "id": case["id"],
                    "route": route,
                    "expected_route": case["expected_route"],
                    "confidence": result.get("confidence"),
                    "ok": ok,
                    "missing_keywords": missing,
                    "answer": answer,
                },
                ensure_ascii=False,
            )
        )
        if not ok:
            failures.append(case["id"])

    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print(f"PASSED: {len(cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
