"""
shared/llm_client.py — Unified LLM Client with Automatic Fallback
===================================================================
Tries providers in order until one succeeds. Groq and OpenRouter both
use the OpenAI-compatible API format, so the same `openai` package
works for all three — no extra dependencies.

Provider priority (best free first):
  1. Groq       - llama-3.3-70b-versatile
  2. OpenRouter - meta-llama/llama-3.3-70b-instruct:free
  3. Groq       - llama-4-scout
  4. OpenRouter - mistral-7b-instruct:free

Best-of-N mode:
  For important calls (RAG answers, Form 16 parsing), the client can
  query BOTH Groq and OpenRouter in parallel and pick the best answer
  using a quality scoring heuristic. This ensures both keys are used.

To use:
    from shared.llm_client import complete, complete_with_system

    answer = complete("What is the 80C deduction limit?")
    answer = complete_with_system(
        system="You are a tax assistant...",
        user="What is the HRA exemption formula?"
    )

Environment variables needed in .env:
    GROQ_API_KEY=gsk_...        ← get free at console.groq.com
    OPENROUTER_API_KEY=sk-or-.. ← get free at openrouter.ai
"""

from __future__ import annotations
import os
import time
import logging
import concurrent.futures
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)


# ── Provider config ────────────────────────────────────────────────────────────
# ORDER MATTERS: First provider that succeeds is used.
# ✓ Groq: FREE tier — 500K tokens/day, 14,400 req/day. Most reliable.
# ✓ OpenRouter :free models — genuinely $0.00, confirmed May 2026.

PROVIDERS = [
    {
        "name":     "groq-llama-3-3-70b",
        "label":    "Groq Llama-3.3-70B (free, 500K tok/day)",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key":  lambda: os.getenv("GROQ_API_KEY", ""),
        "model":    "llama-3.3-70b-versatile",
        "max_tokens": 4000,
        "provider_group": "groq",
    },
    {
        "name":     "openrouter-llama-3-3-70b-free",
        "label":    "OpenRouter Llama-3.3-70B :free ($0.00)",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key":  lambda: os.getenv("OPENROUTER_API_KEY", ""),
        "model":    "meta-llama/llama-3.3-70b-instruct:free",
        "max_tokens": 4000,
        "provider_group": "openrouter",
    },
    {
        "name":     "groq-llama-4-scout",
        "label":    "Groq Llama-4 Scout 17B (free)",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key":  lambda: os.getenv("GROQ_API_KEY", ""),
        "model":    "meta-llama/llama-4-scout-17b-16e-instruct",
        "max_tokens": 4000,
        "provider_group": "groq",
    },
    {
        "name":     "openrouter-mistral-free",
        "label":    "OpenRouter Mistral 7B :free ($0.00)",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key":  lambda: os.getenv("OPENROUTER_API_KEY", ""),
        "model":    "mistralai/mistral-7b-instruct:free",
        "max_tokens": 4000,
        "provider_group": "openrouter",
    },
]

# Errors that mean "try next provider" vs "something else is wrong"
_SKIP_ERRORS = (
    "rate_limit_exceeded",
    "rate limit",
    "quota",
    "model_not_found",
    "model not found",
    "insufficient_quota",
    "context_length_exceeded",   # try smaller model
    "overloaded",
    "service unavailable",
    "503",
    "529",
)


def _should_skip(err_str: str) -> bool:
    return any(s in err_str.lower() for s in _SKIP_ERRORS)


def _call_provider(provider: dict, messages: list[dict], temperature: float) -> str:
    """Call one provider. Returns text or raises."""
    from openai import OpenAI

    api_key = provider["api_key"]()
    if not api_key:
        raise ValueError(f"No API key set for {provider['name']}")

    kwargs = dict(
        api_key=api_key,
        max_retries=0,
    )
    if provider["base_url"]:
        kwargs["base_url"] = provider["base_url"]

    client = OpenAI(**kwargs)

    extra_headers = provider.get("extra_headers", {})

    resp = client.chat.completions.create(
        model=provider["model"],
        messages=messages,
        temperature=temperature,
        max_tokens=provider["max_tokens"],
        extra_headers=extra_headers if extra_headers else None,
    )
    return resp.choices[0].message.content.strip()


# ── Quality scoring for best-of-N ──────────────────────────────────────────────

def _score_response(text: str) -> float:
    """
    Heuristic quality score for an LLM response.
    Higher = better. Used to pick the best response when querying multiple providers.
    """
    score = 0.0

    # Length: prefer substantive answers (not too short, not too long)
    length = len(text)
    if length < 50:
        score -= 5.0    # too short = probably a refusal
    elif length < 200:
        score += 1.0
    elif length < 1500:
        score += 3.0
    else:
        score += 2.0

    # Penalize refusals / "I can't help" patterns
    refusal_phrases = [
        "i cannot", "i can't", "i'm not able", "i am not able",
        "sorry", "i don't have", "i do not have",
        "not able to answer", "no relevant information",
        "unable to", "i apologize",
    ]
    text_lower = text.lower()
    for phrase in refusal_phrases:
        if phrase in text_lower:
            score -= 3.0

    # Reward structured answers
    if "**answer**" in text_lower or "**why**" in text_lower:
        score += 2.0
    if "**source**" in text_lower:
        score += 1.0

    # Reward specific tax references
    tax_terms = ["section", "₹", "lakh", "deduction", "80c", "87a", "rebate",
                 "regime", "slab", "cess", "surcharge", "tds"]
    tax_hits = sum(1 for t in tax_terms if t in text_lower)
    score += min(tax_hits * 0.5, 3.0)

    # Reward citations / source references
    if "[" in text and "]" in text:
        score += 1.0

    return score


# ── Public API ─────────────────────────────────────────────────────────────────

def complete(
    prompt:      str,
    system:      Optional[str] = None,
    temperature: float         = 0.0,
    providers:   Optional[list[dict]] = None,
    validate_fn: Optional[callable] = None,
    best_of_n:   bool = False,
) -> str:
    """
    Send a completion request, trying providers in order until one succeeds.

    Args:
        prompt:      The user message / question.
        system:      Optional system prompt.
        temperature: 0.0 for deterministic (tax answers), 0.3 for more variety.
        providers:   Override the default provider list (for testing).
        validate_fn: Optional function to validate the result before accepting.
        best_of_n:   If True, query one Groq AND one OpenRouter model in parallel
                     and return the best response. Ensures both keys are utilized.

    Returns:
        The model's response as a string.

    Raises:
        RuntimeError: If all providers fail.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    provider_list = providers or PROVIDERS

    if best_of_n:
        return _best_of_n(messages, temperature, provider_list, validate_fn)

    return _try_providers(messages, temperature, provider_list, validate_fn=validate_fn)


def complete_with_system(
    system:      str,
    user:        str,
    temperature: float = 0.0,
    providers:   Optional[list[dict]] = None,
    validate_fn: Optional[callable] = None,
    best_of_n:   bool = False,
) -> str:
    """Convenience wrapper — common pattern in the codebase."""
    return complete(user, system=system, temperature=temperature,
                    providers=providers, validate_fn=validate_fn, best_of_n=best_of_n)


def complete_vision(
    prompt:             str,
    base64_images:      list[str],
    system:             Optional[str] = None,
    temperature:        float         = 0.0,
    providers:          Optional[list[dict]] = None,
    validate_fn:        Optional[callable] = None,
) -> str:
    """Send an image-capable completion request to Vision-supported providers."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    
    content = []
    for b64 in base64_images:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    content.append({"type": "text", "text": prompt})
    
    messages.append({"role": "user", "content": content})

    vision_providers = [
        {
            # Groq Llama-4 Scout supports vision natively
            "name":     "groq-llama-4-scout-vision",
            "label":    "Groq Llama-4 Scout Vision (free)",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key":  lambda: os.getenv("GROQ_API_KEY", ""),
            "model":    "meta-llama/llama-4-scout-17b-16e-instruct",
            "max_tokens": 2048,
            "provider_group": "groq",
        },
        {
            # OpenRouter: Llama 3.2 11B Vision is confirmed :free
            "name":     "openrouter-llama-3-2-vision-free",
            "label":    "OpenRouter Llama-3.2-11B Vision :free",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key":  lambda: os.getenv("OPENROUTER_API_KEY", ""),
            "model":    "meta-llama/llama-3.2-11b-vision-instruct:free",
            "max_tokens": 2048,
            "provider_group": "openrouter",
        },
        {
            # Fallback: Groq Llama-3.3 (text only — strips images gracefully)
            "name":     "groq-llama-3-3-text",
            "label":    "Groq Llama-3.3-70B text fallback (free)",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key":  lambda: os.getenv("GROQ_API_KEY", ""),
            "model":    "llama-3.3-70b-versatile",
            "max_tokens": 2048,
            "provider_group": "groq",
        },
    ]

    return _try_providers(messages, temperature, providers or vision_providers, validate_fn=validate_fn)


def _best_of_n(
    messages:      list[dict],
    temperature:   float,
    provider_list: list[dict],
    validate_fn:   Optional[callable] = None,
) -> str:
    """
    Query one provider from each group (Groq, OpenRouter) concurrently.
    Return the best response by quality score.
    Ensures BOTH API keys are being utilized.
    """
    # Pick one provider per group
    seen_groups = set()
    selected = []
    for p in provider_list:
        group = p.get("provider_group", p["name"])
        if group not in seen_groups:
            api_key = p["api_key"]()
            if api_key:
                seen_groups.add(group)
                selected.append(p)
        if len(selected) >= 2:
            break

    if len(selected) < 2:
        # Fall back to sequential if we don't have 2 providers
        return _try_providers(messages, temperature, provider_list, validate_fn=validate_fn)

    results = []

    def _try_one(provider):
        try:
            text = _call_provider(provider, messages, temperature)
            if validate_fn and not validate_fn(text):
                return None
            return (text, _score_response(text), provider["label"])
        except Exception as e:
            log.warning("best_of_n: %s failed: %s", provider["name"], str(e)[:100])
            return None

    # Run both providers concurrently with a timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(_try_one, p): p for p in selected}
        for future in concurrent.futures.as_completed(futures, timeout=30):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception:
                pass

    if not results:
        # All best-of-N failed → fallback to sequential
        return _try_providers(messages, temperature, provider_list, validate_fn=validate_fn)

    # Pick best by score
    results.sort(key=lambda x: x[1], reverse=True)
    best_text, best_score, best_label = results[0]
    log.info("best_of_n: picked %s (score=%.1f) from %d responses", best_label, best_score, len(results))
    return best_text


def _try_providers(
    messages:    list[dict],
    temperature: float,
    provider_list: list[dict],
    validate_fn:   Optional[callable] = None,
) -> str:
    errors = []

    for provider in provider_list:
        api_key = provider["api_key"]()
        if not api_key:
            log.debug("Skipping %s — no API key set", provider["name"])
            continue

        try:
            log.info("Trying %s...", provider["label"])
            result = _call_provider(provider, messages, temperature)
            
            if validate_fn and not validate_fn(result):
                log.warning("Validation failed for %s result", provider["label"])
                errors.append(f"{provider['label']}: Validation failed")
                continue

            log.info("Success with %s", provider["label"])
            return result

        except Exception as e:
            err_str = str(e)
            errors.append(f"{provider['label']}: {err_str[:120]}")
            log.warning("Provider %s failed: %s", provider["name"], err_str[:120])

            if _should_skip(err_str):
                # Rate limit / quota → try next immediately
                continue
            else:
                # Unknown error → brief pause then try next
                time.sleep(0.5)
                continue

    raise RuntimeError(
        "All LLM providers failed. Errors:\n" +
        "\n".join(f"  • {e}" for e in errors) +
        "\n\nCheck that at least GROQ_API_KEY or OPENROUTER_API_KEY is set in .env"
    )


# ── LangChain-compatible shim (used by itr_graph.py) ──────────────────────────

class FallbackLLM:
    """
    Thin wrapper that looks like a LangChain ChatModel to existing calling code.
    Replaces ChatOpenAI — same .invoke(messages) interface, uses fallback internally.
    """

    def __init__(self, temperature: float = 0.0, provider_list: Optional[list] = None):
        self.temperature   = temperature
        self.provider_list = provider_list or PROVIDERS

    def invoke(self, messages) -> "_FakeResponse":
        # Accept both LangChain message objects and plain dicts
        plain_messages = []
        for m in messages:
            if hasattr(m, "type") and hasattr(m, "content"):
                # LangChain message object
                role = "system" if "system" in m.type else "user"
                plain_messages.append({"role": role, "content": m.content})
            elif isinstance(m, dict):
                plain_messages.append(m)
            else:
                plain_messages.append({"role": "user", "content": str(m)})

        text = _try_providers(plain_messages, self.temperature, self.provider_list)
        return _FakeResponse(text)


class _FakeResponse:
    """Mimics langchain_core message response object."""
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content


def get_llm(temperature: float = 0.0) -> FallbackLLM:
    """
    Drop-in replacement for _get_llm() in itr_graph.py.
    Returns a FallbackLLM that behaves like ChatOpenAI.
    """
    return FallbackLLM(temperature=temperature)


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("Testing LLM fallback chain...")
    print("Available providers:")
    for p in PROVIDERS:
        key = p["api_key"]()
        status = "[OK] key set" if key else "[--] no key"
        print(f"  {p['label'][:45]:45} {status}")

    print("\nSending test prompt...")
    try:
        ans = complete(
            prompt="In one sentence, what is the Section 80C deduction limit for AY 2024-25?",
            system="You are a concise Indian income tax assistant.",
        )
        print(f"\nAnswer: {ans}")
    except RuntimeError as e:
        print(f"\nAll providers failed:\n{e}")
        sys.exit(1)
