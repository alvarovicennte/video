# SURE BETTING

Herramienta personal para detectar y **verificar** oportunidades de arbitraje deportivo (surebets).

## Estado

- **Fase 0 (investigacion):** hecha. Ver [`docs/fase-0-investigacion.md`](docs/fase-0-investigacion.md).
- **H1 (calculadora verificable + datos de prueba):** hecha. 40 pruebas automaticas.
- **H2 (captura de The Odds API):** codigo hecho y probado sin red (52 pruebas). Falta la primera llamada real.
- Siguiente: H3 (detector).

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

## Primera llamada real a The Odds API (prueba PT-1)

Necesitas tu clave gratuita. **Nunca la pegues en el chat ni en un archivo que se suba a GitHub.**

1. En la carpeta `sure-betting`, copia `.env.example` y renombra la copia a `.env` (si Windows no te deja, abre el Bloc de notas, guarda como `.env` con tipo "Todos los archivos").
2. Abre `.env` y sustituye `pon_aqui_tu_clave` por tu clave. Guarda.
3. En la ventana `cmd` de antes (con `.venv\Scripts\activate` hecho), ejecuta una linea cada vez:

```
pip install -e .[dev]
surebet sports --buscar spain
surebet ingest soccer_spain_la_liga --mercados h2h --regiones eu
```

- `sports` no gasta creditos segun la documentacion. Enseña las claves de liga.
- `ingest` gasta 1 credito (1 mercado x 1 region) y se niega si cuesta mas de `--max-creditos` (4 por defecto) o si quedan menos de 25.
- Te mostrara cuantos eventos y cuotas guardo, que casas devolvio y si traen hora de actualizacion.
- Los datos se guardan en `data/` (no se sube a GitHub). Puedes repetirlo; las capturas se anaden, no se sobrescriben.
