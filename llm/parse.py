import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class ParseError(Exception):
    pass


def extract_json_object(text: str) -> dict:
    """Models like to wrap JSON in a code fence or add commentary before/after
    it. Strip the fence if present, then find the first {...} object and
    parse it. Raises ParseError (never a raw json.JSONDecodeError) so callers
    have one exception type to catch."""
    if text is None:
        raise ParseError("model returned no content")

    fenced = _FENCE_RE.search(text)
    candidate = fenced.group(1) if fenced else text

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ParseError(f"no JSON object found in model output: {text!r}")

    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ParseError(f"invalid JSON: {exc}") from exc
