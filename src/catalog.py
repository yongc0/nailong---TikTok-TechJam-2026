"""
Shared in-memory catalog index — loaded ONCE, used by both retrieval routes.

Shared infrastructure (like src/contracts.py), not owned by any single
person: retrieval_filter.py (P2) and retrieval_dense.py (P3) both need the
same 50k products, and loading the catalog twice would double both startup
time and memory for no benefit.

Keeps everything in-memory per the competition's "no external vector DB"
constraint. The FTS5 index mirrors starter/agent.py's schema and BM25 field
weights so the keyword route stays comparable to the published baseline.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Optional

from src.attributes import COLOR_RE, MATERIAL_RE, searchable_text

# Mirrors starter/agent.py's tokenizer + stopwords so our keyword route
# behaves consistently with the baseline it extends.
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}

# BM25 column weights from starter/agent.py: parent_asin is UNINDEXED (0.0),
# then title, categories, features, details, store, description.
BM25_WEIGHTS = (0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0)

# Collapses punctuation and casing so a disclosed constraint can be matched
# as a contiguous phrase against product text. Needed because the two sides
# format the same data differently: the evaluator renders a details entry as
# "Material: alloy" while our index renders it "Material alloy", so raw
# substring matching would miss it. Measured on the public set, normalising
# lifts constraint containment in the target's own text from 94.6% to 97.1%.
_NORMALISE_RE = re.compile(r"[^a-z0-9]+")


def normalise(text: str) -> str:
    """Lowercase, punctuation-free, space-padded text for phrase matching.

    Padding with spaces lets `" phrase " in normalise(doc)` act as a
    word-boundary match without a regex per lookup.
    """
    return " " + _NORMALISE_RE.sub(" ", text.lower()).strip() + " "


def tokenize(text: str) -> list[str]:
    """Lowercase content tokens, stopwords and 1-char tokens removed."""
    # TOKEN_RE keeps only [a-z0-9]+, so quotes, asterisks, parentheses and
    # the other characters FTS5 treats as syntax can never reach the query.
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


def _flatten(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


class Catalog:
    """The frozen 50k-product catalog, indexed for keyword + attribute lookup.

    Attribute maps (material/color/price) are precomputed at load time rather
    than scanned per query: 50k regex scans once at startup (~1-2s) beats
    re-scanning on every turn of every session.
    """

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.products: dict[str, dict] = {}
        self.material: dict[str, set[str]] = {}
        self.color: dict[str, set[str]] = {}
        self.price: dict[str, float] = {}
        # "brand" has no catalog field either; `store` is the closest real
        # signal. Note the evaluator's classify_constraint() never emits
        # "brand", so this is for matching user-stated brands only, never
        # something worth spending a clarification turn asking about.
        self.brand: dict[str, str] = {}
        # Normalised full text per product, for phrase-coverage scoring.
        # Precomputed because it is needed for every candidate on every turn.
        self.norm_text: dict[str, str] = {}
        # log1p(rating_number), min-max scaled to 0..1 after the load — a
        # popularity prior for tiebreaking equally-matching candidates.
        self.popularity: dict[str, float] = {}
        # Normalised category path only — a tighter match surface than the
        # full product text.
        self.norm_categories: dict[str, str] = {}
        self.connection = sqlite3.connect(":memory:")
        self._build()

    def _build(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch: list[tuple] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                parent_asin = str(product["parent_asin"])
                self.products[parent_asin] = product

                # Precompute the attributes our filter route matches on.
                # The catalog has NO dedicated color/material/size/brand
                # fields (confirmed against the real schema) — these are
                # extracted from free text using the evaluator's own
                # vocabulary, see src/attributes.py.
                #
                # ALL matches are kept, not just the first: a garment listing
                # often names several materials ("67% Polyester, 33% Cotton")
                # or colors, and taking only the first regex hit both loses
                # real values and lets an incidental mention (a color in a
                # packaging note) masquerade as the product's actual color.
                corpus = searchable_text(product)
                materials = {m.lower() for m in MATERIAL_RE.findall(corpus)}
                if materials:
                    self.material[parent_asin] = materials
                colors = {c.lower() for c in COLOR_RE.findall(corpus)}
                if colors:
                    self.color[parent_asin] = colors
                price = product.get("price")
                if isinstance(price, (int, float)):
                    self.price[parent_asin] = float(price)
                store = product.get("store")
                if store:
                    self.brand[parent_asin] = str(store).lower()
                self.norm_text[parent_asin] = normalise(corpus)
                self.norm_categories[parent_asin] = normalise(
                    _flatten(product.get("categories"))
                )
                count = product.get("rating_number")
                if isinstance(count, (int, float)) and count > 0:
                    self.popularity[parent_asin] = math.log1p(float(count))

                batch.append((
                    parent_asin,
                    _flatten(product.get("title")),
                    _flatten(product.get("categories")),
                    _flatten(product.get("features")),
                    _flatten(product.get("details")),
                    _flatten(product.get("store")),
                    _flatten(product.get("description")),
                ))
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()

        # Scale popularity into 0..1 so its config weight means the same
        # thing as the other scoring terms.
        if self.popularity:
            top = max(self.popularity.values()) or 1.0
            self.popularity = {k: v / top for k, v in self.popularity.items()}

    def search(self, terms: list[str], limit: int = 500) -> list[tuple[str, float]]:
        """OR-match keyword search. Returns (parent_asin, bm25_score) best-first.

        OR rather than AND deliberately: an AND query over several accumulated
        slots frequently returns zero rows, and an empty candidate list is a
        guaranteed Hit Rate miss for that turn. Precision is recovered in
        rescoring (see retrieval_filter.retrieve) rather than at match time.
        """
        unique = list(dict.fromkeys(terms))[:40]
        if not unique:
            return []
        expression = " OR ".join(f'"{term}"' for term in unique)
        try:
            rows = self.connection.execute(
                f"SELECT parent_asin, bm25(products, {', '.join(str(w) for w in BM25_WEIGHTS)}) "
                "FROM products WHERE products MATCH ? ORDER BY 2 LIMIT ?",
                (expression, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # Malformed FTS expression (unbalanced quotes, reserved syntax) —
            # degrade to no candidates for this route rather than crashing the
            # whole turn.
            return []
        # bm25() returns negative numbers, more negative = better match.
        return [(str(row[0]), float(row[1])) for row in rows]

    def title(self, parent_asin: str) -> str:
        return str(self.products.get(parent_asin, {}).get("title") or "")

    def __len__(self) -> int:
        return len(self.products)
