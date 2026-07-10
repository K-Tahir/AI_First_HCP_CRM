"""Groq LLM client factory.

Centralizing construction here means switching models (e.g. from
`gemma2-9b-it` to `llama-3.3-70b-versatile`) is a one-line config change,
never a code change - satisfying the assignment's "configurable
architecture" requirement.

This module has TWO layers of protection against Groq's `model_decommissioned`
error, because a config-only fix (layer 1) turned out to be fragile in
practice - a stale `.env`, a leftover shell-exported `GROQ_MODEL`, or an old
cached process can all still hand a dead model ID to layer 1 in a way that
doesn't exactly string-match the lookup table (extra whitespace, different
casing, a quoted value that wasn't stripped, etc). Layer 2 is a genuine
runtime guard: if Groq ever rejects a call with `model_decommissioned`
*regardless of why*, we transparently rebuild the client with a hardcoded,
known-good model and retry once, so the request still succeeds.
"""

from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# --- Layer 1: config-time normalization -------------------------------------
# Groq periodically decommissions models. This map rewrites a deprecated
# model ID to a currently-active equivalent before the client is even built.
# Source: https://console.groq.com/docs/deprecations
_DEPRECATED_MODEL_REPLACEMENTS = {
    "gemma2-9b-it": "openai/gpt-oss-20b",
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
    "llama3-70b-8192": "openai/gpt-oss-120b",
    "llama3-8b-8192": "openai/gpt-oss-20b",
    "mixtral-8x7b-32768": "openai/gpt-oss-120b",
    "qwen/qwen3-32b": "openai/gpt-oss-120b",
    "meta-llama/llama-4-scout-17b-16e-instruct": "openai/gpt-oss-120b",
}

# --- Layer 2: absolute last-resort model, used ONLY if Groq rejects a live
# call as decommissioned. Hardcoded on purpose - it must not depend on
# settings/.env/OS env at all, since those are exactly what may be broken.
_EMERGENCY_SAFE_MODEL = "openai/gpt-oss-20b"


def _resolve_model(model: str) -> str:
    """Normalize and translate a model string, tolerant of stray whitespace/casing."""
    normalized = (model or "").strip()
    # Exact match first (fast path), then a forgiving case-insensitive match.
    replacement = _DEPRECATED_MODEL_REPLACEMENTS.get(normalized)
    if replacement is None:
        lowered = normalized.lower()
        for known_bad, known_good in _DEPRECATED_MODEL_REPLACEMENTS.items():
            if lowered == known_bad.lower():
                replacement = known_good
                break
    if replacement:
        logger.warning(
            "Configured Groq model '%s' is deprecated on Groq's platform; "
            "automatically using '%s' instead. Update GROQ_MODEL in your .env "
            "to silence this warning.",
            model,
            replacement,
        )
        return replacement
    return normalized


def _build_client(model: str, temperature: float | None = None) -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Create a key at https://console.groq.com and set it "
            "in your .env file before starting the server."
        )
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=model,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


def get_llm(model: str | None = None, temperature: float | None = None) -> ChatGroq:
    """Return a fresh ChatGroq client for the given model/temperature pair.

    Deliberately NOT cached (no @lru_cache): memoizing this across a
    long-lived process risks masking a .env/API-key change made after the
    server started, which previously made a config fix look like it "didn't
    work" when actually the server just needed a real restart.
    """
    resolved_model = _resolve_model(model or settings.GROQ_MODEL)
    return _build_client(resolved_model, temperature)


def get_fallback_llm() -> ChatGroq:
    """Return the configured fallback model (e.g. openai/gpt-oss-120b)."""
    return get_llm(model=_resolve_model(settings.GROQ_FALLBACK_MODEL))


def _is_decommissioned_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "decommissioned" in text or "model_decommissioned" in text or "does not exist" in text


def invoke_with_self_healing(messages, tools: list | None = None):
    """Invoke the configured Groq LLM, self-healing at call time if Groq rejects
    the model as decommissioned - regardless of *why* a dead model ID reached
    this point (stale .env, stray shell env var, cached process, etc).

    This is the ONLY function the rest of the app should use to talk to Groq
    for the agent loop; it guarantees a request never fails purely because of
    a deprecated model ID as long as `_EMERGENCY_SAFE_MODEL` itself is alive.
    """
    llm = get_llm()
    if tools:
        llm = llm.bind_tools(tools)

    try:
        return llm.invoke(messages)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, we inspect below
        if not _is_decommissioned_error(exc):
            raise

        logger.error(
            "Groq rejected the configured model as decommissioned at call time "
            "(this means a dead model ID reached the client despite config-level "
            "safeguards - check for a stray shell-exported GROQ_MODEL or a stale "
            ".env). Retrying once with the hardcoded emergency model '%s'.",
            _EMERGENCY_SAFE_MODEL,
        )
        emergency_llm = _build_client(_EMERGENCY_SAFE_MODEL)
        if tools:
            emergency_llm = emergency_llm.bind_tools(tools)
        return emergency_llm.invoke(messages)
