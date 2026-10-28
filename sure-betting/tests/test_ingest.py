"""H2 sin red ni claves. El fixture sigue el formato documentado de la API v4; la primera
llamada real confirmara que coincide (prueba PT-1)."""
import gzip
import json
from decimal import Decimal as D
from pathlib import Path

import pytest

from surebet.ingest import run_ingest
from surebet.providers import the_odds_api as t
from surebet.quota import BudgetError, check_budget
from surebet.storage.db import connect

FIX = Path(__file__).parent / "fixtures" / "the_odds_api_sample.json"
KEY = "SECRETKEY123"


def fake_http(status=200, remaining=495, body=None):
    data = body if body is not None else FIX.read_bytes()

    def http(url):
        assert KEY in url  # la clave solo viaja en la peticion
        return status, {"x-requests-remaining": str(remaining), "x-requests-used": str(500 - remaining),
                        "x-requests-last": "2"}, data
    return http


def test_parse_mapea_resultados_y_conserva_decimales():
    qs = t.parse_odds(FIX.read_bytes(), "2026-10-30T10:01:00Z")
    h2h = {(q.book_key, q.outcome): q.odds for q in qs if q.market_code == "FT_1X2"}
    assert h2h[("williamhill", "HOME")] == D("2.45")
    assert h2h[("williamhill", "DRAW")] == D("3.1")
    assert h2h[("williamhill", "AWAY")] == D("3.4")
    ou = {(q.outcome, q.line): q.odds for q in qs if q.market_code == "FT_OU"}
    assert ou[("OVER", "2.5")] == D("2.08") and ou[("UNDER", "2.5")] == D("1.75")
    assert all(isinstance(q.odds, D) for q in qs)


def test_resultado_desconocido_queda_marcado():
    qs = t.parse_odds(FIX.read_bytes(), "x")
    assert any(q.outcome == "UNMAPPED:Equipo raro" for q in qs)


def test_hora_de_actualizacion_por_mercado_o_casa():
    qs = {(q.book_key, q.market_code): q.book_updated_at for q in t.parse_odds(FIX.read_bytes(), "x")}
    assert qs[("williamhill", "FT_OU")] == "2026-10-30T10:00:06Z"
    assert qs[("betsson", "FT_1X2")] == "2026-10-30T09:59:40Z"  # cae al valor de la casa


def test_fuera_del_futbol_el_periodo_es_unknown():
    body = json.dumps([{"id": "b1", "sport_key": "basketball_nba", "commence_time": "z", "home_team": "A",
                        "away_team": "B", "bookmakers": [{"key": "k", "markets": [{"key": "h2h", "outcomes": [
                            {"name": "A", "price": 1.9}, {"name": "B", "price": 1.9}]}]}]}]).encode()
    q = t.parse_odds(body, "x")[0]
    assert q.period == "UNKNOWN"


def test_ingest_guarda_todo_y_la_clave_no(tmp_path):
    conn = connect(tmp_path / "t.db")
    api = t.TheOddsApi(KEY, http=fake_http())
    s = run_ingest(api, conn, "soccer_spain_la_liga", ["h2h", "totals"], ["eu"], tmp_path / "raw", per_run_max=4)
    assert (s.events, s.quotes, s.status) == (1, 8, 200)
    assert s.credits_remaining == 495 and s.unmapped == 1
    assert conn.execute("SELECT COUNT(*) FROM odds_quote").fetchone()[0] == 8
    row = conn.execute("SELECT * FROM poll").fetchone()
    assert KEY not in json.dumps(dict(row))
    raw = Path(row["raw_path"])
    assert json.loads(gzip.decompress(raw.read_bytes())) == json.loads(FIX.read_bytes())


def test_capturas_se_anaden_no_se_sobrescriben(tmp_path):
    conn = connect(tmp_path / "t.db")
    api = t.TheOddsApi(KEY, http=fake_http())
    run_ingest(api, conn, "soccer_spain_la_liga", ["h2h"], ["eu"], tmp_path / "raw")
    run_ingest(api, conn, "soccer_spain_la_liga", ["h2h"], ["eu"], tmp_path / "raw")
    assert conn.execute("SELECT COUNT(*) FROM poll").fetchone()[0] == 2


def test_error_http_se_registra_sin_cuotas(tmp_path):
    conn = connect(tmp_path / "t.db")
    api = t.TheOddsApi(KEY, http=fake_http(401, 0, b'{"message":"invalid key"}'))
    s = run_ingest(api, conn, "soccer_spain_la_liga", ["h2h"], ["eu"], tmp_path / "raw")
    assert s.error and s.quotes == 0
    assert conn.execute("SELECT http_status FROM poll").fetchone()[0] == 401


def test_presupuesto_por_ejecucion(tmp_path):
    conn = connect(tmp_path / "t.db")
    api = t.TheOddsApi(KEY, http=fake_http())
    with pytest.raises(BudgetError):
        run_ingest(api, conn, "soccer_spain_la_liga", ["h2h", "totals"], ["eu", "uk", "fr"], tmp_path / "raw", per_run_max=4)
    assert conn.execute("SELECT COUNT(*) FROM poll").fetchone()[0] == 0  # no llamo


def test_reserva_de_creditos(tmp_path):
    conn = connect(tmp_path / "t.db")
    api = t.TheOddsApi(KEY, http=fake_http(remaining=26))
    run_ingest(api, conn, "soccer_spain_la_liga", ["h2h"], ["eu"], tmp_path / "raw")
    with pytest.raises(BudgetError):
        check_budget(conn, t.PROVIDER, 2, 4, reserve=25)


def test_errores_de_red_no_filtran_la_clave():
    def boom(url):
        raise t.SourceError(f"fallo en {url}")
    with pytest.raises(t.SourceError) as e:
        t.TheOddsApi(KEY, http=boom).sports()
    assert KEY not in str(e.value)


def test_estimacion_de_coste():
    assert t.estimate_cost(["h2h", "totals"], ["eu"]) == 2
    assert t.estimate_cost(["h2h"], ["eu", "uk"]) == 2


def test_lectura_de_clave(tmp_path, monkeypatch):
    from surebet.config import ConfigError, get_odds_api_key
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        get_odds_api_key(tmp_path / ".env")
    (tmp_path / ".env").write_text("# nota\nODDS_API_KEY=abc123\n", encoding="utf-8")
    assert get_odds_api_key(tmp_path / ".env") == "abc123"
    (tmp_path / ".env").write_text("ODDS_API_KEY=pon_aqui_tu_clave\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        get_odds_api_key(tmp_path / ".env")
