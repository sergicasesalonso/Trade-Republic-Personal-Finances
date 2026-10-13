"""Categorías por defecto y reglas automáticas de clasificación.

Cada categoría tiene un *tipo* que decide cómo cuenta en los totales:

- ``gasto``: cuenta como gasto (y para el presupuesto diario).
- ``ingreso``: cuenta como ingreso.
- ``inversion``: compras/ventas de valores, planes de ahorro, etc.
- ``excluido``: no cuenta en nada (p. ej. traspasos entre tus propias cuentas).

Además, una categoría de gasto puede ser *fija* (alquiler, facturas...): se
reserva del presupuesto a principio de mes y no reduce tu gasto diario.
"""

import re

KINDS = ["gasto", "ingreso", "inversion", "excluido"]

DEFAULT_FIXED = {"Vivienda", "Facturas y suministros"}

DEFAULT_CATEGORIES: dict[str, str] = {
    "Supermercado": "gasto",
    "Restaurantes y bares": "gasto",
    "Transporte": "gasto",
    "Compras": "gasto",
    "Ocio y suscripciones": "gasto",
    "Salud y deporte": "gasto",
    "Vivienda": "gasto",
    "Facturas y suministros": "gasto",
    "Hogar": "gasto",
    "Viajes": "gasto",
    "Efectivo": "gasto",
    "Transferencias enviadas": "gasto",
    "Comisiones e impuestos": "gasto",
    "Otros gastos": "gasto",
    "Nómina e ingresos": "ingreso",
    "Intereses": "ingreso",
    "Dividendos": "ingreso",
    "Reembolsos": "ingreso",
    "Saveback": "ingreso",
    "Inversión": "inversion",
    "Movimientos internos": "excluido",
}

# Reglas por nombre del comercio / concepto (regex, sin distinguir mayúsculas).
# Las reglas que crees en el dashboard tienen prioridad sobre éstas.
DEFAULT_RULES: list[tuple[str, str]] = [
    (r"mercadona|lidl|carrefour|\bdia\b|aldi|consum|bon ?preu|condis|caprabo|eroski|alcampo|"
     r"ahorramas|hipercor|supercor|\bspar\b|froiz|gadis|masymas|bonarea|ametller|rewe|edeka|"
     r"supermerca|alimentaci", "Supermercado"),
    (r"glovo|just ?eat|uber ?eats|deliveroo|mcdonald|burger king|telepizza|domino|kfc|"
     r"starbucks|restaur|\bbar\b|cafe|cafeter|taberna|pizzer|sushi|tapas|cervecer|"
     r"foodora|five guys|100 montaditos|vips|goiko|tgb|tim hortons", "Restaurantes y bares"),
    (r"renfe|\btmb\b|metro|\bemt\b|fgc|rodalies|bicing|uber(?! ?eats)|cabify|bolt|free ?now|"
     r"taxi|repsol|cepsa|\bbp\b|shell|galp|petrol|gasolin|parking|aparcamiento|"
     r"autopista|peaje|alsa|blablacar|cooltra|\blime\b|\btier\b|ouigo|iryo", "Transporte"),
    (r"ryanair|vueling|iberia|easyjet|air ?europa|booking|airbnb|hotel|hostel|expedia|"
     r"aena|lufthansa|wizz|edreams|trainline", "Viajes"),
    (r"netflix|spotify|hbo|\bmax\b|disney|prime video|apple\.com|itunes|google|youtube|"
     r"steam|playstation|xbox|nintendo|twitch|cine|yelmo|cinesa|ticketmaster|entradas|"
     r"dazn|filmin|audible|chatgpt|openai|anthropic|claude", "Ocio y suscripciones"),
    (r"farmac|pharma|clinic|hospital|dentist|optica|fisio|gym|gimnas|\bdir\b|basic ?fit|"
     r"mcfit|altafit|anytime fitness|decathlon|sanitas|adeslas|asisa|dkv", "Salud y deporte"),
    (r"alquiler|lloguer|hipoteca|comunidad|\brent\b|miete", "Vivienda"),
    (r"endesa|iberdrola|naturgy|holaluz|totalenergies|som energia|movistar|vodafone|orange|"
     r"\bdigi\b|pepephone|simyo|lowi|\bo2\b|jazztel|masmovil|finetwork|agua|aigues|"
     r"canal de isabel|seguro|mapfre|mutua|allianz|\baxa\b|linea directa", "Facturas y suministros"),
    (r"ikea|leroy merlin|bricomart|bauhaus|maisons du monde|zara home|jysk|ferreter", "Hogar"),
    (r"amazon|amzn|zara|pull ?& ?bear|bershka|stradivarius|mango|h&m|primark|uniqlo|"
     r"el corte ingl|fnac|mediamarkt|media markt|pccomponentes|aliexpress|shein|temu|"
     r"ebay|wallapop|vinted|nike|adidas|apple store|sephora|druni|primor|massimo dutti",
     "Compras"),
]

# Clasificación por tipo de evento de Trade Republic (eventType de pytr).
EVENT_TYPE_CATEGORY: dict[str, str] = {
    "CARD_SUCCESSFUL_ATM_WITHDRAWAL": "Efectivo",
    "CARD_REFUND": "Reembolsos",
    "CARD_TR_REFUND": "Reembolsos",
    "CARD_SUCCESSFUL_OCT": "Reembolsos",
    "CARD_ORDER_BILLED": "Comisiones e impuestos",
    "INTEREST_PAYOUT": "Intereses",
    "INTEREST_PAYOUT_CREATED": "Intereses",
    "CREDIT": "Dividendos",
    "SSP_CORPORATE_ACTION_CASH": "Dividendos",
    "TAX_REFUND": "Comisiones e impuestos",
    "TAX_CORRECTION": "Comisiones e impuestos",
    "SSP_TAX_CORRECTION": "Comisiones e impuestos",
    "PRE_DETERMINED_TAX_BASE_EARNING": "Comisiones e impuestos",
    "ACQUISITION_TRADE_PERK": "Saveback",
    "BENEFITS_SAVEBACK_EXECUTION": "Inversión",
    "SAVEBACK_AGGREGATE": "Inversión",
    "BENEFITS_SPARE_CHANGE_EXECUTION": "Inversión",
    "SPARE_CHANGE_AGGREGATE": "Inversión",
    "ORDER_EXECUTED": "Inversión",
    "TRADE_INVOICE": "Inversión",
    "TRADE_CORRECTED": "Inversión",
    "SAVINGS_PLAN_EXECUTED": "Inversión",
    "SAVINGS_PLAN_INVOICE_CREATED": "Inversión",
    "TRADING_SAVINGSPLAN_EXECUTED": "Inversión",
    "TRADING_TRADE_EXECUTED": "Inversión",
    "IPO_TRADE_EXECUTED": "Inversión",
    "PRIVATE_MARKETS_ORDER_CREATED": "Inversión",
    "PRIVATE_MARKETS_TRADE_EXECUTED": "Inversión",
    "PRIVATE_MARKET_FUND_TRADE_EXECUTED": "Inversión",
    "INCOMING_TRANSFER": "Nómina e ingresos",
    "INCOMING_TRANSFER_DELEGATION": "Nómina e ingresos",
    "BANK_TRANSACTION_INCOMING": "Nómina e ingresos",
    "ACCOUNT_TRANSFER_INCOMING": "Nómina e ingresos",
    "PAYMENT_INBOUND": "Nómina e ingresos",
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": "Nómina e ingresos",
    "PAYMENT_INBOUND_APPLE_PAY": "Movimientos internos",
    "PAYMENT_INBOUND_GOOGLE_PAY": "Movimientos internos",
    "PAYMENT_INBOUND_CREDIT_CARD": "Movimientos internos",
    "OUTGOING_TRANSFER": "Transferencias enviadas",
    "OUTGOING_TRANSFER_DELEGATION": "Transferencias enviadas",
    "BANK_TRANSACTION_OUTGOING": "Transferencias enviadas",
    "PAYMENT_OUTBOUND": "Transferencias enviadas",
    "JUNIOR_P2P_TRANSFER": "Transferencias enviadas",
}

# Pagos con tarjeta y transferencias salientes: primero se intenta clasificar por
# el comercio/concepto (p. ej. "Alquiler" -> Hogar) y si no, por el tipo de evento.
TEXT_FIRST_EVENT_TYPES = {
    "CARD_SUCCESSFUL_TRANSACTION", "CARD_TRANSACTION", "OUTGOING_TRANSFER",
    "OUTGOING_TRANSFER_DELEGATION", "BANK_TRANSACTION_OUTGOING", "PAYMENT_OUTBOUND",
}


def _match_default_rules(text: str) -> str | None:
    for pattern, category in DEFAULT_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return category
    return None


def categorize(title: str, event_type: str, amount: float,
               user_rules: list[tuple[str, str]] | None = None) -> str:
    """Devuelve la categoría de un movimiento.

    Orden: reglas del usuario > (pagos/transferencias) reglas por comercio >
    tipo de evento > reglas por comercio > valor por defecto según el signo.
    """
    text = title or ""
    for pattern, category in user_rules or []:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return category
        except re.error:
            # Si el usuario escribe una regex inválida, la tratamos como texto literal.
            if pattern.lower() in text.lower():
                return category

    event_type = (event_type or "").upper()
    if event_type in TEXT_FIRST_EVENT_TYPES and (cat := _match_default_rules(text)):
        return cat
    if event_type in EVENT_TYPE_CATEGORY:
        return EVENT_TYPE_CATEGORY[event_type]
    if cat := _match_default_rules(text):
        return cat

    if amount is not None and amount > 0:
        return "Nómina e ingresos"
    return "Otros gastos"
