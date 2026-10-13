"""Objetivos: cuánto puedes gastar al día, ritmo del mes y edición de objetivos."""

import pandas as pd
import streamlit as st

from finanzas import budget, db
from finanzas.ui import charts, data, fmt
from finanzas.ui import components as ui

d = data.load_or_stop("Objetivos")
month = ui.page_header("Objetivos", d.months)
m = data.for_month(d, month)
plan = m.plan

if plan.budget is None:
    ui.hero("Al día desde hoy", "Sin objetivo",
            sub="Define abajo un objetivo de ahorro o un límite de gasto para calcular cuánto puedes gastar al día.")
else:
    if plan.per_day is not None:
        ui.hero("Al día desde hoy", fmt.eur(plan.per_day),
                sub=f"Te quedan {fmt.eur(plan.remaining)} para el día a día · {plan.days_left} días")
    else:
        ui.hero("Te sobró del día a día", fmt.signed(plan.remaining),
                tone=ui.tone_of(plan.remaining), sub="Este mes ya ha terminado.")
    ui.pace_bar(plan)

    source = ("Límite de gasto mensual" if db.TOTAL in m.budgets
              else "Ingresos previstos menos ahorro" if db.SAVINGS in m.budgets
              else "Suma de los límites por categoría")
    ui.stat_row([
        {"label": "Presupuesto del mes", "value": fmt.eur(plan.budget), "sub": source},
        {"label": "Gastos fijos previstos", "value": fmt.eur(plan.fixed_expected),
         "sub": f"{fmt.eur(plan.fixed_paid)} ya pagados"},
        {"label": "Para el día a día", "value": fmt.eur(plan.variable_budget),
         "sub": f"{fmt.eur(plan.variable_spent)} gastados"},
    ])

    ui.section("Ritmo del mes")
    cum = budget.cumulative_spending(d.tx, month)
    cum["ideal"] = plan.variable_budget * (pd.Series(range(1, len(cum) + 1)) / len(cum)).values
    today = pd.Timestamp(d.today) if month == d.current else None
    charts.show(charts.cumulative(cum, today), key="cumulative")

    if not plan.categories.empty:
        ui.section("Límites por categoría")
        rows = []
        for r in plan.categories.itertuples(index=False):
            over = r.restante < 0
            sub = (f"Te has pasado {fmt.eur(-r.restante)}" if over
                   else f"Quedan {fmt.eur(r.restante)} · {fmt.eur(r.por_dia)} al día")
            rows.append(ui.list_row(r.categoria, sub, fmt.eur(r.gastado), amount_sub=f"de {fmt.eur(r.limite)}",
                                    bar=r.uso, bar_tone="neg" if over else None))
        ui.list_block(rows)

ui.section("Editar objetivos")
with st.container(key="surface_goals", gap="medium"):
    scope = st.segmented_control(
        "Aplicar a", ["*", month], default="*", required=True, key="goal_scope",
        format_func=lambda s: "Todos los meses" if s == "*" else f"Solo {fmt.month_name(month)}",
        help="Los objetivos de un mes concreto sustituyen a los generales.")
    with db.connect(d.path) as conn:
        saved = {r["category"]: r["amount"]
                 for r in conn.execute("SELECT category, amount FROM budgets WHERE month = ?", (scope,))}
    with st.form(f"budgets_{scope}", border=False):
        c1, c2 = st.columns(2)
        sav = c1.number_input("Objetivo de ahorro mensual (€)", min_value=0.0, step=50.0,
                              value=float(saved.get(db.SAVINGS, 0.0)),
                              help="Presupuesto = ingresos previstos − ahorro.")
        tot = c2.number_input("Límite de gasto total (€, opcional)", min_value=0.0, step=50.0,
                              value=float(saved.get(db.TOTAL, 0.0)),
                              help="Si lo pones, tiene prioridad sobre el objetivo de ahorro.")
        ui.note("Límites por categoría. Deja 0 para no poner límite.")
        cols = st.columns(3)
        per_cat = {name: cols[i % 3].number_input(name, min_value=0.0, step=10.0,
                                                  value=float(saved.get(name, 0.0)), key=f"b_{scope}_{name}")
                   for i, name in enumerate(d.spending_names)}
        if st.form_submit_button("Guardar objetivos", type="primary"):
            with db.connect(d.path) as conn:
                db.set_budget(conn, scope, db.SAVINGS, sav)
                db.set_budget(conn, scope, db.TOTAL, tot)
                for name, val in per_cat.items():
                    db.set_budget(conn, scope, name, val)
            st.toast("Objetivos guardados.")
            st.rerun()
