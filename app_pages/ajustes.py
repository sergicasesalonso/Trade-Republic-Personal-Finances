"""Ajustes: origen de datos, sincronización, categorías y reglas."""

import streamlit as st

from finanzas import db
from finanzas.categories import KINDS
from finanzas.ui import data
from finanzas.ui import components as ui

ui.page_header("Ajustes")

ui.section("Datos")
st.toggle("Usar datos de ejemplo", key="use_demo", persist_state="session",
          help="Genera los datos con python -m finanzas.sync --demo.")
d = data.load()
if d is None or d.tx.empty:
    ui.note("Todavía no hay movimientos en esta base de datos.")
else:
    ui.note(f"{len(d.tx)} movimientos · último: {d.tx['date'].max():%d/%m/%Y}"
            + (f" · cartera actualizada: {d.snapshots['taken_at'].max():%d/%m/%Y %H:%M}"
               if not d.snapshots.empty else ""))
with st.expander("Cómo sincronizar con Trade Republic"):
    st.markdown(
        "1. Inicia sesión una vez (te pedirá teléfono, PIN y código 2FA):\n"
        "   ```\n   pytr login --store_credentials\n   ```\n"
        "2. Descarga tus movimientos y tu cartera:\n"
        "   ```\n   python -m finanzas.sync\n   ```\n"
        "Para probar sin cuenta: `python -m finanzas.sync --demo`."
    )
if d is None:
    st.stop()

ui.section("Categorías")
ui.note("El tipo decide cómo cuenta: gasto, ingreso, inversión o excluido (no cuenta, p. ej. traspasos "
        "entre tus cuentas). Fijo = gasto que se reserva a principio de mes y no reduce tu gasto diario.")
ed = st.data_editor(d.cats, hide_index=True, width="stretch", num_rows="dynamic",
                    column_config={"name": "Categoría",
                                   "kind": st.column_config.SelectboxColumn("Tipo", options=KINDS, required=True),
                                   "fixed": st.column_config.CheckboxColumn("Fijo", default=False)},
                    key="cat_editor")
if st.button("Guardar categorías"):
    with db.connect(d.path) as conn:
        for _, r in ed.dropna(subset=["name", "kind"]).iterrows():
            db.save_category(conn, r["name"].strip(), r["kind"], bool(r["fixed"]))
    st.toast("Categorías guardadas.")
    st.rerun()

ui.section("Reglas automáticas")
ui.note("Si el comercio o concepto contiene el texto (o expresión regular), se asigna la categoría. "
        "Tienen prioridad sobre las reglas por defecto. Los cambios manuales nunca se sobrescriben.")
if d.rules.empty:
    ui.empty_state("Aún no tienes reglas propias.")
for _, r in d.rules.iterrows():
    with st.container(horizontal=True, vertical_alignment="center", key=f"rule_{r['id']}"):
        st.html(f'<div class="tr-rule-pattern">{ui.esc(r["pattern"])}</div>'
                f'<div class="tr-row-sub">{ui.esc(r["category"])}</div>')
        if st.button("Eliminar", key=f"del_{r['id']}", type="tertiary"):
            with db.connect(d.path) as conn:
                db.delete_rule(conn, int(r["id"]))
                db.recategorize_all(conn)
            st.rerun()

with st.container(key="surface_rule"):
    with st.form("new_rule", clear_on_submit=True, border=False):
        a, b = st.columns(2)
        pat = a.text_input("Texto o expresión regular", placeholder="p. ej. alquiler|comunidad")
        cat = b.selectbox("Categoría", d.cats["name"].tolist())
        if st.form_submit_button("Añadir regla", type="primary") and pat.strip():
            with db.connect(d.path) as conn:
                db.add_rule(conn, pat.strip(), cat)
                n = db.recategorize_all(conn)
            st.toast(f"Regla añadida; {n} movimientos reclasificados.")
            st.rerun()
