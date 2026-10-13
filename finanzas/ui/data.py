"""Carga de datos compartida por todas las páginas."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from finanzas import budget, config, db

DEMO_DB = config.DATA_DIR / "demo" / "finanzas.db"


def init_state() -> None:
    """Valores de sesión compartidos (antes de pintar cualquier página)."""
    st.session_state.setdefault("use_demo", not config.DB_PATH.exists())


def db_path() -> Path:
    return DEMO_DB if st.session_state.get("use_demo") else config.DB_PATH


@dataclass
class Data:
    path: Path
    tx: pd.DataFrame
    cats: pd.DataFrame
    rules: pd.DataFrame
    positions: pd.DataFrame
    snapshots: pd.DataFrame
    today: date
    current: str
    months: list[str]

    @property
    def spending_names(self) -> list[str]:
        return self.cats.loc[self.cats["kind"] == "gasto", "name"].tolist()


@dataclass
class Month:
    month: str
    tx: pd.DataFrame
    budgets: dict[str, float]
    plan: budget.DailyPlan


def load() -> Data | None:
    """Lee la base de datos activa. None si todavía no existe."""
    path = db_path()
    if not path.exists():
        return None
    with db.connect(path) as conn:
        tx, cats, rules = db.transactions_df(conn), db.categories_df(conn), db.rules_df(conn)
        positions, snapshots = db.positions_df(conn), db.snapshots_df(conn)
    today = date.today()
    current = today.strftime("%Y-%m")
    months = sorted(tx["month"].unique(), reverse=True) if not tx.empty else []
    if current not in months:
        months = [current] + months
    return Data(path, tx, cats, rules, positions, snapshots, today, current, months)


def load_or_stop(title: str) -> Data:
    """Como ``load`` pero, si no hay datos, muestra cómo conseguirlos y para la página."""
    from . import components as ui

    d = load()
    if d is not None and not d.tx.empty:
        return d
    ui.page_header(title)
    if ui.empty_state("Aún no hay movimientos. Descárgalos con «python -m finanzas.sync» "
                      "o activa los datos de ejemplo en Ajustes.", button="Ir a Ajustes", key="go_settings"):
        st.switch_page("app_pages/ajustes.py")
    st.stop()


def for_month(d: Data, month: str) -> Month:
    with db.connect(d.path) as conn:
        budgets = db.budgets_for_month(conn, month)
    return Month(month, d.tx[d.tx["month"] == month], budgets, budget.daily_plan(d.tx, budgets, month, d.today))


def prev_month(month: str) -> str:
    return (pd.Period(month) - 1).strftime("%Y-%m")
