# Pruebas técnicas de la Fase 0

Scripts y resultados que respaldan las cifras de [`../fase-0-investigacion.md`](../fase-0-investigacion.md) (Anexo B). **No forman parte de la aplicación**: son pruebas de investigación reproducibles.

## Requisitos

Python 3.10 o superior con `pandas` y `numpy` (los ejemplos matemáticos y la simulación solo usan la biblioteca estándar).

## Datos

Los datos no se suben al repositorio. Para reproducir, descárgalos en una carpeta fuera de esta (por ejemplo `~/datos-sb/`):

```bash
# Fútbol: réplica de football-data.co.uk con cuota de bet365 y cuota máxima de mercado
mkdir -p ~/datos-sb/futbol ~/datos-sb/tenis
curl -L -o ~/datos-sb/futbol/Matches.csv \
  https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv

# Tenis: espejo archivado de los datos de Jeff Sackmann (licencia CC BY-NC-SA 4.0, uso no comercial)
base=https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main
for y in 2019 2020 2021 2022 2023 2024 2025 2026; do
  for f in atp/atp_matches_$y.csv atp/atp_matches_qual_chall_$y.csv wta/wta_matches_$y.csv wta/wta_matches_qual_itf_$y.csv; do
    curl -fsSL -o ~/datos-sb/tenis/$(basename $f) $base/$f || echo "no disponible: $f"
  done
done
```

## Cómo ejecutar

Desde esta carpeta (`-I` aísla el intérprete de ficheros locales):

```bash
python3 -I scripts/arbitrajes_aparentes_futbol.py ~/datos-sb/futbol/Matches.csv resultados/futbol
python3 -I scripts/control_cambio_metodologia_futbol.py ~/datos-sb/futbol/Matches.csv
python3 -I scripts/retiradas_tenis.py ~/datos-sb/tenis resultados/tenis
python3 -I scripts/ejemplos_matematicos.py
python3 -I scripts/simulacion_anulacion_asimetrica.py
python3 -I scripts/matrices_puntuacion.py
```

## Qué contiene cada resultado

| Fichero | Contenido |
|---|---|
| `resultados/futbol/resumen_global.csv` | % de partidos con `S < 1`, `< 0,99`, `< 0,98` y `< 0,95` usando la cuota máxima de mercado (1X2 y más/menos 2,5) |
| `resultados/futbol/por_temporada_*.csv` | La misma métrica por temporada (todas las ligas y LaLiga) y margen mediano de bet365 |
| `resultados/futbol/margen_b365_por_division_2022_2024.csv` | Margen mediano de bet365 en 1X2 por liga |
| `resultados/futbol/control_metodologia.txt` | Control que detecta el cambio de método de la réplica desde 2025/26 |
| `resultados/futbol/salida_consola.txt` | Salida completa, incluidos los casos con retorno aparente > 11% |
| `resultados/tenis/retiradas_*.csv` | Retiradas (con y sin set completado), walkovers y descalificaciones por circuito y año |
| `resultados/tenis/simulacion_anulacion_asimetrica.txt` | Simulación del efecto de mezclar reglas de retirada |
| `resultados/ejemplos_matematicos.txt` | Todos los ejemplos numéricos del documento recalculados con `Decimal` |
| `resultados/matrices_puntuacion.txt` | Puntuaciones ponderadas de deportes y fuentes |

## Limitaciones conocidas

- La "cuota máxima de mercado" combina casas distintas en momentos distintos, muchas sin licencia en España. Es un techo teórico, no una tasa de arbitrajes ejecutables.
- Las filas de 2025/26 en adelante de la réplica de fútbol usan otra metodología (ver `control_metodologia.txt`) y no son comparables con las anteriores.
- En tenis, una retirada se clasifica "con set completado" si el marcador incluye al menos un set terminado (6-x con diferencia de 2, 7-5, 7-6 o desempates largos).
- Fecha de descarga de los datos: 15/10/2026.
