"""Matrices de puntuacion de la Fase 0 (deportes y fuentes de datos).

Las puntuaciones (1-5, 5 = mejor) y los pesos son juicios documentados en
docs/fase-0-investigacion.md. Cambia pesos o notas aqui y vuelve a ejecutar:
    python3 -I matrices_puntuacion.py
"""

SPORT_WEIGHTS = {
    "cobertura_gratuita": 20,
    "calidad_y_emparejamiento": 15,
    "simplicidad_liquidacion": 15,
    "disponibilidad_en_casas_es": 10,
    "historicos": 10,
    "validable_sin_dinero": 10,
    "riesgo_cuota_desactualizada": 10,  # 5 = riesgo bajo
    "pocos_resultados_a_cubrir": 10,
}

SPORTS = {
    "Futbol prepartido": dict(cobertura_gratuita=5, calidad_y_emparejamiento=4, simplicidad_liquidacion=4,
                              disponibilidad_en_casas_es=5, historicos=5, validable_sin_dinero=4,
                              riesgo_cuota_desactualizada=3, pocos_resultados_a_cubrir=4),
    "Tenis prepartido": dict(cobertura_gratuita=3, calidad_y_emparejamiento=3, simplicidad_liquidacion=2,
                             disponibilidad_en_casas_es=4, historicos=4, validable_sin_dinero=3,
                             riesgo_cuota_desactualizada=2, pocos_resultados_a_cubrir=5),
    "Baloncesto prepartido": dict(cobertura_gratuita=3, calidad_y_emparejamiento=4, simplicidad_liquidacion=3,
                                  disponibilidad_en_casas_es=4, historicos=2, validable_sin_dinero=2,
                                  riesgo_cuota_desactualizada=3, pocos_resultados_a_cubrir=4),
    "Cualquier deporte en directo": dict(cobertura_gratuita=1, calidad_y_emparejamiento=3, simplicidad_liquidacion=2,
                                         disponibilidad_en_casas_es=4, historicos=1, validable_sin_dinero=1,
                                         riesgo_cuota_desactualizada=1, pocos_resultados_a_cubrir=4),
}

SOURCE_WEIGHTS = {
    "coste": 25,
    "cobertura": 20,
    "fiabilidad": 20,
    "facilidad_implementacion": 15,
    "adecuacion_mercado_es": 20,
}

SOURCES = {
    "The Odds API gratis (500 cr/mes)": dict(coste=5, cobertura=3, fiabilidad=4, facilidad_implementacion=5, adecuacion_mercado_es=2),
    "The Odds API 20K (30 USD/mes)": dict(coste=2, cobertura=4, fiabilidad=4, facilidad_implementacion=5, adecuacion_mercado_es=2),
    "API-Football gratis (100/dia)": dict(coste=5, cobertura=2, fiabilidad=3, facilidad_implementacion=4, adecuacion_mercado_es=2),
    "Betfair Exchange ES clave retardada": dict(coste=5, cobertura=3, fiabilidad=4, facilidad_implementacion=2, adecuacion_mercado_es=5),
    "Betfair Exchange ES clave live (499 GBP)": dict(coste=1, cobertura=4, fiabilidad=5, facilidad_implementacion=2, adecuacion_mercado_es=5),
    "Odds-API.io (de pago, versiones .es)": dict(coste=1, cobertura=4, fiabilidad=3, facilidad_implementacion=4, adecuacion_mercado_es=5),
    "OddsPapi gratis (250/mes)": dict(coste=5, cobertura=2, fiabilidad=2, facilidad_implementacion=4, adecuacion_mercado_es=2),
    "Captura manual CSV de webs .es": dict(coste=5, cobertura=1, fiabilidad=4, facilidad_implementacion=5, adecuacion_mercado_es=5),
    "Scraping de webs .es (NO recomendado)": dict(coste=4, cobertura=4, fiabilidad=2, facilidad_implementacion=1, adecuacion_mercado_es=1),
    "Escaner comercial gratis (uso manual)": dict(coste=5, cobertura=3, fiabilidad=3, facilidad_implementacion=5, adecuacion_mercado_es=3),
    "CSV historicos football/tennis-data": dict(coste=5, cobertura=2, fiabilidad=4, facilidad_implementacion=5, adecuacion_mercado_es=2),
}


def score(table, weights):
    total_w = sum(weights.values())
    rows = []
    for name, notes in table.items():
        s = sum(notes[k] * w for k, w in weights.items()) / total_w
        rows.append((name, round(s, 2), notes))
    return sorted(rows, key=lambda r: r[1], reverse=True)


if __name__ == "__main__":
    print("== Deportes (pesos: %s)" % SPORT_WEIGHTS)
    for name, s, notes in score(SPORTS, SPORT_WEIGHTS):
        print(f"{s:4.2f}  {name}  {notes}")
    print("\n== Fuentes (pesos: %s)" % SOURCE_WEIGHTS)
    for name, s, notes in score(SOURCES, SOURCE_WEIGHTS):
        print(f"{s:4.2f}  {name}  {notes}")
