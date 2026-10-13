"""Formato de cifras y fechas en español."""

from datetime import date

import pandas as pd

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MINUS = "−"


def _num(x: float, decimals: int = 2) -> str:
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def eur(x: float | None) -> str:
    """1.234,56 € (con − tipográfico si es negativo)."""
    if x is None or pd.isna(x):
        return "—"
    s = _num(abs(x))
    return f"{MINUS}{s} €" if x < 0 and round(x, 2) != 0 else f"{s} €"


def signed(x: float | None) -> str:
    """Importe con signo explícito: +12,30 € / −12,30 €."""
    if x is None or pd.isna(x):
        return "—"
    if round(x, 2) == 0:
        return "0,00 €"
    return f"{'+' if x > 0 else MINUS}{_num(abs(x))} €"


def pct(x: float | None, decimals: int = 1, sign: bool = False) -> str:
    """Fracción como porcentaje: 0.123 → 12,3 %."""
    if x is None or pd.isna(x):
        return "—"
    s = f"{_num(abs(x) * 100, decimals)} %"
    if sign and round(x * 100, decimals) != 0:
        return ("+" if x > 0 else MINUS) + s
    return f"{MINUS}{s}" if x < 0 and round(x * 100, decimals) != 0 else s


def month_name(month: str, year: bool = True) -> str:
    """'2026-10' → 'octubre 2026'."""
    y, m = map(int, month.split("-"))
    return f"{MONTHS[m - 1]} {y}" if year else MONTHS[m - 1]


def day_label(d: date, today: date) -> str:
    """Hoy, Ayer, 13 de octubre (con año si no es el actual)."""
    if d == today:
        return "Hoy"
    if (today - d).days == 1:
        return "Ayer"
    s = f"{d.day} de {MONTHS[d.month - 1]}"
    return s if d.year == today.year else f"{s} de {d.year}"


def short_date(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1][:3]}"


def initials(text: str | None) -> str:
    """Dos letras para el avatar: 'Bar Pepe' → 'BP', 'Mercadona' → 'ME'."""
    words = [w for w in "".join(c if c.isalnum() else " " for c in (text or "")).split() if w]
    if not words:
        return "·"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()
