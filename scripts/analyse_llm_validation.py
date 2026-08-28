"""Scores the Phase 3.0 experiment: does an LLM rerank earn its place?

The verdict needs both halves. A rerank that lifts ambiguous sessions but
demotes converged ones is a net loss, because 104 of 200 public sessions are
already ranked 1st and can only lose.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

records = json.loads(Path("results_llm_validation.json").read_text())
usable = [r for r in records if r["llm_rank"] is not None]
failed = len(records) - len(usable)

print(f"{len(records)} sessions, {len(usable)} usable ({failed} unusable LLM replies)\n")

for group in ("ambiguous", "converged"):
    rows = [r for r in usable if r["group"] == group]
    if not rows:
        continue
    ours = sum(1 / r["our_rank"] for r in rows) / len(rows)
    theirs = sum(1 / r["llm_rank"] for r in rows) / len(rows)
    better = sum(1 for r in rows if r["llm_rank"] < r["our_rank"])
    worse = sum(1 for r in rows if r["llm_rank"] > r["our_rank"])
    same = len(rows) - better - worse
    print(f"--- {group}  (n={len(rows)}) ---")
    print(f"  mean reciprocal rank   ours {ours:.3f}   llm {theirs:.3f}   delta {theirs - ours:+.3f}")
    print(f"  llm better: {better}   worse: {worse}   unchanged: {same}")
    if group == "converged" and worse:
        print(f"  ** {worse} already-correct sessions were DEMOTED — pure loss **")
    print()

ours_all = sum(1 / r["our_rank"] for r in usable) / len(usable)
llm_all = sum(1 / r["llm_rank"] for r in usable) / len(usable)
print(f"pooled MRR: ours {ours_all:.3f} -> llm {llm_all:.3f} ({llm_all - ours_all:+.3f})")

# Translate into TechnicalScore. MRR is 30% of it, and this sample is drawn
# disproportionately from ambiguous sessions, so reweight to the real 200-set
# mix (93 ambiguous, 104 converged) before projecting.
sessions = json.load(open("results.json"))["sessions"]
n_amb = sum(1 for s in sessions if s["hit"] and s["best_rank"] > 1)
n_con = sum(1 for s in sessions if s["hit"] and s["best_rank"] == 1)
deltas = {}
for group in ("ambiguous", "converged"):
    rows = [r for r in usable if r["group"] == group]
    if rows:
        deltas[group] = (sum(1 / r["llm_rank"] for r in rows) - sum(1 / r["our_rank"] for r in rows)) / len(rows)
if len(deltas) == 2:
    weighted = (deltas["ambiguous"] * n_amb + deltas["converged"] * n_con) / 200
    print(f"\nprojected MRR delta over the full 200-set mix: {weighted:+.4f}")
    print(f"projected TechnicalScore delta (MRR is 30%):    {0.30 * weighted:+.4f}")
    print(f"  -> {0.875866:.4f} would become ~{0.875866 + 0.30 * weighted:.4f}")
    print("\nVERDICT:", "worth building" if 0.30 * weighted > 0.01
          else "NOT worth building — gain is below noise, and it needs network")
