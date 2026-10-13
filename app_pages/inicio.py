"""Inicio: cuánto puedes gastar hoy, el mes de un vistazo y los últimos movimientos."""

import streamlit as st

from finanzas import budget
from finanzas.ui import charts, data, fmt
from finanzas.ui import components as ui

d = data.load_or_stop("Inicio")
month = ui.page_header("Inicio", d.months)
m = data.for_month(d, month)
plan = m.plan
inc, spent = budget.income(m.tx), budget.spending(m.tx)
saved = inc - spent

if month == d.current and plan.per_day is not None:
    ui.hero("Puedes gastar hoy", fmt.eur(plan.today_left),
            sub=f"Presupuesto diario {fmt.eur(plan.per_day)} · quedan {plan.days_left} días")
    ui.pace_bar(plan)
elif month == d.current:
    ui.hero("Puedes gastar hoy", "Sin objetivo",
            sub="Define un objetivo de ahorro o un límite de gasto y te diremos cuánto puedes gastar cada día.")
    if st.button("Definir objetivo", type="primary"):
        st.switch_page("app_pages/objetivos.py")
else:
    ui.hero(f"Ahorro en {fmt.month_name(month, year=False)}", fmt.signed(saved),
            sub=f"{fmt.pct(saved / inc)} de los ingresos" if inc > 0 else None)

worth = None
if not d.snapshots.empty:
    last = d.snapshots.iloc[-1]
    worth = (last["cash"] or 0) + (last["invested"] or 0)
ui.stat_row([
    {"label": "Ingresos", "value": fmt.eur(inc)},
    {"label": "Gastos", "value": fmt.eur(spent)},
    {"label": "Ahorro", "value": fmt.signed(saved),
     "sub": f"{fmt.pct(saved / inc)} de los ingresos" if inc > 0 else None},
    {"label": "Patrimonio", "value": fmt.eur(worth),
     "sub": f"{fmt.eur(last['invested'])} invertido" if worth is not None else None},
])

ui.section("Últimos movimientos", action=("Ver todos", "app_pages/movimientos.py"))
ui.list_block([ui.tx_row(r) for _, r in m.tx.head(5).iterrows()],
              empty="Aún no hay movimientos este mes.")

ui.section("Últimos 12 meses")
ov = budget.monthly_overview(d.tx).tail(12)
if ov.empty:
    ui.empty_state("Aún no hay meses que comparar.")
else:
    charts.show(charts.overview(ov), key="overview")
