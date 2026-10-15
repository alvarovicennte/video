# SURE BETTING

Herramienta personal para detectar y **verificar** oportunidades de arbitraje deportivo (surebets) entre casas con licencia en España.

## Estado

**Fase 0 terminada: investigación, viabilidad y arquitectura.** Todavía no hay código de la aplicación.

- Documento principal: [`docs/fase-0-investigacion.md`](docs/fase-0-investigacion.md)
- Pruebas técnicas reproducibles: [`docs/pruebas-fase-0/`](docs/pruebas-fase-0/)

## Conclusión en cuatro líneas

1. Ninguna fuente gratuita y autorizada da cuotas automáticas de las webs `.es`; con 0 € se construye un sistema de **detección + verificación manual + medición**, no un escáner en tiempo real.
2. Primer deporte: fútbol prepartido (1X2 y más/menos 2,5 en LaLiga y Premier League).
3. Fuentes: The Odds API (detección), Betfair Exchange ES (mercado español oficial) y captura manual (verificación).
4. Stack: Python + SQLite + línea de comandos; motor determinista con `Decimal` y tests; sin IA en el camino crítico.

## Siguiente paso

Responder a las decisiones 1 y 2 de la sección 14 del documento (objetivo del proyecto y repositorio) y empezar el hito H1: calculadora verificable y datos de prueba.
