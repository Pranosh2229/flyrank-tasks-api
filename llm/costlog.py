import json
import os
import sys
import time
from pathlib import Path

_QUARANTINE_PATH = Path(__file__).resolve().parent.parent / "logs" / "quarantine.jsonl"


def log_cost(*, prompt_version: str, model: str, input_tokens: int, output_tokens: int,
             duration_ms: int, repaired: bool) -> None:
    """One structured log line per call, to stdout -- Twelve-Factor style,
    let the environment route it rather than inventing a log file."""
    line = {
        "event": "llm_call",
        "prompt_version": prompt_version,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "repaired": repaired,
    }
    print(json.dumps(line), file=sys.stdout)


def log_quarantine(*, input_payload: dict, error: str, prompt_version: str, raw_output: str) -> None:
    """A failure that survived the repair retry: set aside with its reason
    instead of crashing the request or reaching the caller as raw text."""
    _QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input": input_payload,
        "error": error,
        "prompt_version": prompt_version,
        "raw_output": raw_output,
    }
    with open(_QUARANTINE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
