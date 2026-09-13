import json
from pathlib import Path
from typing import Any

import httpx


API_URL = "http://localhost:8000/api/extract"
FIELDS = ("order_id", "request_type", "expected_solution")


def load_cases() -> list[dict[str, Any]]:
    fixture = Path(__file__).with_name("ch01_extract_cases.json")
    return json.loads(fixture.read_text(encoding="utf-8"))


def main() -> int:
    failed = False
    for case in load_cases():
        name = case["name"]
        expected = case["expected"]
        try:
            response = httpx.post(API_URL, json={"text": case["text"]}, timeout=30.0)
            actual = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"FAIL {name}: {exc}")
            failed = True
            continue

        matches = response.status_code == 200 and all(
            actual.get(field) == expected[field] for field in FIELDS
        )
        if matches:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}: expected={expected} actual={actual}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
