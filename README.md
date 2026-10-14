# Finanzas personales con Trade Republic

Uso Trade Republic como cuenta principal y quería controlar mis gastos, pero
ninguna app de finanzas personales se conecta a Trade Republic de forma
automática. Así que me hice la mía. Esto es solo un proyecto personal que no pretendo deployear,
a no ser que exista interés para ello.

He intentado que tenga la misma UI que la original de Trade Republic. 

![Trade Republic UI](design/screenshots/Captura%20de%20pantalla%202026-10-14%20105353.png)


Es un programa que corre en mi ordenador: descarga los movimientos de mi cuenta
con [pytr](https://github.com/pytr-org/pytr) y me enseña un dashboard con mis
gastos por categoría, objetivos de ahorro mensuales, cuánto puedo gastar cada
día para cumplirlos y cómo va mi cartera.

Mis credenciales y mis datos no salen de mi ordenador: pytr guarda la sesión en
`~/.pytr` y todo lo demás vive en `data/` (una base SQLite excluida de git).

## Cómo lo uso

```bash
pip install -r requirements.txt

# Solo la primera vez: pytr pide teléfono (+34...), PIN y código 2FA
pytr login --store_credentials

# Descargar o actualizar mis movimientos y la cartera
python -m finanzas.sync

# Abrir el dashboard en http://localhost:8501
streamlit run app.py
```

Puedo repetir la sincronización cuando quiera: no duplica movimientos y respeta
las categorías que he cambiado a mano. Si solo quieres probarlo, en Ajustes
puedes activar datos de ejemplo (o usar `python -m finanzas.sync --demo`).

## Tests

```bash
python -m pytest
```
