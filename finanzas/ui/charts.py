"""Plantilla Plotly común y constructores de gráficos.

Estilo de Trade Republic: fondo transparente, sin títulos (los pone Streamlit),
sin barra de herramientas, sin rejilla salvo una línea horizontal tenue, una
línea de 2 px sin marcadores. Las barras son neutras; solo los ingresos van en
verde.

La plantilla se monta sobre la de Streamlit ("streamlit+finanzas"), que usa
colores comodín (#000001...) que el navegador sustituye por los del tema activo.
Así la línea de tinta (INK = primer color de ``chartCategoricalColors``) y el
texto gris de los ejes cambian solos entre tema claro y oscuro.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from plotly.subplots import make_subplots
from streamlit.elements.lib.streamlit_plotly_theme import CATEGORY_0, GRAY_70

from . import fmt
from .theme import CHART_NEUTRAL, CHART_POSITIVE, FONT

INK = CATEGORY_0
MUTED = GRAY_70
GRID = "rgba(138, 141, 145, 0.18)"
AXIS = dict(showline=False, zeroline=False, ticks="", showgrid=False, fixedrange=True,
            tickfont=dict(size=12, color=MUTED))

pio.templates["finanzas"] = go.layout.Template(layout=dict(
    font=dict(family=FONT, size=12),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    separators=",.",  # 1.234,56
    margin=dict(l=0, r=4, t=8, b=0),
    showlegend=False,
    hovermode="x unified",
    hoverlabel=dict(font=dict(family=FONT, size=13), bordercolor="rgba(0,0,0,0)"),
    xaxis=AXIS,
    yaxis={**AXIS, "showgrid": True, "gridcolor": GRID, "gridwidth": 1, "ticksuffix": " €",
           "tickformat": ",.0f", "nticks": 4, "side": "right", "automargin": True},
    legend=dict(orientation="h", x=0, y=-0.14, xanchor="left", yanchor="top", title=None,
                font=dict(size=13, color=MUTED)),
    bargap=0.35, bargroupgap=0.12,
))

EUR_HOVER = "%{y:,.2f} €"


def show(fig: go.Figure, key: str | None = None) -> None:
    """Pinta un gráfico con la configuración común (sin barra de herramientas)."""
    st.plotly_chart(fig, width="stretch", theme="streamlit", key=key,
                    config={"displayModeBar": False, "scrollZoom": False, "responsive": True})


def _fig(height: int) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(template="streamlit+finanzas", height=height)
    return fig


def _month_labels(months: pd.Series) -> list[str]:
    return [f"{fmt.MONTHS[int(m[5:]) - 1][:3]} {m[2:4]}" for m in months]


def overview(ov: pd.DataFrame) -> go.Figure:
    """Ingresos (verde) y gastos (neutro) por mes, con el ahorro como línea."""
    x = _month_labels(ov["month"])
    fig = _fig(300)
    fig.add_bar(x=x, y=ov["ingresos"], name="Ingresos", marker_color=CHART_POSITIVE,
                marker_cornerradius=4, hovertemplate=EUR_HOVER)
    fig.add_bar(x=x, y=ov["gastos"], name="Gastos", marker_color=CHART_NEUTRAL,
                marker_cornerradius=4, hovertemplate=EUR_HOVER)
    fig.add_scatter(x=x, y=ov["ahorro"], name="Ahorro", mode="lines", line=dict(width=2, color=INK),
                    hovertemplate=EUR_HOVER)
    fig.update_layout(barmode="group", showlegend=True, margin=dict(b=40))
    return fig


def line(x: pd.Series, y: pd.Series, height: int = 260) -> go.Figure:
    """Línea única tipo gráfico de cartera, con la escala ajustada a los datos."""
    fig = _fig(height)
    fig.add_scatter(x=x, y=y, mode="lines", line=dict(width=2, color=INK, shape="spline", smoothing=0.4),
                    customdata=[fmt.short_date(t.date()) for t in pd.to_datetime(x)],
                    hovertemplate="%{customdata}<br>" + EUR_HOVER + "<extra></extra>", name="")
    lo, hi = float(y.min()), float(y.max())
    pad = (hi - lo) * 0.15 or abs(hi) * 0.05 or 1
    fig.update_yaxes(range=[lo - pad, hi + pad])
    # Fechas en español (Plotly solo trae los nombres de mes en inglés)
    ticks = pd.date_range(x.min(), x.max(), periods=4)
    fig.update_xaxes(tickvals=ticks, ticktext=[fmt.short_date(t.date()) for t in ticks])
    fig.update_layout(hovermode="x", margin=dict(b=24))
    return fig


def cumulative(cum: pd.DataFrame, today: pd.Timestamp | None = None) -> go.Figure:
    """Gasto variable acumulado (línea) frente al ritmo ideal (discontinua)."""
    fig = _fig(280)
    actual = cum if today is None else cum[cum["dia"] <= today]
    fig.add_scatter(x=cum["dia"], y=cum["ideal"], name="Ritmo ideal", mode="lines",
                    line=dict(width=1.5, dash="dash", color=CHART_NEUTRAL), hovertemplate=EUR_HOVER)
    fig.add_scatter(x=actual["dia"], y=actual["acumulado"], name="Gastado", mode="lines",
                    line=dict(width=2, color=INK), hovertemplate=EUR_HOVER)
    fig.update_xaxes(tickformat="%d", nticks=6, range=[cum["dia"].min(), cum["dia"].max()])
    fig.update_layout(showlegend=True, margin=dict(b=40))
    return fig


def small_multiples(hist: pd.DataFrame, categories: list[str], cols: int = 2) -> go.Figure:
    """Una mini gráfica de barras por categoría (mismo eje Y), últimos meses."""
    rows = -(-len(categories) // cols)
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=categories, shared_yaxes=True,
                        vertical_spacing=0.12, horizontal_spacing=0.06)
    months = sorted(hist["month"].unique())
    labels = [fmt.MONTHS[int(m[5:]) - 1][:3] for m in months]
    for i, cat in enumerate(categories):
        s = hist[hist["category"] == cat].set_index("month")["gasto"].reindex(months, fill_value=0.0)
        fig.add_bar(x=labels, y=s.values, row=i // cols + 1, col=i % cols + 1, name=cat,
                    marker_color=CHART_NEUTRAL, marker_cornerradius=3,
                    hovertemplate="%{x}: %{y:,.2f} €<extra></extra>")
    fig.update_layout(template="streamlit+finanzas", height=170 * rows, hovermode="closest",
                      margin=dict(l=0, r=0, t=28, b=20))
    fig.update_xaxes(tickfont=dict(size=11, color=MUTED), nticks=4,
                     **{k: v for k, v in AXIS.items() if k != "tickfont"})
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, showline=False, ticks="",
                     tickformat=",.0f", ticksuffix=" €", nticks=3, fixedrange=True, side="right",
                     showticklabels=False)
    for i, a in enumerate(fig.layout.annotations):  # títulos alineados a la izquierda de cada mini gráfica
        ax = fig.layout["xaxis" if i == 0 else f"xaxis{i + 1}"]
        a.update(x=ax.domain[0], xanchor="left", font=dict(size=13, color=INK))
    return fig
