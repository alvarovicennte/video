# SURE BETTING — reglas del proyecto

- Nunca inventar cuotas, resultados ni reglas. Si falta un dato, se marca como desconocido y bloquea la verificacion.
- Calculos de cuotas y dinero solo con Decimal. Prohibido float en src/surebet/engine (hay un test que lo vigila).
- Todo cambio en el motor matematico va con tests. Los casos dorados de docs/fase-0-investigacion.md no se tocan.
- Cada cuota guardada lleva proveedor, hora de captura (UTC), hora de actualizacion del proveedor y referencia a la respuesta original.
- Las cuotas se anaden; nunca se sobrescriben.
- Prohibido el scraping de webs de casas y de comparadores. Solo APIs autorizadas y captura manual.
- Las credenciales viven en .env (nunca en git, nunca en logs).
- Los tests no llaman a APIs reales: usan respuestas grabadas en tests/fixtures.
- Ninguna llamada a una API sin pasar por el gestor de cuota.
- La IA no participa en el calculo ni en la verificacion de oportunidades.
- Codigo e identificadores en ingles; documentacion y mensajes al usuario en espanol.
- Cada hito termina comprobando sus criterios de aceptacion.
