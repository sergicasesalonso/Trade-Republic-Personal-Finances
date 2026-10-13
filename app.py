"""Dashboard de finanzas personales. Ejecuta: streamlit run app.py"""

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from finanzas import budget, config, db
from finanzas.categories import KINDS

st.set_page_config(page_title="Mis finanzas", page_icon="💶", layout="wide")


def eur(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "—"
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


# --- Origen de datos ----------------------------------------------------------
demo_db = config.DATA_DIR / "demo" / "finanzas.db"
real_exists = config.DB_PATH.exists()
with st.sidebar:
    st.title("💶 Mis finanzas")
    use_demo = st.toggle("Usar datos de ejemplo", value=not real_exists,
                         help="Genera los datos con `python -m finanzas.sync --demo`.")
DB = demo_db if use_demo else config.DB_PATH

if not DB.exists():
    st.warning("Todavía no hay datos.")
    st.markdown(
        "1. Inicia sesión una vez en Trade Republic (te pedirá teléfono, PIN y código 2FA):\n"
        "   ```\n   pytr login --store_credentials\n   ```\n"
        "2. Descarga tus movimientos:\n"
        "   ```\n   python -m finanzas.sync\n   ```\n"
        "O prueba primero con datos de ejemplo: `python -m finanzas.sync --demo`."
    )
    st.stop()


def load():
    with db.connect(DB) as conn:
        return (db.transactions_df(conn), db.categories_df(conn), db.rules_df(conn),
                db.positions_df(conn), db.snapshots_df(conn))


tx, cats, rules, positions, snapshots = load()
if tx.empty:
    st.info("La base de datos no tiene movimientos todavía. Ejecuta `python -m finanzas.sync`.")
    st.stop()

today = date.today()
months = sorted(tx["month"].unique(), reverse=True)
current = today.strftime("%Y-%m")
if current not in months:
    months = [current] + months

with st.sidebar:
    month = st.selectbox("Mes", months, index=0)
    st.caption(f"{len(tx)} movimientos · último: {tx['date'].max():%d/%m/%Y}")
    if not snapshots.empty:
        st.caption(f"Cartera actualizada: {snapshots['taken_at'].max():%d/%m/%Y %H:%M}")

with db.connect(DB) as conn:
    budgets = db.budgets_for_month(conn, month)

mtx = tx[tx["month"] == month]
plan = budget.daily_plan(tx, budgets, month, today)
spending_names = cats.loc[cats["kind"] == "gasto", "name"].tolist()

tab_res, tab_cat, tab_obj, tab_tx, tab_port, tab_cfg = st.tabs(
    ["📊 Resumen", "🏷️ Gastos por categoría", "🎯 Objetivos y gasto diario",
     "📜 Movimientos", "📈 Cartera", "⚙️ Categorías y reglas"]
)

# --- Resumen ------------------------------------------------------------------
with tab_res:
    inc, spent = budget.income(mtx), budget.spending(mtx)
    inv = float(-mtx.loc[mtx["kind"] == "inversion", "amount"].sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos del mes", eur(inc))
    c2.metric("Gastos del mes", eur(spent))
    c3.metric("Ahorro", eur(inc - spent), f"{(inc - spent) / inc:.0%} de los ingresos" if inc > 0 else None)
    c4.metric("Invertido este mes", eur(inv))

    if plan.per_day is not None and month == current:
        c1, c2, c3 = st.columns(3)
        c1.metric("Puedes gastar hoy", eur(plan.today_left),
                  help="Presupuesto diario menos lo que ya has gastado hoy (sin contar gastos fijos).")
        c2.metric("Presupuesto diario hasta fin de mes", eur(plan.per_day),
                  f"{plan.days_left} días restantes", delta_color="off")
        c3.metric("Te queda este mes para el día a día", eur(plan.remaining))

    if not snapshots.empty:
        last = snapshots.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo en Trade Republic", eur(last["cash"]))
        c2.metric("Valor de la cartera", eur(last["invested"]))
        c3.metric("Patrimonio total", eur((last["cash"] or 0) + (last["invested"] or 0)))

    ov = budget.monthly_overview(tx).tail(12)
    fig = go.Figure()
    fig.add_bar(x=ov["month"], y=ov["ingresos"], name="Ingresos", marker_color="#2a9d8f")
    fig.add_bar(x=ov["month"], y=ov["gastos"], name="Gastos", marker_color="#e76f51")
    fig.add_scatter(x=ov["month"], y=ov["ahorro"], name="Ahorro", mode="lines+markers", line_color="#264653")
    fig.update_layout(barmode="group", title="Últimos 12 meses", height=380, legend_orientation="h",
                      yaxis_title="€", margin=dict(t=50, b=10))
    st.plotly_chart(fig, width="stretch")

    show = ov.rename(columns={"month": "Mes", "ingresos": "Ingresos", "gastos": "Gastos",
                              "inversion": "Inversión", "ahorro": "Ahorro", "tasa_ahorro": "% ahorro"})
    st.dataframe(show.sort_values("Mes", ascending=False), hide_index=True, width="stretch",
                 column_config={k: st.column_config.NumberColumn(format="%.2f €")
                                for k in ["Ingresos", "Gastos", "Inversión", "Ahorro"]}
                 | {"% ahorro": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})

# --- Gastos por categoría ---------------------------------------------------------
with tab_cat:
    bycat = budget.spending_by_category(mtx)
    if bycat.empty:
        st.info("No hay gastos en este mes.")
    else:
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = px.pie(bycat, names="category", values="gasto", hole=0.5, title=f"Gastos de {month}")
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(showlegend=False, height=420)
            st.plotly_chart(fig, width="stretch")
        with c2:
            prev = (pd.Period(month) - 1).strftime("%Y-%m")
            prevcat = budget.spending_by_category(tx[tx["month"] == prev]).set_index("category")["gasto"]
            bycat["mes anterior"] = bycat["category"].map(prevcat).fillna(0.0)
            bycat["diferencia"] = bycat["gasto"] - bycat["mes anterior"]
            bycat["límite"] = bycat["category"].map(budgets).astype(float)
            st.dataframe(bycat.rename(columns={"category": "Categoría", "gasto": "Gasto"}),
                         hide_index=True, width="stretch", height=420,
                         column_config={k: st.column_config.NumberColumn(format="%.2f €")
                                        for k in ["Gasto", "mes anterior", "diferencia", "límite"]})

        hist = tx[tx["kind"] == "gasto"].copy()
        hist = hist[hist["month"].isin(sorted(tx["month"].unique())[-12:])]
        hist = (-hist.groupby(["month", "category"])["amount"].sum()).rename("gasto").reset_index()
        fig = px.bar(hist, x="month", y="gasto", color="category", title="Evolución por categoría",
                     labels={"month": "Mes", "gasto": "€", "category": "Categoría"})
        fig.update_layout(height=420)
        st.plotly_chart(fig, width="stretch")

        st.subheader("Dónde más gastas este mes")
        top = mtx[mtx["kind"] == "gasto"].groupby("title")["amount"].agg(["sum", "count"])
        top = top.assign(sum=-top["sum"]).sort_values("sum", ascending=False).head(15).reset_index()
        st.dataframe(top.rename(columns={"title": "Comercio", "sum": "Total", "count": "Pagos"}),
                     hide_index=True, width="stretch",
                     column_config={"Total": st.column_config.NumberColumn(format="%.2f €")})

# --- Objetivos y gasto diario --------------------------------------------------
with tab_obj:
    st.subheader(f"Gasto diario · {month}")
    if plan.budget is None:
        st.info("Define abajo un objetivo de ahorro o un límite de gasto para calcular cuánto puedes gastar al día.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Presupuesto del mes", eur(plan.budget), help=f"Calculado a partir de: {plan.budget_source}")
        c2.metric("Gastos fijos previstos", eur(plan.fixed_expected), f"{eur(plan.fixed_paid)} ya pagados",
                  delta_color="off", help="Categorías marcadas como fijas (alquiler, facturas...). "
                  "Se reservan del presupuesto; si aún no se han cobrado se usa la media de los 3 meses anteriores.")
        c3.metric("Para el día a día", eur(plan.variable_budget),
                  f"{eur(plan.variable_spent)} gastados", delta_color="off")
        c4.metric("Al día (desde hoy)", eur(plan.per_day), f"{plan.days_left} días", delta_color="off")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Puedes gastar hoy", eur(plan.today_left))
        c2.metric("Restante del mes", eur(plan.remaining))
        c3.metric("Gasto total del mes", eur(plan.spent),
                  f"{plan.spent / plan.budget:.0%} del presupuesto" if plan.budget else None, delta_color="off")
        st.caption(f"Presupuesto calculado a partir de: {plan.budget_source}.")
        if plan.pace is not None and plan.days_left:
            diff = plan.pace - plan.variable_spent
            if diff >= 0:
                st.success(f"Vas {eur(diff)} por debajo del ritmo previsto. ¡Bien!")
            else:
                st.error(f"Vas {eur(-diff)} por encima del ritmo previsto. Para cumplir el objetivo, "
                         f"no gastes más de {eur(plan.per_day)} al día.")

        cum = budget.cumulative_spending(tx, month)
        cum["ideal"] = plan.variable_budget * (pd.Series(range(1, len(cum) + 1)) / len(cum)).values
        fig = go.Figure()
        fig.add_bar(x=cum["dia"], y=cum["gasto"], name="Gasto variable del día", marker_color="#f4a261", opacity=0.6)
        fig.add_scatter(x=cum["dia"], y=cum["acumulado"], name="Acumulado (sin fijos)", line_color="#e76f51")
        fig.add_scatter(x=cum["dia"], y=cum["ideal"], name="Ritmo ideal", line=dict(dash="dash", color="#2a9d8f"))
        fig.update_layout(height=380, legend_orientation="h", yaxis_title="€", margin=dict(t=20, b=10))
        st.plotly_chart(fig, width="stretch")

    if not plan.categories.empty:
        st.subheader("Límites por categoría")
        st.dataframe(plan.categories.rename(columns={
            "categoria": "Categoría", "limite": "Límite", "gastado": "Gastado",
            "restante": "Restante", "uso": "Uso", "por_dia": "Al día"}),
            hide_index=True, width="stretch",
            column_config={k: st.column_config.NumberColumn(format="%.2f €")
                           for k in ["Límite", "Gastado", "Restante", "Al día"]}
            | {"Uso": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})

    st.divider()
    st.subheader("Editar objetivos")
    scope = st.radio("Aplicar a", ["Todos los meses", f"Solo {month}"], horizontal=True,
                     help="Los objetivos de un mes concreto sustituyen a los generales.")
    scope_key = "*" if scope == "Todos los meses" else month
    with db.connect(DB) as conn:
        current_b = {r["category"]: r["amount"]
                     for r in conn.execute("SELECT category, amount FROM budgets WHERE month = ?", (scope_key,))}
    with st.form("budgets"):
        c1, c2 = st.columns(2)
        sav = c1.number_input("Objetivo de ahorro mensual (€)", min_value=0.0, step=50.0,
                              value=float(current_b.get(db.SAVINGS, 0.0)),
                              help="Presupuesto = ingresos previstos − ahorro.")
        tot = c2.number_input("Límite de gasto total (€, opcional)", min_value=0.0, step=50.0,
                              value=float(current_b.get(db.TOTAL, 0.0)),
                              help="Si lo pones, tiene prioridad sobre el objetivo de ahorro.")
        st.markdown("**Límites por categoría** (0 = sin límite)")
        cols = st.columns(3)
        per_cat = {}
        for i, name in enumerate(spending_names):
            per_cat[name] = cols[i % 3].number_input(name, min_value=0.0, step=10.0,
                                                     value=float(current_b.get(name, 0.0)), key=f"b_{name}")
        if st.form_submit_button("Guardar objetivos", type="primary"):
            with db.connect(DB) as conn:
                db.set_budget(conn, scope_key, db.SAVINGS, sav)
                db.set_budget(conn, scope_key, db.TOTAL, tot)
                for name, val in per_cat.items():
                    db.set_budget(conn, scope_key, name, val)
            st.success("Objetivos guardados.")
            st.rerun()

# --- Movimientos -------------------------------------------------------------------
with tab_tx:
    c1, c2, c3 = st.columns([2, 2, 1])
    q = c1.text_input("Buscar", placeholder="Comercio o concepto")
    sel_cats = c2.multiselect("Categorías", cats["name"].tolist())
    only_month = c3.toggle("Solo este mes", value=True)
    view = mtx if only_month else tx
    if q:
        view = view[view["title"].str.contains(q, case=False, na=False)
                    | view["subtitle"].str.contains(q, case=False, na=False)]
    if sel_cats:
        view = view[view["category"].isin(sel_cats)]
    st.caption(f"{len(view)} movimientos · total {eur(view['amount'].sum())}. "
               "Cambia la categoría en la tabla y pulsa Guardar.")
    edit = view[["id", "date", "title", "subtitle", "amount", "category", "event_type"]].copy()
    edited = st.data_editor(
        edit, hide_index=True, width="stretch", height=520, disabled=["id", "date", "title", "subtitle", "amount", "event_type"],
        column_config={
            "id": None,
            "date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "title": "Comercio / concepto", "subtitle": "Detalle",
            "amount": st.column_config.NumberColumn("Importe", format="%.2f €"),
            "category": st.column_config.SelectboxColumn("Categoría", options=cats["name"].tolist(), required=True),
            "event_type": "Tipo TR",
        },
        key="tx_editor",
    )
    changed = edited[edited["category"] != edit["category"]]
    c1, c2 = st.columns([1, 3])
    remember = c2.checkbox("Crear también una regla para ese comercio (se aplicará a futuros movimientos)")
    if c1.button(f"Guardar {len(changed)} cambios", disabled=changed.empty, type="primary"):
        import re
        with db.connect(DB) as conn:
            for _, r in changed.iterrows():
                db.set_category(conn, r["id"], r["category"])
                if remember and r["title"]:
                    db.add_rule(conn, re.escape(r["title"]), r["category"])
            if remember:
                db.recategorize_all(conn)
        st.success("Guardado.")
        st.rerun()

# --- Cartera ---------------------------------------------------------------------
with tab_port:
    if positions.empty:
        st.info("No hay datos de cartera. Se descargan con `python -m finanzas.sync`.")
    else:
        p = positions.copy()
        p["coste"] = p["quantity"] * p["avg_cost"]
        p["ganancia"] = p["net_value"] - p["coste"]
        p["rentabilidad"] = p["ganancia"] / p["coste"].where(p["coste"] > 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor", eur(p["net_value"].sum()))
        c2.metric("Coste", eur(p["coste"].sum()))
        tot_gain = p["ganancia"].sum()
        c3.metric("Ganancia latente", eur(tot_gain),
                  f"{tot_gain / p['coste'].sum():.1%}" if p["coste"].sum() else None)
        c1, c2 = st.columns([1, 2])
        with c1:
            fig = px.pie(p, names="name", values="net_value", hole=0.5, title="Distribución")
            fig.update_layout(showlegend=False, height=380)
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, width="stretch")
        with c2:
            st.dataframe(p[["name", "isin", "quantity", "price", "avg_cost", "net_value", "ganancia", "rentabilidad"]]
                         .rename(columns={"name": "Nombre", "isin": "ISIN", "quantity": "Cantidad", "price": "Precio",
                                          "avg_cost": "Precio medio", "net_value": "Valor", "ganancia": "Ganancia",
                                          "rentabilidad": "Rentab."}),
                         hide_index=True, width="stretch",
                         column_config={k: st.column_config.NumberColumn(format="%.2f €")
                                        for k in ["Precio", "Precio medio", "Valor", "Ganancia"]}
                         | {"Rentab.": st.column_config.NumberColumn(format="percent")})
    if len(snapshots) > 1:
        s = snapshots.assign(total=snapshots["cash"].fillna(0) + snapshots["invested"].fillna(0))
        st.plotly_chart(px.line(s, x="taken_at", y=["total", "cash", "invested"], title="Patrimonio en cada sincronización",
                                labels={"taken_at": "", "value": "€", "variable": ""}), width="stretch")

# --- Categorías y reglas -----------------------------------------------------------
with tab_cfg:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Categorías")
        st.caption("El tipo decide cómo cuenta: gasto, ingreso, inversión o excluido (no cuenta, p. ej. traspasos "
                   "entre tus cuentas). «Fijo» = gasto que se reserva a principio de mes y no reduce tu gasto diario.")
        ed = st.data_editor(cats, hide_index=True, width="stretch", num_rows="dynamic",
                            column_config={"name": "Categoría",
                                           "kind": st.column_config.SelectboxColumn("Tipo", options=KINDS, required=True),
                                           "fixed": st.column_config.CheckboxColumn("Fijo", default=False)},
                            key="cat_editor")
        if st.button("Guardar categorías"):
            with db.connect(DB) as conn:
                for _, r in ed.dropna(subset=["name", "kind"]).iterrows():
                    db.save_category(conn, r["name"].strip(), r["kind"], bool(r["fixed"]))
            st.rerun()
    with c2:
        st.subheader("Reglas automáticas")
        st.caption("Si el comercio/concepto contiene el texto (o expresión regular), se asigna la categoría. "
                   "Tienen prioridad sobre las reglas por defecto. Los cambios manuales nunca se sobrescriben.")
        for _, r in rules.iterrows():
            a, b, c = st.columns([3, 3, 1])
            a.code(r["pattern"])
            b.write(r["category"])
            if c.button("🗑️", key=f"del_{r['id']}"):
                with db.connect(DB) as conn:
                    db.delete_rule(conn, int(r["id"]))
                    db.recategorize_all(conn)
                st.rerun()
        with st.form("new_rule", clear_on_submit=True):
            a, b = st.columns(2)
            pat = a.text_input("Texto o regex", placeholder="p. ej. alquiler|comunidad")
            cat = b.selectbox("Categoría", cats["name"].tolist())
            if st.form_submit_button("Añadir regla") and pat.strip():
                with db.connect(DB) as conn:
                    db.add_rule(conn, pat.strip(), cat)
                    n = db.recategorize_all(conn)
                st.success(f"Regla añadida; {n} movimientos reclasificados.")
                st.rerun()
