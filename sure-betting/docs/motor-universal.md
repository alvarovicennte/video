# Motor universal de arbitraje

**Qué resuelve.** Dado un partido de cualquier deporte y todas las cuotas que tengamos de él (de todas las casas y de todos los mercados), encuentra la combinación de apuestas que **garantiza el mayor retorno en todos los escenarios posibles**, o demuestra que no existe. No hay que elegir deporte ni mercado.

Código: `src/surebet/engine/lp.py` (matemática), `src/surebet/engine/scenarios.py` (deportes y mercados) y `src/surebet/universal.py` (escáner). Pruebas: `tests/test_universal.py`.

## 1. La idea en una frase

Cada apuesta es un vector de pagos sobre los escenarios que pueden ocurrir. Un arbitraje es una mezcla de apuestas que cobra al menos lo apostado en **todos** los escenarios. Encontrar la mejor mezcla es un problema de **programación lineal**, y la programación lineal tiene solución exacta y demostrablemente óptima.

## 2. Formulación

- Escenarios `s` (por ejemplo, marcadores 0-0, 1-0, 2-1… o "gana P1", "P2 se retira tras el primer set").
- Apuestas `j` con pago bruto por euro apostado `R[j][s]`: la cuota si gana, 1 si se devuelve, 0 si pierde, y valores intermedios en líneas de cuarto (por ejemplo, 1,5 si la mitad gana a 2,00 y la otra mitad se devuelve).

```
min  V = Σ_j y_j
s.a. Σ_j y_j · R[j][s] ≥ 1     para todo escenario s
     y_j ≥ 0
```

Si `V < 1`, apostando `y_j` en cada apuesta pones `V` y cobras al menos 1 pase lo que pase. El retorno garantizado es `1/V − 1`. Con una sola apuesta por resultado de un mercado simple, `V` es exactamente la suma de probabilidades `S` de siempre, y una prueba lo comprueba con miles de casos.

**El dual** (lo que el programa resuelve por dentro) busca probabilidades `p_s ≥ 0` que maximicen `Σ p_s` sin que ninguna apuesta tenga valor positivo (`Σ_s R[j][s]·p_s ≤ 1`). Por dualidad, `máx Σp = V`. Se lee así: hay arbitraje justo cuando **no existe ningún reparto de probabilidades** que haga justas a la vez todas las cuotas disponibles. Es el teorema fundamental de la valoración sin arbitraje, aplicado a las apuestas.

## 3. Exactitud

- El simplex está escrito con fracciones exactas (`fractions.Fraction`) y la regla de Bland, que garantiza que termina.
- Cada solución se comprueba al final por dualidad fuerte: la suma de importes es igual al valor óptimo, y el pago mínimo es ≥ 1. Si no cuadra, el programa se detiene en lugar de dar un número dudoso.
- No hay `float` en ninguna decisión. Esto ya evitó un error real: con decimales, tres cuotas de 3,00 parecían un arbitraje.

## 4. Deportes y mercados

| Modelo | Deportes | Escenarios | Mercados |
|---|---|---|---|
| `score` (marcador) | Fútbol 90', baloncesto u hockey a tiempo reglamentario, balonmano | Marcadores representativos alrededor de cada línea | 1X2, empate no apuesta (DNB), doble oportunidad (DC), hándicap asiático (entero, medio y de cuarto), totales (ídem), ambos marcan |
| `winner` (ganador) | Tenis, tenis de mesa, bádminton, pádel; también dardos, MMA o esports sin retiradas | Gana P1, gana P2 y, en deportes de raqueta, cuatro escenarios de retirada | Ganador del partido |

**Marcadores representativos.** No hace falta probar todos los marcadores posibles. Los pagos solo cambian al cruzar una línea, así que basta con los marcadores alrededor de cada umbral más los marcadores pequeños. Una prueba con `hypothesis` compara el resultado contra todos los marcadores hasta 12-12 en combinaciones aleatorias de mercados, y salen idénticos.

**Retiradas con la regla de cada casa.** Para cada casa y deporte se indica su regla:

| Regla | Si un jugador se retira |
|---|---|
| `MATCH_COMPLETED` | Se anula la apuesta (bet365 en tenis, según su ayuda) |
| `ONE_SET` | Se anula si no se completó un set; si no, gana quien pasa de ronda (Betfair Sportsbook) |
| `BALL_SERVED` | Gana quien pasa de ronda en cuanto empieza el partido |
| `UNKNOWN` | Peor caso: la apuesta se pierde |

El motor exige beneficio también en esos escenarios. Si dos casas tienen reglas distintas, no da el arbitraje por bueno: lo marca como **frágil** ("solo sale si nadie se retira"), que es exactamente el riesgo medido en la Fase 0, donde un 2-3% de partidos acaban en retirada tras un set.

**Escenarios en que todo se devuelve.** Por ejemplo, total de 2 goles con resultado 1-1 apostando a más y menos de 2. Se ignoran porque dan 0 pase lo que pase: ni pierdes ni ganas.

**Exchange.** Una apuesta en contra (lay) a cuota `L` con comisión `k` equivale a apostar a favor del resultado contrario con cuota `1 + (1−k)/(L−1)` sobre la responsabilidad. Con eso, casa contra exchange es un caso más del mismo programa, y da el mismo 1,69% sobre el capital que el ejemplo 5 del documento.

## 5. Qué encuentra que un escáner simple no ve

1. **Arbitrajes entre mercados.** Por ejemplo, "empate no apuesta local" a 1,80 en una casa y "doble oportunidad X2" a 2,40 en otra: 2,86% garantizado. Ninguno de los dos mercados tiene arbitraje por sí solo.
2. **Líneas enteras y de cuarto** con devoluciones parciales, calculadas exactamente.
3. **La mejor mezcla posible**, no la primera que aparece: si hay varias formas de cubrir, elige la de mayor retorno.
4. **Robustez frente a las reglas de anulación**, en lugar de una lista de casas prohibidas.

## 6. Límites (lo que el algoritmo no puede arreglar)

- **Datos.** El motor es tan bueno como las cuotas que recibe. Sin cuotas rápidas de las webs `.es`, no hay arbitrajes reales que encontrar (Fase 0, sección 5).
- **Periodos.** No mezcla mercados de periodos distintos (90 minutos frente a prórroga incluida). Cada periodo se analiza por separado.
- **Aplazamientos y partidos suspendidos** en fútbol aún no se modelan como escenarios. La siguiente mejora natural es añadirlos con las ventanas de cada casa (por ejemplo, 5 días en bet365).
- **Ejecución.** Cuotas que cambian, límites de importe y limitación de cuentas siguen siendo los riesgos principales.

## 7. Cómo usarlo

```
surebet scan docs/ejemplos/cuotas_multideporte_inventadas.csv --banca 100 --paso 1
surebet scan-db          # sobre las cuotas capturadas con `surebet ingest`
```

Formato del CSV: `event_id, event_name, sport, period, market, line, outcome, side, book, odds, commission, rule, captured_at`. El archivo de ejemplo usa cuotas inventadas.
