"""Lectura de credenciales. La clave vive en .env o en una variable de entorno."""
from __future__ import annotations

import os
from pathlib import Path


class ConfigError(Exception):
    pass


def load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    p = Path(path)
    out: dict[str, str] = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_odds_api_key(env_path: str | Path = ".env") -> str:
    key = os.environ.get("ODDS_API_KEY") or load_dotenv(env_path).get("ODDS_API_KEY")
    if not key or key == "pon_aqui_tu_clave":
        raise ConfigError("Falta la clave. Crea un archivo .env con la linea: ODDS_API_KEY=tu_clave")
    return key
