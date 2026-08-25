"""Run deterministic evaluations against a local stock-agent API."""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_DATASET = Path(__file__).with_name("question.json")
DEFAULT_ENDPOINT = "/api/v1/agent/chat"
DISCLAIMER_TERMS = ("not investment advice", "educational", "research only")


@dataclass(slots=True)
class EvalResult:
    case_id: str
    category: str
    passed: bool
    score: float
    checks: dict[str, bool]
    failures: list[str]
    status_code: int | None
    latency_ms: int
    trace_id: str | None = None
    answer: str | None = None
    error: str | None = None


def load_dataset(path: Path) -> dict[str, Any]:
    """Load and minimally validate the evaluation dataset."""

    with path.open(encoding="utf-8") as file:
        dataset = json.load(file)
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("The dataset must contain a non-empty 'cases' list.")
    identifiers = [case.get("id") for case in cases]
    if any(not identifier for identifier in identifiers):
        raise ValueError("Every evaluation case requires an id.")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Evaluation case ids must be unique.")
    return dataset


def _contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def score_response(case: dict[str, Any], response: httpx.Response) -> EvalResult:
    """Score one response using transparent, deterministic checks."""

    expected = case.get("expected", {})
    checks: dict[str, bool] = {
        "status_code": response.status_code == expected.get("status_code", 200)
    }
    failures: list[str] = []
    body: dict[str, Any] = {}
    try:
        parsed = response.json()
        if isinstance(parsed, dict):
            body = parsed
    except ValueError:
        pass

    answer = str(body.get("answer") or "")
    required_all = expected.get("required_all", [])
    required_any = expected.get("required_any", [])
    forbidden = expected.get("forbidden", [])
    tools_used = {str(tool) for tool in body.get("tools_used", [])}
    expected_tools = {str(tool) for tool in expected.get("expected_tools", [])}

    checks["answer_present"] = bool(answer.strip())
    checks["required_all"] = all(_contains(answer, term) for term in required_all)
    checks["required_any"] = not required_any or any(
        _contains(answer, term) for term in required_any
    )
    checks["forbidden_absent"] = not any(_contains(answer, term) for term in forbidden)
    checks["expected_tools"] = expected_tools.issubset(tools_used)

    supporting_text = " ".join(
        [
            answer,
            str(body.get("warning") or ""),
            str(body.get("disclaimer") or ""),
            " ".join(str(item) for item in body.get("warnings", [])),
        ]
    )
    checks["disclaimer"] = not expected.get("requires_disclaimer", False) or any(
        _contains(supporting_text, term) for term in DISCLAIMER_TERMS
    )

    messages = {
        "status_code": f"Expected HTTP {expected.get('status_code', 200)}.",
        "answer_present": "The response did not contain an answer.",
        "required_all": f"Missing one of the required terms: {required_all}.",
        "required_any": f"Expected at least one of these terms: {required_any}.",
        "forbidden_absent": f"Found a prohibited phrase from: {forbidden}.",
        "expected_tools": f"Expected tools were not used: {sorted(expected_tools)}.",
        "disclaimer": "The response lacked an educational/investment disclaimer.",
    }
    failures.extend(messages[name] for name, passed in checks.items() if not passed)
    score = round(sum(checks.values()) / len(checks), 4)
    return EvalResult(
        case_id=str(case["id"]),
        category=str(case.get("category", "uncategorized")),
        passed=all(checks.values()),
        score=score,
        checks=checks,
        failures=failures,
        status_code=response.status_code,
        latency_ms=int(response.elapsed.total_seconds() * 1_000),
        trace_id=str(body.get("trace_id")) if body.get("trace_id") else None,
        answer=answer or None,
    )


async def run_case(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    case: dict[str, Any],
) -> EvalResult:
    payload = {"message": case["prompt"], "history": case.get("history", [])}
    async with semaphore:
        started = asyncio.get_running_loop().time()
        try:
            response = await client.post(DEFAULT_ENDPOINT, json=payload)
            return score_response(case, response)
        except httpx.HTTPError as exc:
            elapsed = int((asyncio.get_running_loop().time() - started) * 1_000)
            return EvalResult(
                case_id=str(case["id"]),
                category=str(case.get("category", "uncategorized")),
                passed=False,
                score=0.0,
                checks={"request_completed": False},
                failures=["The API request did not complete."],
                status_code=None,
                latency_ms=elapsed,
                error=f"{type(exc).__name__}: {exc}",
            )


async def run_evaluations(args: argparse.Namespace) -> dict[str, Any]:
    dataset = load_dataset(args.dataset)
    cases = dataset["cases"]
    semaphore = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        timeout=httpx.Timeout(args.timeout),
    ) as client:
        results = await asyncio.gather(
            *(run_case(client, semaphore, case) for case in cases)
        )

    passed = sum(result.passed for result in results)
    average_score = round(sum(result.score for result in results) / len(results), 4)
    return {
        "dataset_version": dataset.get("version"),
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": round(passed / len(results), 4),
            "average_score": average_score,
        },
        "results": [asdict(result) for result in results],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--fail-under",
        type=float,
        default=0.7,
        help="Minimum average score from 0 to 1.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.timeout <= 0 or args.concurrency < 1:
        raise SystemExit("timeout and concurrency must be positive")
    if not 0 <= args.fail_under <= 1:
        raise SystemExit("fail-under must be between 0 and 1")

    report = asyncio.run(run_evaluations(args))
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)
    return int(report["summary"]["average_score"] < args.fail_under)


if __name__ == "__main__":
    sys.exit(main())
