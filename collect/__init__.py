"""Data-collection package — one module per AI engine.

Each module exposes a `query(prompt_text, pass_number)` function that returns a
raw-response record conforming to data/schema.md. API calls are NOT implemented
yet — this is structure only. Keys are read from .env (never hard-coded).

Engines:
    chatgpt   — OpenAI API
    claude    — Anthropic API
    perplexity — Perplexity Sonar API
    gemini    — Google AI Studio / Vertex API
    google_ai_overviews — no public API; SERP provider or manual capture
"""

ENGINES = [
    "chatgpt",
    "claude",
    "perplexity",
    "gemini",
    "google_ai_overviews",
]
