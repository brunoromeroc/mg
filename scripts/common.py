"""Utilidades compartidas por sync_official.py y build.py."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONSOLAS_FILE = ROOT / "consolas.yaml"
BASE_DIR = ROOT / "base"
OVERRIDES_DIR = ROOT / "overrides"
DIST_DIR = ROOT / "dist"
LOCK_FILE = ROOT / "revisions.lock.json"

CLAVE_VALIDA = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ErrorClaro(Exception):
    """Error con un mensaje pensado para que lo lea una persona, no un dev."""


def leer_json(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErrorClaro(f"El archivo {ruta} no es un JSON valido: {e}") from e


def escribir_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(datos, indent=2, ensure_ascii=False) + "\n"
    ruta.write_text(texto, encoding="utf-8", newline="\n")


def cargar_consolas() -> dict[str, dict]:
    """Lee consolas.yaml y valida que tenga la forma esperada."""
    if not CONSOLAS_FILE.exists():
        raise ErrorClaro(f"No encuentro {CONSOLAS_FILE}")

    datos = yaml.safe_load(CONSOLAS_FILE.read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or not datos:
        raise ErrorClaro("consolas.yaml esta vacio o mal armado: tiene que tener al menos una consola.")

    for clave, cfg in datos.items():
        if not isinstance(clave, str) or not CLAVE_VALIDA.match(clave):
            raise ErrorClaro(
                f"El nombre de consola '{clave}' no sirve como carpeta.\n"
                "Usa solo minusculas, numeros y guiones (ejemplo: rg-ds, rg-35xx-h)."
            )
        if not isinstance(cfg, dict):
            raise ErrorClaro(f"La consola '{clave}' esta mal armada: le faltan 'nombre' y 'plataformas'.")
        if not cfg.get("nombre"):
            raise ErrorClaro(f"La consola '{clave}' no tiene 'nombre'.")
        plataformas = cfg.get("plataformas")
        if not isinstance(plataformas, list) or not plataformas:
            raise ErrorClaro(f"La consola '{clave}' no tiene plataformas cargadas.")
        vistas = set()
        for p in plataformas:
            if not isinstance(p, str) or not p.strip():
                raise ErrorClaro(f"La consola '{clave}' tiene una plataforma vacia o invalida.")
            if p in vistas:
                raise ErrorClaro(f"La consola '{clave}' tiene la plataforma '{p}' repetida.")
            vistas.add(p)

    return datos


def plataformas_usadas(consolas: dict[str, dict]) -> set[str]:
    usadas: set[str] = set()
    for cfg in consolas.values():
        usadas.update(cfg["plataformas"])
    return usadas


def repo_desde_git() -> tuple[str, str]:
    """Devuelve (usuario, repo) leyendo el remote 'origin' del repositorio git."""
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ErrorClaro(
            "No pude averiguar a que repositorio de GitHub apunta esta carpeta.\n"
            "Solucion: conecta el repo con\n"
            "  git remote add origin https://github.com/USUARIO/marketgamer-daijisho.git\n"
            "o corre el script pasando el dato a mano:\n"
            "  py scripts/build.py --repo USUARIO/marketgamer-daijisho"
        ) from e

    m = re.match(r"^(?:https://github\.com/|git@github\.com:)([^/]+)/(.+?)(?:\.git)?/?$", url)
    if not m:
        raise ErrorClaro(
            f"El remote 'origin' ({url}) no parece de GitHub.\n"
            "Corre el script pasando el dato a mano:\n"
            "  py scripts/build.py --repo USUARIO/marketgamer-daijisho"
        )
    return m.group(1), m.group(2)
