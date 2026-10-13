"""Movimientos: buscador, lista agrupada por día y edición de categorías."""

import re

import streamlit as st

from finanzas import db
from finanzas.ui import data, fmt
from finanzas.ui import components as ui

MAX_ROWS = 300

d = data.load_or_stop("Movimientos")
month = ui.page_header("Movimientos", d.months)
cat_names = d.cats["name"].tolist()

with st.container(horizontal=True, vertical_alignment="center", key="tx_filters"):
    q = st.text_input("Buscar", placeholder="Buscar comercio o concepto", key="tx_q",
                      label_visibility="collapsed", width="stretch")
    sel_cats = st.multiselect("Categorías", cat_names, placeholder="Todas las categorías", key="tx_cats",
                              label_visibility="collapsed", width=260)
    scope = st.segmented_control("Periodo", ["mes", "todo"], default="mes", required=True, key="tx_scope",
                                 format_func=lambda s: fmt.month_name(month).capitalize() if s == "mes" else "Todo",
                                 label_visibility="collapsed")

view = d.tx[d.tx["month"] == month] if scope == "mes" else d.tx
if q:
    view = view[view["title"].str.contains(q, case=False, na=False, regex=False)
                | view["subtitle"].str.contains(q, case=False, na=False, regex=False)]
if sel_cats:
    view = view[view["category"].isin(sel_cats)]

with st.container(horizontal=True, vertical_alignment="center", key="tx_bar"):
    st.html(f'<p class="tr-note tnum">{len(view)} movimientos · total {ui.esc(fmt.signed(view["amount"].sum()))}</p>')
    mode = st.segmented_control("Vista", ["Lista", "Editar categorías"], default="Lista", required=True,
                                key="tx_mode", label_visibility="collapsed")

if mode == "Lista":
    rows = []
    for day, group in list(view.head(MAX_ROWS).groupby(view.head(MAX_ROWS)["date"].dt.date, sort=False)):
        rows.append(ui.day_header(fmt.day_label(day, d.today)))
        rows += [ui.list_row(r["title"] or r["subtitle"] or "Movimiento", r["category"], fmt.signed(r["amount"]),
                             positive=True if r["amount"] > 0 else None) for _, r in group.iterrows()]
    ui.list_block(rows, empty="No hay movimientos con estos filtros." if (q or sel_cats)
                  else "Aún no hay movimientos este mes.")
    if len(view) > MAX_ROWS:
        ui.note(f"Se muestran los {MAX_ROWS} más recientes. Usa el buscador para encontrar el resto.")
else:
    ui.note("Cambia la categoría en la tabla y pulsa Guardar.")
    edit = view[["id", "date", "title", "subtitle", "amount", "category", "event_type"]].copy()
    edited = st.data_editor(
        edit, hide_index=True, width="stretch", height=520,
        disabled=["id", "date", "title", "subtitle", "amount", "event_type"],
        column_config={
            "id": None,
            "date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "title": "Comercio / concepto", "subtitle": "Detalle",
            "amount": st.column_config.NumberColumn("Importe", format="%.2f €"),
            "category": st.column_config.SelectboxColumn("Categoría", options=cat_names, required=True),
            "event_type": "Tipo TR",
        },
        key="tx_editor",
    )
    changed = edited[edited["category"] != edit["category"]]
    with st.container(horizontal=True, vertical_alignment="center", key="tx_save"):
        save = st.button(f"Guardar {len(changed)} cambios", disabled=changed.empty, type="primary")
        remember = st.checkbox("Crear también una regla para ese comercio (se aplicará a futuros movimientos)")
    if save:
        with db.connect(d.path) as conn:
            for _, r in changed.iterrows():
                db.set_category(conn, r["id"], r["category"])
                if remember and r["title"]:
                    db.add_rule(conn, re.escape(r["title"]), r["category"])
            if remember:
                db.recategorize_all(conn)
        st.toast("Cambios guardados.")
        st.rerun()
