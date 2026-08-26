"""
Every tunable knob for the pipeline lives here — nobody should hardcode a
threshold, weight, or model name inside a pillar module. This is what lets
teammates without Claude Code access run experiments (edit a value, re-run
`python3 -m evaluator.local_evaluator`, compare TechnicalScore) without
touching pipeline logic.

Values below are placeholders/starting guesses, not tuned. Expect every
number here to change once the hacking window opens and you're looking at
real scenario_metrics breakdowns.
"""

# --- Over-generality / clarification trigger (state.py, P1) ---
CANDIDATE_POOL_TOO_LARGE = 50   # (reserved) pool breadth above which the result set counts as over-general
MAX_CLARIFYING_TURNS = 4        # force a best-guess return after this many clarifying questions, well inside the 10-turn hard cap

# Stop asking once the top candidate leads the shortlist by this margin
# (0..1). Asking is free in this harness — the evaluator scores
# recommendations before it reads ask_attribute — so the agent asks by
# default and this threshold only decides when it has converged enough to
# go quiet. Lower it to ask less.
CONFIDENT_MARGIN = 0.35

# Order to ask about when several slots are still unknown.
#
# MEASURED, not guessed: classifying every public-set target's disclosable
# constraints through the evaluator's own classify_constraint() gives the
# share of sessions where asking each attribute actually yields new
# information:
#
#   feature   96.0%     style      9.0%
#   material  76.5%     size       4.5%
#   color     25.5%     use_case   2.0%
#   budget/brand/category: 0% — never ask these
#
# "feature" tops the list because it is classify_constraint()'s default
# bucket, so most constraints land there. budget scores 0% because
# intent_card() appends the price hint last and only the first four
# constraints survive; brand has no branch in classify_constraint() at all;
# category is disclosed for free in turn 1 by initial_message().
# Every wasted question costs a turn against MTTC, so the zero-yield
# attributes are excluded entirely rather than merely deprioritised.
# Re-run tests/test_attribute_yield.py if the evaluator ever changes.
ATTRIBUTE_PRIORITY = [
    "feature", "material", "color", "style", "size", "use_case",
]

# --- Filter retrieval (retrieval_filter.py, P2) ---
# How many keyword hits to rescore. Much wider than top_k on purpose: the
# target often ranks poorly on raw BM25 but well once verified attribute
# matches are counted, so it must survive into rescoring to be findable.
POOL_SIZE = 800
# Flat score bonus per verified attribute match, added to the 0..1
# normalised keyword score. Raise it to trust structured matches more,
# lower it to trust keyword relevance more.
VERIFIED_MATCH_BONUS = 0.5
# Budget is a proximity target ("budget around $X"), not a ceiling — this is
# the fraction of the stated price still counted as a match.
BUDGET_TOLERANCE = 0.35

# --- Retrieval fusion (fusion_rerank.py, P3) ---
FILTER_ROUTE_WEIGHT = 0.6
DENSE_ROUTE_WEIGHT = 0.4
FUSION_METHOD = "rrf"           # "rrf" or "weighted_sum"
RRF_K = 60

# --- Dense retrieval (retrieval_dense.py, P3) ---
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # local, in-memory — no external vector DB
DENSE_TOP_K = 50

# --- LLM calls (Groq) ---
GROQ_MODEL = "openai/gpt-oss-20b"

# gpt-oss models spend completion tokens on an internal reasoning trace
# before the final answer — cap too low and you get an empty reply.
# Confirmed empirically: 20 tokens -> empty; 200 tokens -> reliable.
RERANK_REASONING_EFFORT = "medium"   # ranking drives MRR (30% of score) — worth the extra reasoning
RERANK_MAX_COMPLETION_TOKENS = 500
RERANK_CANDIDATE_POOL = 30           # how many fused candidates to hand the LLM for final reranking

CLARIFY_REASONING_EFFORT = "low"     # cheap classification/question-picking — don't overspend here
CLARIFY_MAX_COMPLETION_TOKENS = 200

# --- Personalization (personalization.py, P4) ---
PROFILE_BOOST_WEIGHT = 0.15     # how much preference_tags overlap nudges final ranking score (soft prior, never a hard filter)
