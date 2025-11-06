from __future__ import annotations
import os, yaml, pathlib

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "digest.db"
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "sources.yaml"

def load_config(path: str | os.PathLike | None = None) -> dict:
    cfg_path = pathlib.Path(path) if path else DEFAULT_CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError("Invalid config file: missing 'sources' key")
    return data

def get_db_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DB_PATH", DEFAULT_DB_PATH))
