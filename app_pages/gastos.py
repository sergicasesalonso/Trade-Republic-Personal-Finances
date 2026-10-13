"""Gastos: total del mes, reparto por categoría, comercios y evolución."""

import streamlit as st

from finanzas import budget
from finanzas.ui import charts, data, fmt
from finanzas.ui import components as ui

d = data.load_or_stop("Gastos")
month = ui.page_header("Gastos", d.months)
m = data.for_month(d, month)
prev = data.prev_month(month)
ptx = d.tx[d.tx["month"] == prev]
prev_name = fmt.month_name(prev, year=False)

spent, pspent = budget.spending(m.tx), budget.spending(ptx)
delta = tone = None
if pspent > 0:
    diff = spent - pspent
    delta = f"{fmt.signed(diff)} ({fmt.pct(diff / pspent, sign=True)}) respecto a {prev_name}"
    tone = ui.tone_of(diff, invert=True)
ui.hero(f"Gastado en {fmt.month_name(month, year=False)}", fmt.eur(spent), delta=delta, tone=tone)

bycat = budget.spending_by_category(m.tx)
ui.section("Por categoría")
if bycat.empty:
    ui.empty_state("Aún no hay gastos este mes.")
else:
    prevcat = budget.spending_by_category(ptx).set_index("category")["gasto"]
    spend_tx = m.tx[m.tx["kind"] == "gasto"]
    top = float(bycat["gasto"].max())
    catlist = st.container(key="catlist", gap=None)
    for i, r in enumerate(bycat.itertuples(index=False)):
        cat_tx = spend_tx[spend_tx["category"] == r.category]
        change = r.gasto - float(prevcat.get(r.category, 0.0))
        n = len(cat_tx)
        vs = f"{fmt.signed(change)} vs {prev_name[:3]}" if round(change, 2) else f"Igual que en {prev_name[:3]}"
        with catlist, st.container(key=f"catrow_{i}", gap=None):
            st.html(ui.list_row(
                r.category, f"{fmt.pct(r.gasto / spent)} del gasto · {n} {'pago' if n == 1 else 'pagos'}",
                fmt.eur(r.gasto), amount_sub=vs,
                amount_sub_tone=ui.tone_of(change, invert=True), bar=r.gasto / top))
            with st.expander(f"Movimientos de {r.category}"):
                ui.list_block([ui.tx_row(t) for _, t in cat_tx.iterrows()])

ui.section("Dónde más gastas")
merchants = (m.tx[m.tx["kind"] == "gasto"].groupby("title")["amount"].agg(["sum", "count"])
             .assign(sum=lambda x: -x["sum"]).sort_values("sum", ascending=False).head(8))
ui.list_block([ui.list_row(title, f"{c} {'pago' if c == 1 else 'pagos'}", fmt.eur(s))
               for title, s, c in merchants[merchants["sum"] > 0].itertuples()],
              empty="Aún no hay gastos este mes.")

ui.section("Evolución por categoría")
last12 = sorted(d.tx["month"].unique())[-12:]
hist = d.tx[(d.tx["kind"] == "gasto") & d.tx["month"].isin(last12)]
hist = (-hist.groupby(["month", "category"])["amount"].sum()).rename("gasto").reset_index()
hist = hist[hist["gasto"] > 0]
if hist["month"].nunique() < 2:
    ui.empty_state("Hacen falta al menos dos meses de datos para ver la evolución.")
else:
    top_cats = hist.groupby("category")["gasto"].sum().sort_values(ascending=False).head(6).index.tolist()
    ui.note(f"Las {len(top_cats)} categorías con más gasto, mes a mes. Pasa el cursor por una barra para ver el importe.")
    charts.show(charts.small_multiples(hist, top_cats), key="cat_evolution")
