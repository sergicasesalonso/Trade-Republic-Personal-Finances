# Finanzas personales con Trade Republic

Programa local que descarga los datos de tu cuenta de Trade Republic con
[pytr](https://github.com/pytr-org/pytr) y te muestra un dashboard de finanzas
personales:

- **Inicio**: cuánto puedes gastar hoy, cómo vas respecto al ritmo del mes,
  ingresos, gastos, ahorro y patrimonio, últimos movimientos y los últimos 12 meses.
- **Gastos**: total del mes frente al anterior, ranking por categoría (pulsa una
  para ver sus movimientos), comercios donde más gastas y evolución por categoría.
- **Objetivos**: objetivo de ahorro mensual o límite de gasto, límites por
  categoría y **cuánto puedes gastar cada día** para cumplirlos. Los gastos
  fijos (alquiler, facturas...) se reservan aparte y no te bajan el
  presupuesto diario.
- **Movimientos**: lista agrupada por día con buscador y filtro, y un modo
  «Editar categorías» (con opción de crear una regla para ese comercio).
- **Cartera**: valor, ganancia latente, evolución del patrimonio, posiciones y
  distribución.
- **Ajustes**: datos de ejemplo, estado de la sincronización, categorías (fijas
  o excluidas, p. ej. traspasos entre tus cuentas) y reglas automáticas.

Todo se guarda en `data/` (una base SQLite) en tu ordenador y está excluido de git.

## Instalación

```bash
pip install -r requirements.txt
```

## 1. Iniciar sesión en Trade Republic (solo la primera vez)

Esto lo ejecutas tú: pytr te pedirá tu número de teléfono (formato `+34...`),
tu PIN y el código que te llega a la app/SMS.

```bash
pytr login --store_credentials
```

pytr guarda la sesión en `~/.pytr` (fuera de este repositorio). Este programa no
lee ni guarda nunca tu teléfono, PIN ni tokens. Si en algún momento la sesión
caduca, la sincronización te volverá a pedir el código 2FA en la terminal.

## 2. Descargar tus datos

```bash
python -m finanzas.sync
```

Descarga el historial completo de movimientos (`data/raw/all_events.json`) y la
cartera, y lo importa en `data/finanzas.db`. Puedes repetirlo cuando quieras:
los movimientos se actualizan sin duplicarse y las categorías que hayas cambiado
a mano se respetan.

Otras opciones:

```bash
python -m finanzas.sync --solo-importar   # reimportar sin conectarse
python -m finanzas.sync --sin-cartera     # solo movimientos
python -m finanzas.sync --demo            # datos de ejemplo en data/demo
```

## 3. Abrir el dashboard

```bash
streamlit run app.py
```

Se abre en http://localhost:8501. El mes se elige arriba a la derecha de cada
página y se mantiene al cambiar de página; los datos de ejemplo se activan en
Ajustes. El tema (claro u oscuro) sigue al de tu sistema.

El diseño imita el lenguaje visual de Trade Republic: los tokens están en
`design/DESIGN.md`, el CSS en `finanzas/ui/theme.css` y los componentes en
`finanzas/ui/`.

## Cómo se calcula el gasto diario

1. **Presupuesto del mes** = límite de gasto total si lo defines; si no,
   ingresos previstos − objetivo de ahorro (los ingresos previstos son los del
   mes o, si aún no han llegado, la media de los 3 meses anteriores); si no,
   la suma de los límites por categoría.
2. Se reservan los **gastos fijos previstos** (categorías marcadas como fijas:
   lo ya pagado este mes o la media de los 3 meses anteriores).
3. Lo que queda es el presupuesto **para el día a día**. Se divide lo que
   queda de él (sin contar lo gastado hoy) entre los días que faltan, incluido
   hoy. «Puedes gastar hoy» resta lo que ya has gastado hoy.

## Categorías

La clasificación automática usa, por este orden: tus reglas, el nombre del
comercio (Mercadona, Glovo, Renfe, Netflix...), el tipo de evento de Trade
Republic (intereses, dividendos, órdenes, transferencias...) y, si nada encaja,
«Otros gastos» o «Nómina e ingresos» según el signo. Cada categoría tiene un
tipo: `gasto`, `ingreso`, `inversion` o `excluido` (no cuenta en los totales).

## Tests

```bash
python -m pytest
```
