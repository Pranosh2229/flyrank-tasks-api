"""Runs evals/cases.json against a running /enrich endpoint and prints how
many matched on the key field (audience), plus the ones that failed and why.
Cases run concurrently -- the endpoint's own retry/timeout behaviour per
request is unchanged, this only avoids waiting on 8 slow calls one at a time.

Usage: python evals/run_eval.py [base_url]
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
CASES_PATH = Path(__file__).parent / "cases.json"


def check_case(case: dict, result: dict) -> tuple[bool, str]:
    expected = case["expected_audience"]
    got = result.get("audience")
    allowed = expected if isinstance(expected, list) else [expected]
    if got not in allowed:
        return False, f"expected audience in {allowed}, got {got!r}"

    if case.get("expected_low_confidence") and result.get("confidence", 1.0) >= 0.5:
        return False, f"expected confidence < 0.5, got {result.get('confidence')}"

    expected_flag = case.get("expected_flag")
    if expected_flag and expected_flag not in result.get("quality_flags", []):
        return False, f"expected {expected_flag!r} in quality_flags, got {result.get('quality_flags')}"

    return True, "ok"


async def run_case(client: httpx.AsyncClient, case: dict):
    try:
        resp = await client.post(f"{BASE_URL}/enrich", json=case["input"])
    except httpx.HTTPError as exc:
        return case["id"], case["note"], False, f"request error: {exc}"
    if resp.status_code != 200:
        return case["id"], case["note"], False, f"HTTP {resp.status_code}: {resp.text}"
    ok, reason = check_case(case, resp.json())
    return case["id"], case["note"], ok, reason


async def main():
    cases = json.loads(CASES_PATH.read_text())
    async with httpx.AsyncClient(timeout=200.0) as client:
        results = await asyncio.gather(*(run_case(client, c) for c in cases))

    passed = sum(1 for _, _, ok, _ in results if ok)
    print(f"{passed}/{len(cases)} passed")
    for case_id, note, ok, reason in results:
        if not ok:
            print(f"  FAILED case {case_id} ({note}): {reason}")


if __name__ == "__main__":
    asyncio.run(main())
