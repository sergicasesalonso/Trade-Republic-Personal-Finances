"""Descarga los datos de Trade Republic con pytr y los guarda en la base local.

Uso:
    python -m finanzas.sync                 # descarga movimientos + cartera
    python -m finanzas.sync --solo-importar # reimporta data/raw/all_events.json sin conectarse
    python -m finanzas.sync --demo          # genera datos de ejemplo (sin cuenta)

Antes de la primera sincronización ejecuta tú mismo ``pytr login --store_credentials``
(te pedirá teléfono, PIN y el código 2FA). pytr guarda la sesión en ~/.pytr;
este programa nunca lee ni guarda tus credenciales.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

from . import config, db
from .importer import load_events, load_portfolio_csv


def run_pytr(args: list[str]) -> tuple[int, str]:
    """Ejecuta pytr mostrando su salida en vivo (por si pide el código 2FA) y la devuelve."""
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "pytr", *args],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    captured = bytearray()
    while True:
        chunk = proc.stdout.read1(1024) if hasattr(proc.stdout, "read1") else proc.stdout.read(1)
        if not chunk:
            break
        captured += chunk
        sys.stdout.write(chunk.decode("utf-8", errors="replace"))
        sys.stdout.flush()
    return proc.wait(), captured.decode("utf-8", errors="replace")


def fetch_transactions() -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    code, _ = run_pytr([
        "export_transactions",
        "--outputdir", str(config.RAW_DIR),
        "--store-event-database",
        "--lang", "es",
        str(config.RAW_DIR / "account_transactions.csv"),
    ])
    if code != 0:
        raise SystemExit("pytr export_transactions ha fallado. ¿Has hecho `pytr login --store_credentials`?")


def fetch_portfolio() -> float | None:
    """Descarga la cartera a CSV y devuelve el efectivo disponible (si pytr lo muestra)."""
    code, out = run_pytr(["portfolio", "--output", str(config.PORTFOLIO_FILE)])
    if code != 0:
        print("Aviso: no se pudo descargar la cartera; sigo solo con los movimientos.")
        return None
    m = re.search(r"^Cash\s+\w+\s+(-?[\d.,]+)", out, re.MULTILINE)
    return float(m.group(1).replace(",", "")) if m else None


def import_local(cash: float | None = None) -> None:
    if not config.EVENTS_FILE.exists():
        raise SystemExit(f"No existe {config.EVENTS_FILE}. Ejecuta primero la sincronización.")
    rows = load_events(config.EVENTS_FILE)
    with db.connect() as conn:
        new, updated = db.upsert_transactions(conn, rows)
        print(f"Movimientos: {new} nuevos, {updated} actualizados.")
        if config.PORTFOLIO_FILE.exists():
            positions = load_portfolio_csv(config.PORTFOLIO_FILE)
            db.save_portfolio(conn, positions, cash, datetime.now().isoformat(timespec="seconds"))
            print(f"Cartera: {len(positions)} posiciones" + (f", efectivo {cash:.2f} €" if cash is not None else ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza tus datos de Trade Republic.")
    parser.add_argument("--solo-importar", action="store_true",
                        help="No conectarse a Trade Republic; solo reimportar los ficheros de data/raw.")
    parser.add_argument("--sin-cartera", action="store_true", help="No descargar la cartera.")
    parser.add_argument("--demo", action="store_true", help="Generar datos de ejemplo en data/demo.")
    args = parser.parse_args()

    if args.demo:
        from .demo import build_demo
        build_demo()
        return

    cash = None
    if not args.solo_importar:
        fetch_transactions()
        if not args.sin_cartera:
            cash = fetch_portfolio()
    import_local(cash)
    print(f"Listo. Base de datos: {config.DB_PATH}")


if __name__ == "__main__":
    main()
