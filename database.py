# -*- coding: utf-8 -*-
"""
database.py — NHM Coach Backoffice
SQLite database setup using Python's built-in sqlite3.
Tables: clients, plans, feedback
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "data/coach.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL,
            lang        TEXT NOT NULL DEFAULT 'de',
            nst_type    TEXT NOT NULL,
            goal        TEXT NOT NULL,
            pillars     TEXT NOT NULL,
            duration    TEXT NOT NULL DEFAULT '4',
            calories    TEXT DEFAULT '',
            train_days  TEXT DEFAULT '3',
            notes       TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER NOT NULL,
            version     INTEGER NOT NULL DEFAULT 1,
            content     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'draft',
            sent_at     TEXT DEFAULT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id     INTEGER NOT NULL,
            client_id   INTEGER NOT NULL,
            answers     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES plans(id),
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS assistant_chats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL DEFAULT 'Neues Gespräch',
            client_id   INTEGER DEFAULT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS assistant_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id     INTEGER NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES assistant_chats(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT NOT NULL,
            content     TEXT NOT NULL,
            file_size   INTEGER DEFAULT 0,
            created_at  TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)

    # ── Kunden-Portal Tabellen ────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS client_tokens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER NOT NULL UNIQUE,
            token       TEXT NOT NULL UNIQUE,
            last_login  TEXT DEFAULT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS client_notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER NOT NULL,
            category    TEXT NOT NULL DEFAULT 'allgemein',
            text        TEXT NOT NULL,
            flagged     INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS exercise_weights (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER NOT NULL,
            plan_id     INTEGER NOT NULL,
            week        INTEGER NOT NULL DEFAULT 1,
            day         TEXT NOT NULL,
            exercise    TEXT NOT NULL,
            weight      REAL DEFAULT NULL,
            unit        TEXT NOT NULL DEFAULT 'kg',
            reps_done   TEXT DEFAULT NULL,
            updated_at  TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS client_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER NOT NULL,
            sender      TEXT NOT NULL DEFAULT 'client',
            text        TEXT NOT NULL,
            file_path   TEXT DEFAULT NULL,
            read_by_coach INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS client_released_pillars (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER NOT NULL UNIQUE,
            pillars     TEXT NOT NULL DEFAULT '[]',
            updated_at  TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    conn.commit()
    conn.close()


# ── Client CRUD ───────────────────────────────────────────────────────────────

def create_client(name, email, lang, nst_type, goal, pillars, duration,
                  calories="", train_days="3", notes=""):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO clients (name, email, lang, nst_type, goal, pillars,
                             duration, calories, train_days, notes,
                             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, email, lang, nst_type, goal,
          json.dumps(pillars) if isinstance(pillars, list) else pillars,
          duration, calories, train_days, notes, now, now))
    client_id = c.lastrowid
    conn.commit()
    conn.close()
    return client_id


def get_client(client_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["pillars"] = json.loads(d["pillars"])
    except Exception:
        d["pillars"] = [d["pillars"]]
    return d


def update_client(client_id, **kwargs):
    now = datetime.utcnow().isoformat()
    kwargs["updated_at"] = now
    if "pillars" in kwargs and isinstance(kwargs["pillars"], list):
        kwargs["pillars"] = json.dumps(kwargs["pillars"])
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [client_id]
    conn = get_conn()
    conn.execute(f"UPDATE clients SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def list_clients():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM clients ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["pillars"] = json.loads(d["pillars"])
        except Exception:
            d["pillars"] = [d["pillars"]]
        result.append(d)
    return result


def delete_client(client_id):
    conn = get_conn()
    conn.execute("DELETE FROM feedback WHERE client_id=?", (client_id,))
    conn.execute("DELETE FROM plans WHERE client_id=?", (client_id,))
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()


# ── Plan CRUD ─────────────────────────────────────────────────────────────────

def create_plan(client_id, content, version=1):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO plans (client_id, version, content, status, created_at)
        VALUES (?, ?, ?, 'draft', ?)
    """, (client_id, version, json.dumps(content), now))
    plan_id = c.lastrowid
    conn.commit()
    conn.close()
    return plan_id


def get_plan(plan_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["content"] = json.loads(d["content"])
    except Exception:
        pass
    return d


def get_latest_plan(client_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM plans WHERE client_id=? ORDER BY version DESC LIMIT 1",
        (client_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["content"] = json.loads(d["content"])
    except Exception:
        pass
    return d


def list_plans(client_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM plans WHERE client_id=? ORDER BY version DESC",
        (client_id,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["content"] = json.loads(d["content"])
        except Exception:
            pass
        result.append(d)
    return result


def update_plan_content(plan_id, content):
    conn = get_conn()
    conn.execute(
        "UPDATE plans SET content=? WHERE id=?",
        (json.dumps(content), plan_id)
    )
    conn.commit()
    conn.close()


def mark_plan_sent(plan_id):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE plans SET status='sent', sent_at=? WHERE id=?",
        (now, plan_id)
    )
    conn.commit()
    conn.close()


def get_next_version(client_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT MAX(version) as v FROM plans WHERE client_id=?",
        (client_id,)
    ).fetchone()
    conn.close()
    return (row["v"] or 0) + 1


# ── Feedback CRUD ─────────────────────────────────────────────────────────────

def save_feedback(plan_id, client_id, answers):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO feedback (plan_id, client_id, answers, created_at)
        VALUES (?, ?, ?, ?)
    """, (plan_id, client_id, json.dumps(answers), now))
    fb_id = c.lastrowid
    conn.commit()
    conn.close()
    return fb_id


def get_feedback(plan_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM feedback WHERE plan_id=? ORDER BY created_at DESC",
        (plan_id,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["answers"] = json.loads(d["answers"])
        except Exception:
            pass
        result.append(d)
    return result


# ── Assistant Chat CRUD ───────────────────────────────────────────────────────

def create_chat(title="Neues Gespräch", client_id=None):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO assistant_chats (title, client_id, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """, (title, client_id, now, now))
    chat_id = c.lastrowid
    conn.commit()
    conn.close()
    return chat_id


def get_chat(chat_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM assistant_chats WHERE id=?", (chat_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_chats():
    conn = get_conn()
    rows = conn.execute(
        "SELECT ac.*, c.name as client_name FROM assistant_chats ac "
        "LEFT JOIN clients c ON ac.client_id = c.id "
        "ORDER BY ac.updated_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_chat_title(chat_id, title):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute("UPDATE assistant_chats SET title=?, updated_at=? WHERE id=?", (title, now, chat_id))
    conn.commit()
    conn.close()


def touch_chat(chat_id):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute("UPDATE assistant_chats SET updated_at=? WHERE id=?", (now, chat_id))
    conn.commit()
    conn.close()


def delete_chat(chat_id):
    conn = get_conn()
    conn.execute("DELETE FROM assistant_messages WHERE chat_id=?", (chat_id,))
    conn.execute("DELETE FROM assistant_chats WHERE id=?", (chat_id,))
    conn.commit()
    conn.close()


def add_message(chat_id, role, content):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO assistant_messages (chat_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (chat_id, role, content, now))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id


def get_messages(chat_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM assistant_messages WHERE chat_id=? ORDER BY created_at ASC",
        (chat_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Knowledge Docs CRUD ───────────────────────────────────────────────────────

def save_knowledge_doc(filename, content, file_size=0):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO knowledge_docs (filename, content, file_size, created_at)
        VALUES (?, ?, ?, ?)
    """, (filename, content, file_size, now))
    doc_id = c.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def list_knowledge_docs():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, filename, file_size, created_at, substr(content,1,200) as preview "
        "FROM knowledge_docs ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_knowledge_doc(doc_id):
    conn = get_conn()
    conn.execute("DELETE FROM knowledge_docs WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()


def get_all_knowledge_text():
    """Returns combined text from knowledge base + all uploaded docs."""
    conn = get_conn()
    kb_row = conn.execute(
        "SELECT content FROM knowledge_base ORDER BY id DESC LIMIT 1"
    ).fetchone()
    docs = conn.execute("SELECT filename, content FROM knowledge_docs").fetchall()
    conn.close()

    parts = []
    if kb_row:
        parts.append("=== WISSENSBASIS (Konzept & Regeln) ===\n" + kb_row["content"])
    for doc in docs:
        parts.append(f"=== DOKUMENT: {doc['filename']} ===\n{doc['content']}")
    return "\n\n".join(parts)


# ── Knowledge Base CRUD ───────────────────────────────────────────────────────

def get_knowledge_base():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM knowledge_base ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_knowledge_base(content):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    existing = conn.execute("SELECT id FROM knowledge_base LIMIT 1").fetchone()
    if existing:
        conn.execute("UPDATE knowledge_base SET content=?, updated_at=? WHERE id=?",
                     (content, now, existing["id"]))
    else:
        conn.execute("INSERT INTO knowledge_base (content, updated_at) VALUES (?, ?)",
                     (content, now))
    conn.commit()
    conn.close()

# ── Client Token (Portal Login) ───────────────────────────────────────────────

def get_or_create_client_token(client_id):
    """Returns existing token or creates a new one for the client."""
    import secrets
    conn = get_conn()
    row = conn.execute("SELECT * FROM client_tokens WHERE client_id=?", (client_id,)).fetchone()
    if row:
        conn.close()
        return dict(row)
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO client_tokens (client_id, token, created_at) VALUES (?, ?, ?)",
        (client_id, token, now)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM client_tokens WHERE client_id=?", (client_id,)).fetchone()
    conn.close()
    return dict(row)


def get_client_by_token(token):
    """Returns client dict if token is valid, else None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT c.* FROM clients c JOIN client_tokens ct ON c.id=ct.client_id WHERE ct.token=?",
        (token,)
    ).fetchone()
    if row:
        now = datetime.utcnow().isoformat()
        conn.execute("UPDATE client_tokens SET last_login=? WHERE token=?", (now, token))
        conn.commit()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["pillars"] = json.loads(d["pillars"])
    except Exception:
        d["pillars"] = [d["pillars"]]
    return d


def regenerate_client_token(client_id):
    """Creates a new token for the client (invalidates old one)."""
    import secrets
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    existing = conn.execute("SELECT id FROM client_tokens WHERE client_id=?", (client_id,)).fetchone()
    if existing:
        conn.execute("UPDATE client_tokens SET token=?, created_at=? WHERE client_id=?",
                     (token, now, client_id))
    else:
        conn.execute("INSERT INTO client_tokens (client_id, token, created_at) VALUES (?, ?, ?)",
                     (client_id, token, now))
    conn.commit()
    conn.close()
    return token


# ── Client Notes ──────────────────────────────────────────────────────────────

def add_client_note(client_id, text, category="allgemein"):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO client_notes (client_id, category, text, created_at) VALUES (?, ?, ?, ?)",
        (client_id, category, text, now)
    )
    note_id = c.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_client_notes(client_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM client_notes WHERE client_id=? ORDER BY created_at DESC",
        (client_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def flag_client_note(note_id, flagged=True):
    conn = get_conn()
    conn.execute("UPDATE client_notes SET flagged=? WHERE id=?", (1 if flagged else 0, note_id))
    conn.commit()
    conn.close()


def delete_client_note(note_id):
    conn = get_conn()
    conn.execute("DELETE FROM client_notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


# ── Exercise Weights ──────────────────────────────────────────────────────────

def save_exercise_weight(client_id, plan_id, week, day, exercise, weight, unit="kg", reps_done=None):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM exercise_weights WHERE client_id=? AND plan_id=? AND week=? AND day=? AND exercise=?",
        (client_id, plan_id, week, day, exercise)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE exercise_weights SET weight=?, unit=?, reps_done=?, updated_at=? WHERE id=?",
            (weight, unit, reps_done, now, existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO exercise_weights (client_id, plan_id, week, day, exercise, weight, unit, reps_done, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (client_id, plan_id, week, day, exercise, weight, unit, reps_done, now)
        )
    conn.commit()
    conn.close()


def get_exercise_weights(client_id, plan_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM exercise_weights WHERE client_id=? AND plan_id=? ORDER BY week, day, exercise",
        (client_id, plan_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Client Messages (Chat) ────────────────────────────────────────────────────

def add_client_message(client_id, text, sender="client", file_path=None):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO client_messages (client_id, sender, text, file_path, created_at) VALUES (?, ?, ?, ?, ?)",
        (client_id, sender, text, file_path, now)
    )
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id


def get_client_messages(client_id, limit=100):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM client_messages WHERE client_id=? ORDER BY created_at ASC LIMIT ?",
        (client_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_messages_read(client_id):
    conn = get_conn()
    conn.execute(
        "UPDATE client_messages SET read_by_coach=1 WHERE client_id=? AND sender='client'",
        (client_id,)
    )
    conn.commit()
    conn.close()


def get_unread_count(client_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM client_messages WHERE client_id=? AND sender='client' AND read_by_coach=0",
        (client_id,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ── Released Pillars ──────────────────────────────────────────────────────────

def get_released_pillars(client_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT pillars FROM client_released_pillars WHERE client_id=?", (client_id,)
    ).fetchone()
    conn.close()
    if not row:
        return []
    try:
        return json.loads(row["pillars"])
    except Exception:
        return []


def set_released_pillars(client_id, pillars):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM client_released_pillars WHERE client_id=?", (client_id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE client_released_pillars SET pillars=?, updated_at=? WHERE client_id=?",
            (json.dumps(pillars), now, client_id)
        )
    else:
        conn.execute(
            "INSERT INTO client_released_pillars (client_id, pillars, updated_at) VALUES (?, ?, ?)",
            (client_id, json.dumps(pillars), now)
        )
    conn.commit()
    conn.close()
