from pathlib import Path

from evals.run_tool_eval import load_cases


def test_eval_cases_label_expected_faq_miss() -> None:
    cases = load_cases(Path("evals/ch02_tool_cases.json"))
    postage = next(case for case in cases if case["id"] == "faq-miss-postage")

    assert postage["expected_faq_match"] is False
    assert postage["known_limitation"] == "SQL LIKE keyword recall"
