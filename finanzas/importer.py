"""Convierte los eventos del timeline de Trade Republic (all_events.json de pytr)
y el CSV de cartera en filas para la base de datos."""

import csv
import json
from datetime import datetime
from pathlib import Path

# Eventos que no son movimientos de dinero reales.
SKIP_EVENT_TYPES = {
    "CARD_FAILED_TRANSACTION",
    "CARD_VERIFICATION",
    "CARD_SUCCESSFUL_VERIFICATION",
    "CARD_FAILED_VERIFICATION",
}
SKIP_STATUSES = {"CANCELED", "CANCELLED", "FAILED", "REJECTED"}


def parse_timestamp(ts: str) -> datetime:
    """'2024-05-03T10:21:44.123+0000' -> datetime en hora local."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    elif len(ts) > 5 and ts[-5] in "+-" and ts[-3] != ":":
        ts = ts[:-2] + ":" + ts[-2:]
    return datetime.fromisoformat(ts).astimezone()


def event_to_row(event: dict) -> dict | None:
    amount = (event.get("amount") or {}).get("value")
    if amount in (None, 0):
        return None
    event_type = (event.get("eventType") or "").upper()
    if event_type in SKIP_EVENT_TYPES:
        return None
    if (event.get("status") or "").upper() in SKIP_STATUSES:
        return None
    try:
        when = parse_timestamp(event["timestamp"])
    except (KeyError, ValueError):
        return None
    return {
        "id": str(event["id"]),
        "timestamp": when.isoformat(),
        "date": when.date().isoformat(),
        "title": event.get("title") or "",
        "subtitle": event.get("subtitle") or "",
        "event_type": event_type,
        "amount": float(amount),
        "currency": (event.get("amount") or {}).get("currency") or "EUR",
    }


def load_events(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        events = json.load(f)
    rows = [event_to_row(e) for e in events]
    return [r for r in rows if r]


def _num(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    # pytr puede localizar decimales (1.234,56); normalizamos.
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    return float(value)


def load_portfolio_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)  # cabecera: Name;ISIN;quantity;price;avgCost;netValue
        out = []
        for row in reader:
            if len(row) < 6:
                continue
            out.append({
                "name": row[0],
                "isin": row[1],
                "quantity": _num(row[2]),
                "price": _num(row[3]),
                "avg_cost": _num(row[4]),
                "net_value": _num(row[5]),
            })
    return out
