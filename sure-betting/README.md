# SURE BETTING

Herramienta personal para detectar y **verificar** oportunidades de arbitraje deportivo (surebets).

## Estado

- **Fase 0 (investigacion):** hecha. Ver [`docs/fase-0-investigacion.md`](docs/fase-0-investigacion.md).
- **H1 (calculadora verificable + datos de prueba):** hecha. 40 pruebas automaticas.
- Siguiente: **H2** (primera fuente real de cuotas).

## Probar la calculadora en Windows (opcional, solo si quieres)

1. Instala Python 3.12 o superior desde https://www.python.org/downloads/ y **marca la casilla "Add python.exe to PATH"** al instalar.
2. Abre la carpeta `sure-betting` en el Explorador, haz clic en la barra de direcciones, escribe `cmd` y pulsa Enter.
3. Copia y pega, una linea cada vez:

```
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
surebet calc 2,10 2,00 --banca 100 --paso 1
```

Otros comandos:

```
surebet calc 2,45 3,60 3,40 --paso 1
surebet backlay 100 2,20 2,10 --comision 0,02
surebet gen-test-data
pytest
```

`surebet calc` te dice si hay arbitraje, cuanto apostar a cada resultado y cuanto pierdes por redondear.
Las cuotas se escriben con coma o con punto. Es teoria: no sabe si la cuota sigue disponible en la web.
