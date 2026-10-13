"""Bloques de interfaz con el estilo de Trade Republic.

Los bloques estáticos (hero, filas, barras) son HTML pequeño dentro de st.html,
con clases ``tr-*`` definidas en theme.css. Todo texto que viene de los datos
(comercios, categorías, conceptos) se escapa con ``esc``. Los bloques que
mezclan HTML y widgets usan ``st.container(key=...)``, que da una clase CSS
estable ``st-key-<key>``.
"""

import html
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from . import fmt

RANGES = ["1M", "3M", "6M", "1A", "Máx"]
_RANGE_DAYS = {"1M": 31, "3M": 92, "6M": 183, "1A": 366}


def esc(text) -> str:
    return html.escape("" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text))


def _tone(tone: str | None) -> str:
    """'pos' / 'neg' → clase de color. Cualquier otro valor: tinta normal."""
    return {"pos": " tr-pos", "neg": " tr-neg", "muted": " tr-muted"}.get(tone or "", "")


def tone_of(x: float | None, invert: bool = False) -> str | None:
    """Tono por signo: positivo verde, negativo rojo (invert para gastos)."""
    if x is None or pd.isna(x) or round(x, 2) == 0:
        return None
    good = x > 0 if not invert else x < 0
    return "pos" if good else "neg"


# --- Cabecera y secciones --------------------------------------------------

def page_header(title: str, months: list[str] | None = None) -> str | None:
    """Título de página a la izquierda y, si se pasan meses, el selector de mes
    a la derecha. El mes elegido se guarda en la sesión (clave ``month``) y se
    mantiene al cambiar de página."""
    if months and st.session_state.get("month") not in months:
        st.session_state.pop("month", None)
    with st.container(horizontal=True, vertical_alignment="center", key="page_header", gap="small"):
        st.html(f'<h1 class="tr-title">{esc(title)}</h1>')
        if months:
            return st.selectbox("Mes", months, format_func=lambda m: fmt.month_name(m).capitalize(),
                                key="month", label_visibility="collapsed", width=190,
                                persist_state="session")
    return None


def section(title: str, action: tuple[str, str] | None = None, key: str | None = None) -> None:
    """Título de sección (20px/600). ``action`` = (texto, página) añade un enlace
    discreto a la derecha, p. ej. ("Ver todos", "app_pages/movimientos.py")."""
    key = key or "sec_" + "".join(c for c in title.lower() if c.isalnum())
    with st.container(horizontal=True, vertical_alignment="bottom", key=key, gap="small"):
        st.html(f'<h2 class="tr-section">{esc(title)}</h2>')
        if action:
            st.page_link(action[1], label=action[0], width="content")


# --- Números grandes ---------------------------------------------------------

def hero(label: str, value: str, sub: str | None = None, delta: str | None = None,
         tone: str | None = None) -> None:
    """La cifra principal de la página. ``delta`` va debajo, en verde o rojo
    según ``tone`` ('pos'/'neg'), siempre con signo o palabra además del color."""
    parts = [f'<div class="tr-hero-label">{esc(label)}</div>',
             f'<div class="tr-hero-value tnum">{esc(value)}</div>']
    if delta:
        parts.append(f'<div class="tr-hero-delta tnum{_tone(tone)}">{esc(delta)}</div>')
    if sub:
        parts.append(f'<div class="tr-hero-sub">{esc(sub)}</div>')
    st.html(f'<div class="tr-hero">{"".join(parts)}</div>')


def stat_row(items: list[dict]) -> None:
    """Fila de 3-4 cifras discretas, sin tarjetas.

    Cada item: {"label", "value", "sub"?, "tone"?} (tone colorea solo ``sub``)."""
    cells = []
    for it in items:
        sub = (f'<div class="tr-stat-sub tnum{_tone(it.get("tone"))}">{esc(it["sub"])}</div>'
               if it.get("sub") else "")
        cells.append(f'<div class="tr-stat"><div class="tr-stat-label">{esc(it["label"])}</div>'
                     f'<div class="tr-stat-value tnum">{esc(it["value"])}</div>{sub}</div>')
    st.html(f'<div class="tr-stats" style="--n:{len(items)}">{"".join(cells)}</div>')


# --- Barras de progreso -----------------------------------------------------

def progress_html(value: float, pace: float | None = None, tone: str | None = None) -> str:
    """Barra fina. ``value`` y ``pace`` son fracciones (0-1, se recortan).
    ``pace`` dibuja una marca vertical en el ritmo ideal."""
    w = max(0.0, min(float(value), 1.0)) * 100
    fill = {"pos": " tr-fill-pos", "neg": " tr-fill-neg", "muted": " tr-fill-muted"}.get(tone or "", "")
    mark = ""
    if pace is not None:
        mark = f'<div class="tr-progress-pace" style="left:{max(0.0, min(pace, 1.0)) * 100:.2f}%"></div>'
    return (f'<div class="tr-progress" role="presentation"><div class="tr-progress-fill{fill}" '
            f'style="width:{w:.2f}%"></div>{mark}</div>')


def progress(value: float, pace: float | None = None, tone: str | None = None,
             left: str | None = None, right: str | None = None, note: str | None = None,
             note_tone: str | None = None) -> None:
    """Barra de progreso con etiquetas opcionales encima y una frase debajo."""
    top = ""
    if left or right:
        top = (f'<div class="tr-progress-top"><span>{esc(left)}</span>'
               f'<span class="tnum">{esc(right)}</span></div>')
    bottom = f'<div class="tr-progress-note{_tone(note_tone)}">{esc(note)}</div>' if note else ""
    st.html(f'<div class="tr-progress-block">{top}{progress_html(value, pace, tone)}{bottom}</div>')


def pace_bar(plan) -> None:
    """Gasto del día a día frente al presupuesto variable, con la marca del ritmo
    ideal y una frase: verde si vas por debajo del ritmo, rojo si por encima."""
    if not plan.variable_budget or plan.pace is None:
        return
    diff = plan.pace - plan.variable_spent
    tone = "pos" if diff >= 0 else "neg"
    sentence = (f"Vas {fmt.eur(diff)} por debajo del ritmo" if diff >= 0
                else f"Vas {fmt.eur(-diff)} por encima del ritmo")
    progress(plan.variable_spent / plan.variable_budget, plan.pace / plan.variable_budget, tone,
             left="Gasto del día a día",
             right=f"{fmt.eur(plan.variable_spent)} de {fmt.eur(plan.variable_budget)}",
             note=sentence, note_tone=tone)


def kpi(value: str, delta: str | None = None, tone: str | None = None, label: str | None = None) -> None:
    """Cifra secundaria (20px) con una variación opcional al lado."""
    lab = f'<div class="tr-stat-label">{esc(label)}</div>' if label else ""
    dl = f'<span class="tr-kpi-delta tnum{_tone(tone)}">{esc(delta)}</span>' if delta else ""
    st.html(f'<div class="tr-kpi">{lab}<span class="tr-stat-value tnum">{esc(value)}</span>{dl}</div>')


# --- Listas -------------------------------------------------------------------

def list_row(title: str, subtitle: str | None, amount: str, avatar_text: str | None = None,
             positive: bool | None = None, amount_sub: str | None = None,
             amount_sub_tone: str | None = None, bar: float | None = None,
             bar_tone: str | None = None) -> str:
    """HTML de una fila: avatar con iniciales, título y subtítulo, importe a la
    derecha. ``positive`` True pinta el importe en verde, False en rojo, None en
    tinta. ``bar`` (0-1) añade una barra fina bajo el título."""
    avatar = esc(avatar_text if avatar_text is not None else fmt.initials(title))
    tone = {True: " tr-pos", False: " tr-neg"}.get(positive, "")
    sub = f'<div class="tr-row-sub">{esc(subtitle)}</div>' if subtitle else ""
    bar_html = f'<div class="tr-row-bar">{progress_html(bar, tone=bar_tone)}</div>' if bar is not None else ""
    asub = (f'<div class="tr-row-asub tnum{_tone(amount_sub_tone)}">{esc(amount_sub)}</div>'
            if amount_sub else "")
    return (f'<div class="tr-row"><div class="tr-avatar" aria-hidden="true">{avatar}</div>'
            f'<div class="tr-row-main"><div class="tr-row-title">{esc(title)}</div>{sub}{bar_html}</div>'
            f'<div class="tr-row-end"><div class="tr-row-amount tnum{tone}">{esc(amount)}</div>{asub}</div></div>')


def day_header(label: str) -> str:
    return f'<div class="tr-day">{esc(label)}</div>'


def list_block(rows: list[str], empty: str = "No hay nada que mostrar.") -> None:
    """Pinta varias filas (de ``list_row``/``day_header``) en un solo bloque."""
    if not rows:
        empty_state(empty)
        return
    st.html(f'<div class="tr-list">{"".join(rows)}</div>')


def tx_row(r) -> str:
    """Fila de un movimiento: comercio, categoría · fecha, importe con signo."""
    when = r["date"].date() if hasattr(r["date"], "date") else r["date"]
    return list_row(r["title"] or r["subtitle"] or "Movimiento",
                    f"{r['category']} · {fmt.short_date(when)}",
                    fmt.signed(r["amount"]), positive=True if r["amount"] > 0 else None)


# --- Otros ----------------------------------------------------------------------

def range_pills(key: str, default: str = "Máx") -> str:
    """Selector de periodo bajo un gráfico: 1M, 3M, 6M, 1A, Máx."""
    return st.segmented_control("Periodo", RANGES, default=default, required=True, key=key,
                                label_visibility="collapsed")


def range_start(choice: str, end: date) -> date | None:
    """Fecha de inicio del periodo elegido (None = todo)."""
    return end - timedelta(days=_RANGE_DAYS[choice]) if choice in _RANGE_DAYS else None


def empty_state(text: str, button: str | None = None, key: str | None = None) -> bool:
    """Mensaje tranquilo para listas o gráficos vacíos. Con ``button`` devuelve
    True cuando se pulsa."""
    st.html(f'<div class="tr-empty">{esc(text)}</div>')
    return bool(button) and st.button(button, type="primary", key=key)


def note(text: str) -> None:
    """Texto secundario (13px, gris)."""
    st.html(f'<p class="tr-note">{esc(text)}</p>')
