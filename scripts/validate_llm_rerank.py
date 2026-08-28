"""
Phase 3.0 — does an LLM rerank actually beat our ranker where it matters?

Deliberately samples TWO groups:
  * ambiguous  — we hit but not at rank 1; the only place a rerank can gain.
  * converged  — we already rank the target 1st; a rerank can only lose here,
                 and 104 of 200 public sessions are in this state.

A rerank that lifts the first group but damages the second is not worth
shipping, so both are measured. Writes results incrementally so a rate-limit
stall does not lose completed work.

Usage: python3 scripts/validate_llm_rerank.py [n_ambiguous] [n_converged]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Run from the repo root regardless of how the script is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from groq import Groq

import config
from agent import Agent
from evaluator.local_evaluator import (
    catalog_index, coarse_category, customer_reply, initial_message,
    materialize_hidden_fields, normalize_recommendations,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
client = Groq(api_key=os.environ["GROQ_API_KEY"])

N_AMBIGUOUS = int(sys.argv[1]) if len(sys.argv) > 1 else 25
N_CONVERGED = int(sys.argv[2]) if len(sys.argv) > 2 else 15
OUT = Path("results_llm_validation.json")

# Free tier: 30 RPM / 8,000 TPM. At ~800 tokens a call the token limit binds
# first, so pace to stay under it rather than under the request limit.
SECONDS_BETWEEN_CALLS = 7.0


def candidate_blurb(catalog, parent_asin: str) -> str:
    product = catalog.products.get(parent_asin, {})
    title = str(product.get("title") or "")[:110]
    features = [str(f) for f in (product.get("features") or [])][:2]
    detail = "; ".join(f[:60] for f in features)
    return f"{title}" + (f" | {detail}" if detail else "")


def build_prompt(state, catalog, candidates) -> str:
    constraints = "\n".join(f"- {c}" for c in state.disclosed_text) or "- (none stated yet)"
    listing = "\n".join(
        f"[{i}] {candidate_blurb(catalog, c.parent_asin)}"
        for i, c in enumerate(candidates)
    )
    return (
        "A shopper is searching an online clothing catalogue.\n\n"
        f"Product category they asked for: {state.slots.category or 'unspecified'}\n"
        f"Requirements they have stated, in their own words:\n{constraints}\n\n"
        f"Candidate products:\n{listing}\n\n"
        "Rank the candidates by how completely each one satisfies EVERY stated "
        "requirement. The best match is the product that meets all of them, not "
        "the one that merely mentions similar words.\n"
        'Reply with only JSON: {"ranking": [indices, best first]}'
    )


def llm_rank(prompt: str) -> list[int] | None:
    """Returns the reordered indices, or None if the call is unusable."""
    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            # Low effort, generous cap: gpt-oss spends completion tokens on
            # an internal reasoning trace BEFORE the answer, so "medium" at
            # 800 tokens truncated the JSON mid-array.
            reasoning_effort="low",
            max_completion_tokens=1500,
            temperature=0.0,
        )
    except Exception as exc:                      # rate limit, network, 5xx
        print(f"    call failed: {type(exc).__name__}: {str(exc)[:90]}")
        return None
    content = (response.choices[0].message.content or "").strip()
    # Tolerate a truncated array: take every integer after "ranking" rather
    # than requiring well-formed JSON. Missing indices are backfilled by the
    # caller, so a partial ranking is still usable.
    tail = content.split("ranking", 1)[-1]
    numbers = [int(x) for x in re.findall(r"\d+", tail)]
    if not numbers:
        print(f"    unparseable reply: {content[:70]!r}")
        return None
    return numbers


def replay_to_hit(agent, sample, ids, cats, prods):
    """Re-run a session and return (state, candidates, target) at the turn the
    target first entered our top 10 — the moment a rerank would act."""
    target = str(sample["ground_truth"]["parent_asin"])
    card, behaviour = materialize_hidden_fields(sample, prods)
    effective = {**sample, "intent_card": card, "behavior": behaviour}
    agent.reset(sample["sample_id"], sample["user_profile"])
    disclosed, boundary_used = set(), False
    override_applied = sample["scenario_type"] != "intent_override"
    message = initial_message(effective, coarse_category(cats.get(target, [])), disclosed)

    for turn in range(1, 11):
        response = agent.respond(sample["sample_id"], message, turn, 10)
        ranked = normalize_recommendations(response["recommendations"], ids)
        if override_applied and target in ranked:
            return agent._sessions[sample["sample_id"]], ranked, target
        override = effective.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            disclosed.add(str(override.get("new_value", "")))
            message = str(override.get("message", ""))
        else:
            message, boundary_used = customer_reply(
                effective, response.get("ask_attribute"), disclosed, boundary_used
            )
    return None, None, target


def main() -> None:
    samples = {s["sample_id"]: s for s in
               (json.loads(l) for l in Path("data/public_set.jsonl").read_text().splitlines() if l.strip())}
    sessions = json.load(open("results.json"))["sessions"]
    ambiguous = [x["sample_id"] for x in sessions if x["hit"] and x["best_rank"] > 1][:N_AMBIGUOUS]
    converged = [x["sample_id"] for x in sessions if x["hit"] and x["best_rank"] == 1][:N_CONVERGED]

    ids, cats, prods = catalog_index("data/catalog.jsonl")
    agent = Agent("data/catalog.jsonl")
    records = []

    for group, sample_ids in (("ambiguous", ambiguous), ("converged", converged)):
        for n, sample_id in enumerate(sample_ids, 1):
            state, ranked, target = replay_to_hit(agent, samples[sample_id], ids, cats, prods)
            if not ranked:
                continue
            candidates = [type("C", (), {"parent_asin": a})() for a in ranked]
            ours = ranked.index(target) + 1
            order = llm_rank(build_prompt(state, agent.catalog, candidates))
            if order is None:
                theirs = None
            else:
                # Keep any index the model dropped, in our original order, so a
                # truncated reply is not silently scored as a miss.
                seen = [i for i in order if 0 <= i < len(ranked)]
                seen += [i for i in range(len(ranked)) if i not in seen]
                reordered = [ranked[i] for i in seen]
                theirs = reordered.index(target) + 1
            records.append({"sample_id": sample_id, "group": group,
                            "our_rank": ours, "llm_rank": theirs})
            print(f"  [{group} {n}/{len(sample_ids)}] {sample_id}: ours={ours} llm={theirs}")
            OUT.write_text(json.dumps(records, indent=2))
            time.sleep(SECONDS_BETWEEN_CALLS)

    print(f"\nwrote {OUT} ({len(records)} records)")


if __name__ == "__main__":
    main()
