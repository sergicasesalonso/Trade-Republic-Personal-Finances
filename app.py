"""Dashboard de finanzas personales. Ejecuta: streamlit run app.py"""

import streamlit as st

from finanzas.ui import data, theme

st.set_page_config(page_title="Finanzas", page_icon="static/favicon.png", layout="wide")
theme.inject()
data.init_state()

pages = [
    st.Page("app_pages/inicio.py", title="Inicio", default=True),
    st.Page("app_pages/gastos.py", title="Gastos"),
    st.Page("app_pages/objetivos.py", title="Objetivos"),
    st.Page("app_pages/movimientos.py", title="Movimientos"),
    st.Page("app_pages/cartera.py", title="Cartera"),
    st.Page("app_pages/ajustes.py", title="Ajustes"),
]
page = st.navigation(pages, position="top")

# En móvil Streamlit pliega la barra superior en un menú lateral; en su lugar se
# muestra esta fila de enlaces desplazable (theme.css la oculta en escritorio).
with st.container(horizontal=True, key="mobile_nav", gap="small"):
    for i, p in enumerate(pages):
        with st.container(key="mnav_active" if p.url_path == page.url_path else f"mnav_{i}", width="content"):
            st.page_link(p, width="content")

page.run()
