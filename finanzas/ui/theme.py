"""Tokens de diseño (ver design/DESIGN.md) y carga del CSS."""

from pathlib import Path

import streamlit as st

# Colores por tema. El CSS (theme.css) define los mismos valores como variables.
DARK = {
    "bg": "#000000", "surface": "#151515", "surface2": "#202020", "text": "#FFFFFF",
    "muted": "#93969A", "hairline": "#202020", "positive": "#02CA50", "negative": "#FF4034",
}
LIGHT = {
    "bg": "#FFFFFF", "surface": "#F2F3F4", "surface2": "#E6E7E9", "text": "#000000",
    "muted": "#6A6B6D", "hairline": "#E6E7E9", "positive": "#007A35", "negative": "#C9241A",
}

# Gráficos: un solo valor válido en los dos temas (contraste >= 3:1 en blanco y negro).
CHART_NEUTRAL = "#8A8D91"
CHART_POSITIVE = "#00A843"
CHART_NEGATIVE = "#F0392D"
FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"

_CSS = Path(__file__).with_name("theme.css")


def inject() -> None:
    """Inyecta el CSS de la app. Se llama una vez por ejecución desde app.py."""
    st.html(f"<style>{_CSS.read_text(encoding='utf-8')}</style>")
