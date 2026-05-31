"""Pre-flight check: one cheap call per provider to confirm keys + pinned models.

For each of the 5 providers this:
  - resolves the API key + pinned model string from .env,
  - makes ONE cheap, low/zero-token call (model-list or 1-token ping),
  - prints PASS / FAIL with the resolved model string,
  - validates the pinned model against the provider's LIVE model list (the
    authoritative source) and flags it if it is missing/outdated.

    python -m collect.test_connection

This never runs the collection matrix and costs at most a few cents.
"""

from __future__ import annotations

from . import config

# Best-effort reference of current model IDs (early 2026). The LIVE list pulled
# from each provider below is authoritative; this is just a hint for the user.
REFERENCE_MODELS = {
    "openai": ["gpt-4o", "gpt-4.1", "gpt-4o-mini", "o3", "o4-mini"],
    "anthropic": ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"],
    "gemini": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    "perplexity": ["sonar", "sonar-pro", "sonar-reasoning", "sonar-reasoning-pro",
                   "sonar-deep-research"],
}


def _suggest(model: str | None, available: list[str]) -> str:
    if not available:
        return ""
    if model:
        near = [m for m in available if model.split("-")[0] in m][:5]
        if near:
            return f" closest available: {', '.join(near)}"
    return f" available e.g.: {', '.join(sorted(available)[:6])}"


def check_openai() -> dict:
    spec = config.ENGINES["openai"]
    key, model = config.get_key(spec), config.get_model(spec)
    if not key or not model:
        return _missing(spec, key, model)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        ids = [m.id for m in client.models.list().data]
        ok_model = model in ids
        return _result(spec, model, ok_model, ids)
    except Exception as exc:  # noqa: BLE001
        return _fail(spec, model, exc)


def check_anthropic() -> dict:
    spec = config.ENGINES["anthropic"]
    key, model = config.get_key(spec), config.get_model(spec)
    if not key or not model:
        return _missing(spec, key, model)
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=key)
        ids = [m.id for m in client.models.list(limit=100).data]
        return _result(spec, model, model in ids, ids)
    except Exception as exc:  # noqa: BLE001
        return _fail(spec, model, exc)


def check_gemini() -> dict:
    spec = config.ENGINES["gemini"]
    key, model = config.get_key(spec), config.get_model(spec)
    if not key or not model:
        return _missing(spec, key, model)
    try:
        from google import genai

        client = genai.Client(api_key=key)
        ids = [m.name.replace("models/", "") for m in client.models.list()]
        return _result(spec, model, model in ids, ids)
    except Exception as exc:  # noqa: BLE001
        return _fail(spec, model, exc)


def check_perplexity() -> dict:
    # No list-models endpoint; validate with a 1-token ping (cheap).
    spec = config.ENGINES["perplexity"]
    key, model = config.get_key(spec), config.get_model(spec)
    if not key or not model:
        return _missing(spec, key, model)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, base_url="https://api.perplexity.ai")
        # Perplexity enforces a floor of 16 tokens for sonar models; use 32 to be safe.
        client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=32
        )
        return {"name": spec.display, "status": "PASS", "model": model,
                "detail": "ping ok (no list endpoint; model accepted by API)"}
    except Exception as exc:  # noqa: BLE001
        return _fail(spec, model, exc)


def check_serpapi() -> dict:
    spec = config.ENGINES["gaio"]
    key = config.get_key(spec)
    if not key:
        return {"name": spec.display, "status": "FAIL", "model": "SERP/AIO",
                "detail": f"{spec.key_var} not set in .env"}
    try:
        import requests

        r = requests.get("https://serpapi.com/account", params={"api_key": key}, timeout=30)
        r.raise_for_status()
        acct = r.json()
        left = acct.get("total_searches_left", "?")
        return {"name": spec.display, "status": "PASS", "model": "SERP/AIO",
                "detail": f"key valid; {left} searches left (AIO extraction untested)"}
    except Exception as exc:  # noqa: BLE001
        return {"name": spec.display, "status": "FAIL", "model": "SERP/AIO",
                "detail": f"{type(exc).__name__}: {exc}"}


def _missing(spec, key, model) -> dict:
    missing = []
    if not key:
        missing.append(spec.key_var)
    if spec.model_var and not model:
        missing.append(spec.model_var)
    return {"name": spec.display, "status": "FAIL", "model": model or "(unset)",
            "detail": f"missing in .env: {', '.join(missing)}"}


def _fail(spec, model, exc) -> dict:
    return {"name": spec.display, "status": "FAIL", "model": model,
            "detail": f"{type(exc).__name__}: {exc}"}


def _result(spec, model, ok_model, available) -> dict:
    if ok_model:
        detail = "key valid; pinned model found in live model list ✓"
    else:
        detail = f"key valid, but pinned model NOT in live list — outdated?{_suggest(model, available)}"
    return {"name": spec.display, "status": "PASS" if ok_model else "WARN",
            "model": model, "detail": detail}


def main() -> int:
    print("Pre-flight connection check (1 cheap call per provider)\n" + "=" * 64)
    results = [
        check_openai(),
        check_anthropic(),
        check_gemini(),
        check_perplexity(),
        check_serpapi(),
    ]
    for r in results:
        icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}.get(r["status"], "?")
        print(f"{icon} {r['status']:4}  {r['name']:22} model={r['model']}")
        print(f"        {r['detail']}")

    print("\nReference — current model IDs (early 2026; live list above is authoritative):")
    for key in config.API_ENGINE_KEYS:
        print(f"  {config.ENGINES[key].model_var:16} {', '.join(REFERENCE_MODELS[key])}")

    fails = [r for r in results if r["status"] == "FAIL"]
    warns = [r for r in results if r["status"] == "WARN"]
    print("\n" + "=" * 64)
    print(f"Summary: {len(results) - len(fails) - len(warns)} PASS, "
          f"{len(warns)} WARN (model pin), {len(fails)} FAIL.")
    if warns:
        print("WARN: update the pinned *_MODEL in .env to a model from the live list.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
