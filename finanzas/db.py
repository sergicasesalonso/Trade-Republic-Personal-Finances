"""Base de datos SQLite local con movimientos, categorías, reglas y objetivos."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from . import config
from .categories import DEFAULT_CATEGORIES, DEFAULT_FIXED, categorize

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    date            TEXT NOT NULL,
    title           TEXT,
    subtitle        TEXT,
    event_type      TEXT,
    amount          REAL NOT NULL,
    currency        TEXT,
    category        TEXT NOT NULL,
    category_manual INTEGER NOT NULL DEFAULT 0,
    note            TEXT
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);

CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('gasto','ingreso','inversion','excluido')),
    fixed INTEGER NOT NULL DEFAULT 0  -- gasto fijo (alquiler, facturas...)
);

CREATE TABLE IF NOT EXISTS rules (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern  TEXT NOT NULL,
    category TEXT NOT NULL
);

-- Objetivos mensuales. month = 'YYYY-MM' o '*' (se aplica a todos los meses
-- que no tengan uno propio). category = nombre de categoría, '__TOTAL__'
-- (límite de gasto total) o '__AHORRO__' (objetivo de ahorro).
CREATE TABLE IF NOT EXISTS budgets (
    month    TEXT NOT NULL,
    category TEXT NOT NULL,
    amount   REAL NOT NULL,
    PRIMARY KEY (month, category)
);

CREATE TABLE IF NOT EXISTS snapshots (
    taken_at TEXT PRIMARY KEY,
    cash     REAL,
    invested REAL
);

CREATE TABLE IF NOT EXISTS positions (
    isin      TEXT PRIMARY KEY,
    name      TEXT,
    quantity  REAL,
    price     REAL,
    avg_cost  REAL,
    net_value REAL
);
"""

TOTAL = "__TOTAL__"
SAVINGS = "__AHORRO__"


@contextmanager
def connect(path: Path | None = None):
    path = Path(path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO categories(name, kind, fixed) VALUES (?, ?, ?)",
            [(n, k, int(n in DEFAULT_FIXED)) for n, k in DEFAULT_CATEGORIES.items()],
        )
        yield conn
        conn.commit()
    finally:
        conn.close()


# --- Movimientos -----------------------------------------------------------

def user_rules(conn) -> list[tuple[str, str]]:
    return [(r["pattern"], r["category"]) for r in conn.execute("SELECT pattern, category FROM rules ORDER BY id")]


def upsert_transactions(conn, rows: list[dict]) -> tuple[int, int]:
    """Inserta o actualiza movimientos. Respeta las categorías puestas a mano."""
    rules = user_rules(conn)
    new = updated = 0
    for r in rows:
        existing = conn.execute(
            "SELECT category, category_manual FROM transactions WHERE id = ?", (r["id"],)
        ).fetchone()
        if existing and existing["category_manual"]:
            category = existing["category"]
        else:
            category = categorize(r["title"], r["event_type"], r["amount"], rules)
        conn.execute(
            """INSERT INTO transactions(id, timestamp, date, title, subtitle, event_type,
                                        amount, currency, category)
               VALUES (:id, :timestamp, :date, :title, :subtitle, :event_type,
                       :amount, :currency, :category)
               ON CONFLICT(id) DO UPDATE SET
                   timestamp=excluded.timestamp, date=excluded.date, title=excluded.title,
                   subtitle=excluded.subtitle, event_type=excluded.event_type,
                   amount=excluded.amount, currency=excluded.currency,
                   category=excluded.category""",
            {**r, "category": category},
        )
        if existing:
            updated += 1
        else:
            new += 1
        conn.execute("INSERT OR IGNORE INTO categories(name, kind) VALUES (?, 'gasto')", (category,))
    return new, updated


def recategorize_all(conn) -> int:
    """Vuelve a aplicar las reglas a todos los movimientos no editados a mano."""
    rules = user_rules(conn)
    rows = conn.execute(
        "SELECT id, title, event_type, amount FROM transactions WHERE category_manual = 0"
    ).fetchall()
    for r in rows:
        cat = categorize(r["title"], r["event_type"], r["amount"], rules)
        conn.execute("UPDATE transactions SET category = ? WHERE id = ?", (cat, r["id"]))
    return len(rows)


def set_category(conn, tx_id: str, category: str) -> None:
    conn.execute(
        "UPDATE transactions SET category = ?, category_manual = 1 WHERE id = ?", (category, tx_id)
    )


def transactions_df(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        """SELECT t.*, COALESCE(c.kind, 'gasto') AS kind, COALESCE(c.fixed, 0) AS fixed
           FROM transactions t LEFT JOIN categories c ON c.name = t.category
           ORDER BY t.timestamp DESC""",
        conn,
    )
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df


# --- Categorías y reglas ---------------------------------------------------

def categories_df(conn) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT name, kind, fixed FROM categories ORDER BY kind, name", conn)
    df["fixed"] = df["fixed"].astype(bool)
    return df


def save_category(conn, name: str, kind: str, fixed: bool = False) -> None:
    conn.execute(
        "INSERT INTO categories(name, kind, fixed) VALUES (?, ?, ?) "
        "ON CONFLICT(name) DO UPDATE SET kind=excluded.kind, fixed=excluded.fixed",
        (name, kind, int(bool(fixed))),
    )


def rules_df(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT id, pattern, category FROM rules ORDER BY id", conn)


def add_rule(conn, pattern: str, category: str) -> None:
    conn.execute("INSERT INTO rules(pattern, category) VALUES (?, ?)", (pattern, category))


def delete_rule(conn, rule_id: int) -> None:
    conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))


# --- Objetivos -------------------------------------------------------------

def budgets_for_month(conn, month: str) -> dict[str, float]:
    """Objetivos efectivos de un mes: los genéricos ('*') sobrescritos por los del mes."""
    out: dict[str, float] = {}
    for m in ("*", month):
        for r in conn.execute("SELECT category, amount FROM budgets WHERE month = ?", (m,)):
            out[r["category"]] = r["amount"]
    return out


def set_budget(conn, month: str, category: str, amount: float | None) -> None:
    if amount is None or amount <= 0:
        conn.execute("DELETE FROM budgets WHERE month = ? AND category = ?", (month, category))
    else:
        conn.execute(
            "INSERT INTO budgets(month, category, amount) VALUES (?, ?, ?) "
            "ON CONFLICT(month, category) DO UPDATE SET amount=excluded.amount",
            (month, category, amount),
        )


# --- Cartera ---------------------------------------------------------------

def save_portfolio(conn, positions: list[dict], cash: float | None, taken_at: str) -> None:
    conn.execute("DELETE FROM positions")
    conn.executemany(
        "INSERT INTO positions(isin, name, quantity, price, avg_cost, net_value) "
        "VALUES (:isin, :name, :quantity, :price, :avg_cost, :net_value)",
        positions,
    )
    invested = sum(p["net_value"] or 0 for p in positions)
    conn.execute(
        "INSERT OR REPLACE INTO snapshots(taken_at, cash, invested) VALUES (?, ?, ?)",
        (taken_at, cash, invested),
    )


def positions_df(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM positions ORDER BY net_value DESC", conn)


def snapshots_df(conn) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM snapshots ORDER BY taken_at", conn)
    df["taken_at"] = pd.to_datetime(df["taken_at"])
    return df
