"""Centralised runtime paths for the aircraft tracker."""

from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
KMLS_DIR = PROJECT_DIR / 'kmls'
AIRCRAFT_JSON_PATH = Path('/var/run/dump1090-fa/aircraft.json')


def ensure_runtime_dirs() -> None:
    """Create directories used for generated runtime artifacts."""
    KMLS_DIR.mkdir(exist_ok=True, parents=True)


def database_path(name: str) -> str:
    """Return a sqlite database path inside the project directory."""
    return str(PROJECT_DIR / name)


def kml_path(name: str, suffix: str = 'kmz') -> str:
    """Return a path for generated KMZ/KML output."""
    ensure_runtime_dirs()
    return str(KMLS_DIR / f'{name}.{suffix}')
