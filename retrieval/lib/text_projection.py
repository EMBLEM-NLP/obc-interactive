#!/usr/bin/env python3
"""Shared text-ownership rules for retrieval/context projections.

The canonical graph preserves what the source pages contain, including legacy
article/sentence body text that can contain a flattened copy of a table. That
copy is useful for provenance but harmful for retrieval because the same table
is then embedded twice: once as run-on parent prose and once as structured cell
content.

This module defines one ownership test and one retrieval projection so context
assemblers and embedders can agree on which text belongs to a provision.
"""

from __future__ import annotations

import sqlite3

# Same threshold historically used by obc_context.py to identify flattened
# table prose. Keep it here so the threshold stops drifting between consumers.
FLAT_BODY_CHARS = 600


def has_table(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def scope_ids(db: sqlite3.Connection, node_id: str) -> list[str]:
    return [
        row[0]
        for row in db.execute(
            "SELECT descendant FROM closure WHERE ancestor=?", (node_id,)
        )
    ]


def bound_table_ids(db: sqlite3.Connection, node_id: str) -> list[str]:
    """Tables that explicitly form part of node_id or any descendant.

    New corpora encode the relationship as ref.kind='forms_part_of'. Legacy
    corpora overloaded table.parent; that path remains only as a compatibility
    fallback while old release snapshots are still readable.
    """
    ids = scope_ids(db, node_id)
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))

    if has_table(db, "ref"):
        rows = db.execute(
            f"""SELECT DISTINCT r.src
                FROM ref r JOIN node n ON n.id=r.src
                WHERE r.kind='forms_part_of'
                  AND r.dst IN ({placeholders})
                  AND n.type='table'
                ORDER BY n.rowid""",
            ids,
        ).fetchall()
        if rows:
            return [row[0] for row in rows]

    # Transitional/legacy data only. Once every supported corpus release has
    # the explicit edge, this branch can be removed.
    rows = db.execute(
        f"""SELECT DISTINCT n.id
            FROM node n
            WHERE n.type='table' AND n.parent IN ({placeholders})
            ORDER BY n.rowid""",
        ids,
    ).fetchall()
    return [row[0] for row in rows]


def owns_table(db: sqlite3.Connection, node_id: str) -> bool:
    return bool(bound_table_ids(db, node_id))


def projected_body(
    db: sqlite3.Connection,
    node_id: str,
    node_type: str,
    body: str | None,
    *,
    prefix_chars: int = FLAT_BODY_CHARS,
) -> tuple[str, bool]:
    """Return retrieval-safe body and whether a flattened tail was suppressed.

    For a long article/sentence that owns a table, preserve a short textual
    prefix (often the introductory sentence) but suppress the duplicated tail.
    Structured table-cell content is added separately by the caller.
    """
    text = (body or "").strip()
    if (
        len(text) > prefix_chars
        and node_type in ("article", "sentence")
        and owns_table(db, node_id)
    ):
        return text[:prefix_chars].rstrip(), True
    return text, False


def table_text(db: sqlite3.Connection, table_ids: list[str]) -> str:
    """Flatten structured cells only for the retrieval representation."""
    if not table_ids or not has_table(db, "cell"):
        return ""
    placeholders = ",".join("?" * len(table_ids))
    rows = db.execute(
        f"""SELECT table_id, page, r, c, text
            FROM cell WHERE table_id IN ({placeholders})
            ORDER BY table_id, page, r, c""",
        table_ids,
    ).fetchall()
    return " ".join((row[4] or "").strip() for row in rows if (row[4] or "").strip())
