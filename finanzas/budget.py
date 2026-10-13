"""Cálculos de resumen mensual, objetivos y gasto diario disponible."""

import calendar
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .db import SAVINGS, TOTAL


def month_bounds(month: str) -> tuple[date, date]:
    y, m = map(int, month.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def spending(df: pd.DataFrame) -> float:
    """Gasto neto (positivo) de los movimientos de tipo gasto."""
    return float(-df.loc[df["kind"] == "gasto", "amount"].sum())


def income(df: pd.DataFrame) -> float:
    return float(df.loc[df["kind"] == "ingreso", "amount"].sum())


def monthly_overview(df: pd.DataFrame) -> pd.DataFrame:
    """Ingresos, gastos, inversión neta y ahorro por mes."""
    if df.empty:
        return pd.DataFrame(columns=["month", "ingresos", "gastos", "inversion", "ahorro", "tasa_ahorro"])
    g = df.groupby(["month", "kind"])["amount"].sum().unstack(fill_value=0.0)
    out = pd.DataFrame({
        "ingresos": g.get("ingreso", 0.0),
        "gastos": -g.get("gasto", 0.0),
        "inversion": -g.get("inversion", 0.0),
    })
    out["ahorro"] = out["ingresos"] - out["gastos"]
    out["tasa_ahorro"] = (out["ahorro"] / out["ingresos"].where(out["ingresos"] > 0)).fillna(0.0)
    return out.reset_index().sort_values("month")


def spending_by_category(df: pd.DataFrame) -> pd.DataFrame:
    g = df[df["kind"] == "gasto"].groupby("category")["amount"].sum()
    out = (-g).rename("gasto").reset_index()
    return out[out["gasto"] > 0].sort_values("gasto", ascending=False)


def expected_income(df: pd.DataFrame, month: str) -> float:
    """Ingresos del mes; si todavía no han llegado, la media de los 3 meses anteriores."""
    this = income(df[df["month"] == month])
    prev = monthly_overview(df[df["month"] < month]).tail(3)
    avg = float(prev["ingresos"].mean()) if not prev.empty else 0.0
    return max(this, avg)


def _fixed(df: pd.DataFrame) -> pd.Series:
    return df["fixed"].astype(bool) if "fixed" in df else pd.Series(False, index=df.index)


def expected_fixed(df: pd.DataFrame, month: str) -> tuple[float, float]:
    """(gastos fijos ya pagados este mes, gastos fijos previstos para el mes).

    Lo previsto es lo ya pagado o, si es mayor, la media de los 3 meses anteriores
    (así el alquiler se reserva aunque todavía no se haya cobrado)."""
    fx = df[_fixed(df)]
    paid = spending(fx[fx["month"] == month])
    prev_months = sorted(m for m in df["month"].unique() if m < month)[-3:]
    avg = sum(spending(fx[fx["month"] == m]) for m in prev_months) / len(prev_months) if prev_months else 0.0
    return paid, max(paid, avg)


@dataclass
class DailyPlan:
    month: str
    budget: float | None          # gasto máximo del mes (None si no hay objetivo)
    budget_source: str            # de dónde sale el presupuesto
    spent: float                  # gastado en el mes (fijo + variable)
    fixed_paid: float             # gastos fijos ya pagados
    fixed_expected: float         # gastos fijos previstos en el mes
    variable_budget: float | None # presupuesto para el día a día (sin fijos)
    variable_spent: float
    spent_today: float            # gasto variable de hoy
    days_total: int
    days_left: int                # días que quedan, incluyendo hoy
    remaining: float | None       # lo que queda para gasto variable
    per_day: float | None         # lo que puedes gastar cada día desde hoy
    today_left: float | None      # lo que te queda hoy
    pace: float | None            # gasto variable "ideal" acumulado a final de hoy
    categories: pd.DataFrame = field(default_factory=pd.DataFrame)


def daily_plan(df: pd.DataFrame, budgets: dict[str, float], month: str, today: date) -> DailyPlan:
    """Cuánto puedes gastar al día para cumplir el objetivo del mes.

    Los gastos fijos (alquiler, facturas...) se reservan del presupuesto; el resto
    se reparte entre los días que quedan. El presupuesto diario se calcula con lo
    gastado *antes* de hoy, así no cambia durante el día.
    """
    start, end = month_bounds(month)
    mdf = df[df["month"] == month]
    var = mdf[~_fixed(mdf)]
    days_total = (end - start).days + 1
    ref = min(max(today, start), end)
    days_left = (end - ref).days + 1 if today <= end else 0

    spent = spending(mdf)
    variable_spent = spending(var)
    var_before = spending(var[var["date"].dt.date < ref])
    spent_today = spending(var[var["date"].dt.date == ref]) if today <= end else 0.0
    fixed_paid, fixed_expected = expected_fixed(df, month)

    if TOTAL in budgets:
        budget, source = budgets[TOTAL], "límite de gasto mensual"
    elif SAVINGS in budgets:
        inc = expected_income(df, month)
        budget = max(inc - budgets[SAVINGS], 0.0)
        source = f"ingresos previstos ({inc:,.2f} €) − objetivo de ahorro ({budgets[SAVINGS]:,.2f} €)"
    else:
        cat_sum = sum(v for k, v in budgets.items() if k not in (TOTAL, SAVINGS))
        budget, source = (cat_sum, "suma de los límites por categoría") if cat_sum else (None, "sin objetivo")

    variable_budget = remaining = per_day = today_left = pace = None
    if budget is not None:
        variable_budget = max(budget - fixed_expected, 0.0)
        remaining = variable_budget - variable_spent
        if days_left > 0:
            per_day = max(variable_budget - var_before, 0.0) / days_left
            today_left = per_day - spent_today
        pace = variable_budget * ((ref - start).days + 1) / days_total

    rows = []
    by_cat = spending_by_category(mdf).set_index("category")["gasto"]
    for cat, limit in budgets.items():
        if cat in (TOTAL, SAVINGS):
            continue
        used = float(by_cat.get(cat, 0.0))
        rows.append({
            "categoria": cat, "limite": limit, "gastado": used, "restante": limit - used,
            "uso": used / limit if limit else 0.0,
            "por_dia": max(limit - used, 0.0) / days_left if days_left else 0.0,
        })
    cats = pd.DataFrame(rows, columns=["categoria", "limite", "gastado", "restante", "uso", "por_dia"])

    return DailyPlan(month, budget, source, spent, fixed_paid, fixed_expected, variable_budget,
                     variable_spent, spent_today, days_total, days_left, remaining, per_day,
                     today_left, pace, cats.sort_values("uso", ascending=False))


def cumulative_spending(df: pd.DataFrame, month: str, variable_only: bool = True) -> pd.DataFrame:
    """Gasto (variable) acumulado día a día en el mes, para compararlo con el ritmo ideal."""
    start, end = month_bounds(month)
    mdf = df[(df["month"] == month) & (df["kind"] == "gasto")]
    if variable_only:
        mdf = mdf[~_fixed(mdf)]
    daily = (-mdf.groupby(mdf["date"].dt.date)["amount"].sum())
    idx = pd.date_range(start, end, freq="D").date
    daily = daily.reindex(idx, fill_value=0.0)
    return pd.DataFrame({"dia": pd.to_datetime(idx), "gasto": daily.values, "acumulado": daily.cumsum().values})
