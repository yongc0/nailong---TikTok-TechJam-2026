"""
Smoke test: confirm a Groq API key works and gpt-oss-20b responds.

Usage:
    python3 scripts/test_groq.py

Reads GROQ_API_KEY from a .env file in the repo root (never prints the key itself).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print(
        "No GROQ_API_KEY found.\n"
        f"Create a file at {REPO_ROOT / '.env'} containing:\n"
        "  GROQ_API_KEY=your-key-here\n"
        "(see .env.example — this file is already git-ignored, safe to keep secrets in)",
        file=sys.stderr,
    )
    sys.exit(1)

client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": (
                "A shopper says: 'I need black leather ankle boots, size 8, under $60.' "
                "Classify their intent as exactly one word: BUYING or BROWSING. "
                "Reply with only that one word."
            ),
        }
    ],
    reasoning_effort="low",
    max_completion_tokens=200,
)

choice = response.choices[0].message
usage = response.usage

print("Model:", response.model)
print("Reasoning:", getattr(choice, "reasoning", None))
print("Reply:", (choice.content or "").strip())
print(
    "Tokens — prompt:", usage.prompt_tokens,
    "completion:", usage.completion_tokens,
    "total:", usage.total_tokens,
)
print("\n✅ Groq API key works and gpt-oss-20b is reachable.")
