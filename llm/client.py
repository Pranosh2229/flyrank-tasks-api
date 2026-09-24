import os
import random
import time
from pathlib import Path

from openai import APIStatusError, APITimeoutError, OpenAI

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Stage 4: an explicit timeout well under the SDK's ten-minute default, and
# retries handled by our own logic (not the SDK's silent default of 2).
_TIMEOUT_SECONDS = 45.0
_MAX_RETRIES = 2
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=_TIMEOUT_SECONDS,
        max_retries=0,
    )


def load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")


class ModelCallResult:
    def __init__(self, text: str, input_tokens: int, output_tokens: int, duration_ms: int, attempts: int):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms
        self.attempts = attempts


def call_model(system_prompt: str, user_content: str) -> ModelCallResult:
    """One logical model call, with retry on timeouts/429/5xx only -- never on
    400/401/403, since those will still be wrong on the next attempt and on a
    metered free tier every pointless retry burns real quota. Exponential
    backoff with jitter: 1s, 2s, 4s."""
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    attempt = 0
    started = time.monotonic()
    while True:
        attempt += 1
        try:
            response = client.chat.completions.create(
                model=os.environ["LLM_MODEL"],
                temperature=0.2,
                messages=messages,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            usage = response.usage
            return ModelCallResult(
                text=response.choices[0].message.content,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                duration_ms=duration_ms,
                attempts=attempt,
            )
        except APITimeoutError:
            if attempt > _MAX_RETRIES:
                raise
        except APIStatusError as exc:
            if exc.status_code not in _RETRYABLE_STATUS_CODES or attempt > _MAX_RETRIES:
                raise
        backoff = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
        time.sleep(backoff)
