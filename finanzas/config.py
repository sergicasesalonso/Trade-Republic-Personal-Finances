"""Rutas y ajustes globales.

Todos los datos personales viven en ``data/`` (ignorado por git). Las
credenciales de Trade Republic las guarda pytr en ``~/.pytr`` y este programa
nunca las lee ni las copia.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("FINANZAS_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "finanzas.db"
EVENTS_FILE = RAW_DIR / "all_events.json"
PORTFOLIO_FILE = RAW_DIR / "portfolio.csv"
