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
CANDIDATE_POOL_TOO_LARGE = 50   # ask instead of guessing if more candidates than this survive retrieval
MAX_CLARIFYING_TURNS = 4        # force a best-guess return after this many clarifying questions, well inside the 10-turn hard cap
ATTRIBUTE_PRIORITY = [          # default order to ask about when several slots are still unknown
    "category", "budget", "size", "color", "material",
    "style", "brand", "use_case", "feature", "other",
]

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
