"""
Entry point the local evaluator imports (`from starter.agent import Agent`).

Our implementation lives in the repo-root `agent.py`, which is the single
file the submission exports per docs/submission_rules.md. This module only
re-exports it so evaluator/local_evaluator.py runs unmodified — modifying
evaluator files is explicitly disallowed.

The original weak BM25 starter is preserved verbatim as
starter/agent_bm25_baseline.py for baseline comparisons; nothing imports it
by default. To score the old baseline again, point this import at it.
"""
from __future__ import annotations

from agent import Agent

__all__ = ["Agent"]
