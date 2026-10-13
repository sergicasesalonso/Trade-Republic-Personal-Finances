"""Cartera: valor, ganancia latente, evolución del patrimonio y posiciones."""

import pandas as pd
import streamlit as st

from finanzas.ui import charts, data, fmt
from finanzas.ui import components as ui


def qty(x: float) -> str:
    s = f"{x:,.4f}".rstrip("0").rstrip(".")
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


d = data.load_or_stop("Cartera")
ui.page_header("Cartera")
p = d.positions.copy()
snaps = d.snapshots.assign(total=d.snapshots["cash"].fillna(0) + d.snapshots["invested"].fillna(0))

if p.empty:
    ui.hero("Valor de la cartera", fmt.eur(0),
            sub="No hay datos de cartera. Se descargan con python -m finanzas.sync.")
else:
    p["coste"] = p["quantity"] * p["avg_cost"]
    p["ganancia"] = p["net_value"] - p["coste"]
    p["rentabilidad"] = p["ganancia"] / p["coste"].where(p["coste"] > 0)
    value, cost, gain = p["net_value"].sum(), p["coste"].sum(), p["ganancia"].sum()
    ui.hero("Valor de la cartera", fmt.eur(value),
            delta=f"{fmt.signed(gain)} ({fmt.pct(gain / cost, sign=True)})" if cost else fmt.signed(gain),
            tone=ui.tone_of(gain), sub="Ganancia latente sobre el precio de compra")

ui.section("Patrimonio")
if len(snaps) < 2:
    ui.empty_state("Hacen falta al menos dos sincronizaciones para ver la evolución del patrimonio.")
else:
    chart = st.container(key="nw_chart")
    choice = ui.range_pills("nw_range")
    start = ui.range_start(choice, snaps["taken_at"].max().date())
    s = snaps if start is None else snaps[snaps["taken_at"] >= pd.Timestamp(start)]
    if len(s) < 2:
        s = snaps.tail(2)
    with chart:
        change = s["total"].iloc[-1] - s["total"].iloc[0]
        ui.kpi(fmt.eur(s["total"].iloc[-1]), f"{fmt.signed(change)} en el periodo", ui.tone_of(change))
        charts.show(charts.line(s["taken_at"], s["total"]), key="networth")

if not snaps.empty:
    last = snaps.iloc[-1]
    ui.stat_row([
        {"label": "Efectivo", "value": fmt.eur(last["cash"])},
        {"label": "Invertido", "value": fmt.eur(last["invested"])},
        {"label": "Patrimonio total", "value": fmt.eur(last["total"]),
         "sub": f"Actualizado {last['taken_at']:%d/%m/%Y %H:%M}"},
    ])

if not p.empty:
    ui.section("Posiciones")
    ui.list_block([
        ui.list_row(r.name, f"{qty(r.quantity)} × {fmt.eur(r.price)}", fmt.eur(r.net_value),
                    amount_sub=fmt.pct(r.rentabilidad, sign=True), amount_sub_tone=ui.tone_of(r.rentabilidad))
        for r in p.itertuples(index=False)
    ])

    ui.section("Distribución")
    alloc = p[["name", "net_value"]].rename(columns={"net_value": "valor"})
    if not snaps.empty and (snaps.iloc[-1]["cash"] or 0) > 0:
        alloc = pd.concat([alloc, pd.DataFrame([{"name": "Efectivo", "valor": snaps.iloc[-1]["cash"]}])])
    alloc = alloc.sort_values("valor", ascending=False)
    total = alloc["valor"].sum()
    ui.list_block([ui.list_row(r.name, f"{fmt.pct(r.valor / total)} del patrimonio", fmt.eur(r.valor),
                               bar=r.valor / total)
                   for r in alloc.itertuples(index=False)])
