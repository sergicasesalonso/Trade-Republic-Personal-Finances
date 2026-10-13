"""Genera datos de ejemplo con el mismo formato que pytr, para probar el dashboard
sin conectar tu cuenta. Se guardan en data/demo/ (nunca en tu base real)."""

import json
import random
from datetime import date, datetime, timedelta

from . import config, db
from .importer import load_events

MERCHANTS = [
    ("Mercadona", 15, 90, 8), ("Lidl", 10, 60, 4), ("Bonpreu", 8, 45, 3),
    ("Glovo", 12, 35, 3), ("Bar Pepe", 3, 15, 6), ("Restaurante La Tasca", 20, 60, 2),
    ("Starbucks", 4, 8, 3), ("TMB", 11.35, 11.35, 2), ("Repsol", 40, 70, 2),
    ("Uber", 8, 25, 1), ("Amazon", 10, 120, 3), ("Zara", 20, 80, 1),
    ("Netflix", 12.99, 12.99, 1), ("Spotify", 10.99, 10.99, 1), ("Basic-Fit", 29.99, 29.99, 1),
    ("Farmacia Central", 5, 30, 1), ("Iberdrola", 45, 80, 1), ("Movistar", 35, 35, 1),
    ("Ryanair", 40, 150, 0.3), ("Cine Yelmo", 9, 20, 0.7),
]


def _event(eid: str, when: datetime, title: str, event_type: str, amount: float, subtitle: str = "") -> dict:
    return {
        "id": eid,
        "timestamp": when.strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
        "title": title,
        "subtitle": subtitle,
        "eventType": event_type,
        "status": "EXECUTED",
        "amount": {"currency": "EUR", "value": round(amount, 2)},
    }


def generate_events(months: int = 6, seed: int = 7) -> list[dict]:
    rnd = random.Random(seed)
    today = date.today()
    first = date(today.year, today.month, 1)
    for _ in range(months - 1):
        first = (first - timedelta(days=1)).replace(day=1)
    events, n = [], 0

    def add(day: date, title: str, etype: str, amount: float, subtitle: str = "") -> None:
        nonlocal n
        n += 1
        when = datetime(day.year, day.month, day.day, rnd.randint(8, 21), rnd.randint(0, 59))
        events.append(_event(f"demo-{n:05d}", when, title, etype, amount, subtitle))

    d = first
    while d <= today:
        if d.day == 1:
            add(d, "Empresa SL", "INCOMING_TRANSFER", 2150.0, "Nómina")
            add(d, "Alquiler piso", "OUTGOING_TRANSFER", -750.0)
            add(d, "Interés", "INTEREST_PAYOUT", rnd.uniform(4, 9))
        if d.day == 2:
            add(d, "MSCI World", "TRADING_SAVINGSPLAN_EXECUTED", -300.0, "Plan de inversión ejecutado")
        if d.day == 15 and rnd.random() < 0.5:
            add(d, "Apple Inc.", "CREDIT", rnd.uniform(3, 12), "Dividendo")
        for title, lo, hi, per_month in MERCHANTS:
            if rnd.random() < per_month / 30:
                add(d, title, "CARD_SUCCESSFUL_TRANSACTION", -rnd.uniform(lo, hi))
        if rnd.random() < 0.03:
            add(d, "Cajero", "CARD_SUCCESSFUL_ATM_WITHDRAWAL", -rnd.choice([20, 50, 100]))
        d += timedelta(days=1)
    return events


def build_demo() -> None:
    demo_dir = config.DATA_DIR / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    events_path = demo_dir / "all_events.json"
    events_path.write_text(json.dumps(generate_events(), indent=2), encoding="utf-8")
    db_path = demo_dir / "finanzas.db"
    db_path.unlink(missing_ok=True)
    with db.connect(db_path) as conn:
        db.upsert_transactions(conn, load_events(events_path))
        db.save_portfolio(conn, [
            {"isin": "IE00B4L5Y983", "name": "iShares Core MSCI World", "quantity": 42.5,
             "price": 98.4, "avg_cost": 85.1, "net_value": 4182.0},
            {"isin": "US0378331005", "name": "Apple Inc.", "quantity": 6.0,
             "price": 210.3, "avg_cost": 172.0, "net_value": 1261.8},
            {"isin": "XF000BTC0017", "name": "Bitcoin", "quantity": 0.012,
             "price": 58000.0, "avg_cost": 41000.0, "net_value": 696.0},
        ], cash=3120.55, taken_at=datetime.now().isoformat(timespec="seconds"))
        db.set_budget(conn, "*", db.SAVINGS, 500)
        db.set_budget(conn, "*", "Restaurantes y bares", 180)
        db.set_budget(conn, "*", "Supermercado", 300)
        db.set_budget(conn, "*", "Compras", 150)
    print(f"Datos de ejemplo creados en {db_path}")


if __name__ == "__main__":
    build_demo()
