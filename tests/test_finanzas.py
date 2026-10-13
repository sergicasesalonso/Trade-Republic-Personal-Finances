from datetime import date

import pytest

from finanzas import budget, db
from finanzas.categories import categorize
from finanzas.importer import event_to_row


@pytest.mark.parametrize("title,etype,amount,expected", [
    ("MERCADONA BARCELONA", "CARD_SUCCESSFUL_TRANSACTION", -20, "Supermercado"),
    ("Glovo", "CARD_SUCCESSFUL_TRANSACTION", -15, "Restaurantes y bares"),
    ("Uber", "CARD_SUCCESSFUL_TRANSACTION", -10, "Transporte"),
    ("Uber Eats", "CARD_SUCCESSFUL_TRANSACTION", -10, "Restaurantes y bares"),
    ("Alquiler piso", "OUTGOING_TRANSFER", -700, "Vivienda"),
    ("IKEA", "CARD_SUCCESSFUL_TRANSACTION", -80, "Hogar"),
    ("Movistar", "CARD_SUCCESSFUL_TRANSACTION", -35, "Facturas y suministros"),
    ("Lime", "CARD_SUCCESSFUL_TRANSACTION", -3, "Transporte"),
    ("Sublime Cafe", "CARD_SUCCESSFUL_TRANSACTION", -3, "Restaurantes y bares"),
    ("Juan", "OUTGOING_TRANSFER", -30, "Transferencias enviadas"),
    ("Empresa SL", "INCOMING_TRANSFER", 2000, "Nómina e ingresos"),
    ("MSCI World", "TRADING_SAVINGSPLAN_EXECUTED", -100, "Inversión"),
    ("Comercio raro", "CARD_SUCCESSFUL_TRANSACTION", -5, "Otros gastos"),
])
def test_categorize(title, etype, amount, expected):
    assert categorize(title, etype, amount) == expected


def test_user_rule_wins():
    assert categorize("Mercadona", "CARD_SUCCESSFUL_TRANSACTION", -5, [("mercadona", "Hogar")]) == "Hogar"


def test_event_to_row_skips_failed_and_parses_timestamp():
    base = {"id": "1", "timestamp": "2024-05-03T10:21:44.123+0000", "title": "X",
            "subtitle": None, "eventType": "card_successful_transaction",
            "amount": {"value": -12.5, "currency": "EUR"}}
    row = event_to_row(base)
    assert row["amount"] == -12.5 and row["event_type"] == "CARD_SUCCESSFUL_TRANSACTION"
    assert row["date"] in ("2024-05-03", "2024-05-02", "2024-05-04")
    assert event_to_row({**base, "eventType": "CARD_FAILED_TRANSACTION"}) is None
    assert event_to_row({**base, "status": "CANCELED"}) is None
    assert event_to_row({**base, "amount": None}) is None


def _rows(*items):
    return [{"id": str(i), "timestamp": f"{d}T12:00:00", "date": d, "title": t, "subtitle": "",
             "event_type": e, "amount": a, "currency": "EUR"} for i, (d, t, e, a) in enumerate(items)]


def test_daily_plan_and_manual_category(tmp_path):
    with db.connect(tmp_path / "t.db") as conn:
        db.upsert_transactions(conn, _rows(
            ("2024-06-01", "Empresa", "INCOMING_TRANSFER", 2000),
            ("2024-06-05", "Mercadona", "CARD_SUCCESSFUL_TRANSACTION", -300),
            ("2024-06-10", "Glovo", "CARD_SUCCESSFUL_TRANSACTION", -50),
            ("2024-06-10", "Traspaso", "OUTGOING_TRANSFER", -500),
        ))
        db.set_category(conn, "3", "Movimientos internos")  # no cuenta como gasto
        db.set_budget(conn, "*", db.SAVINGS, 1000)
        df = db.transactions_df(conn)
        budgets = db.budgets_for_month(conn, "2024-06")

    plan = budget.daily_plan(df, budgets, "2024-06", date(2024, 6, 10))
    assert plan.budget == 1000                  # 2000 ingresos − 1000 ahorro
    assert plan.spent == 350
    assert plan.days_left == 21                 # del 10 al 30, incluido hoy
    assert plan.per_day == pytest.approx((1000 - 300) / 21)
    assert plan.today_left == pytest.approx(plan.per_day - 50)


def test_manual_category_survives_resync(tmp_path):
    with db.connect(tmp_path / "t.db") as conn:
        rows = _rows(("2024-06-05", "Mercadona", "CARD_SUCCESSFUL_TRANSACTION", -30))
        db.upsert_transactions(conn, rows)
        db.set_category(conn, "0", "Restaurantes y bares")
        db.upsert_transactions(conn, rows)
        assert db.transactions_df(conn).iloc[0]["category"] == "Restaurantes y bares"


def test_fixed_expenses_are_reserved_not_spread(tmp_path):
    with db.connect(tmp_path / "t.db") as conn:
        db.upsert_transactions(conn, _rows(
            ("2024-05-01", "Alquiler piso", "OUTGOING_TRANSFER", -700),   # mes anterior
            ("2024-06-01", "Empresa", "INCOMING_TRANSFER", 2000),
            ("2024-06-05", "Mercadona", "CARD_SUCCESSFUL_TRANSACTION", -100),
        ))
        db.set_budget(conn, "*", db.TOTAL, 1300)
        df = db.transactions_df(conn)
        budgets = db.budgets_for_month(conn, "2024-06")

    plan = budget.daily_plan(df, budgets, "2024-06", date(2024, 6, 11))
    assert plan.fixed_paid == 0 and plan.fixed_expected == 700   # alquiler aún no cobrado
    assert plan.variable_budget == 600
    assert plan.per_day == pytest.approx((600 - 100) / 20)
