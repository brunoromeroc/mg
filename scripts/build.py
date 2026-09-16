"""Genera dist/<consola>/index.json + los JSON de cada plataforma.

Uso:
    py scripts/build.py
    py scripts/build.py --repo USUARIO/marketgamer-daijisho   (si no hay remote de git)

Reglas de revisionNumber (para que las consolas detecten actualizaciones):
  - Si el contenido de una plataforma no cambio, se mantiene la revision anterior.
  - Si cambio (o es nueva), la nueva revision es:
        max(revision anterior + 1, revision oficial)
    asi el numero siempre sube y nunca baja.
El estado se guarda en revisions.lock.json (lo maneja este script, no lo edites).

Si algo no valida, el script no escribe NADA: dist/ queda como estaba.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import sys

from common import (
    BASE_DIR,
    DIST_DIR,
    LOCK_FILE,
    OVERRIDES_DIR,
    ErrorClaro,
    cargar_consolas,
    escribir_json,
    leer_json,
    repo_desde_git,
)

RAW = "https://raw.githubusercontent.com"


def hash_contenido(datos: dict) -> str:
    """Huella del contenido IGNORANDO revisionNumber."""
    sin_rev = {k: v for k, v in datos.items() if k != "revisionNumber"}
    texto = json.dumps(sin_rev, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def resolver_repo(arg_repo: str | None) -> tuple[str, str]:
    origen = arg_repo or os.environ.get("GITHUB_REPOSITORY")
    if origen:
        if "/" not in origen:
            raise ErrorClaro(f"'{origen}' no tiene la forma USUARIO/REPO.")
        usuario, repo = origen.split("/", 1)
        return usuario, repo
    return repo_desde_git()


def existe_exacto(carpeta, nombre_archivo: str) -> bool:
    """Como .exists() pero respetando mayusculas/minusculas.

    Windows no distingue mayusculas y Linux si. Sin esto, un nombre mal escrito
    en consolas.yaml funcionaria en la compu y fallaria recien en GitHub.
    """
    if not carpeta.is_dir():
        return False
    return nombre_archivo in {p.name for p in carpeta.iterdir()}


def archivo_fuente(consola: str, plataforma: str):
    """Devuelve (ruta, de_donde). Prioriza overrides/<consola>/ sobre base/."""
    nombre = f"{plataforma}.json"
    if existe_exacto(OVERRIDES_DIR / consola, nombre):
        return OVERRIDES_DIR / consola / nombre, "override"
    if existe_exacto(BASE_DIR, nombre):
        return BASE_DIR / nombre, "base"

    disponibles = sorted(p.stem for p in BASE_DIR.glob("*.json")) if BASE_DIR.is_dir() else []
    parecidos = difflib.get_close_matches(plataforma, disponibles, n=3, cutoff=0.5)
    ayuda = ""
    if parecidos:
        ayuda = (
            f"\n\n¿Quisiste decir: {', '.join(parecidos)}?\n"
            "(Los nombres van EXACTO, respetando mayusculas y minusculas.)"
        )
    raise ErrorClaro(
        f"La consola '{consola}' usa la plataforma '{plataforma}', pero ese archivo no existe.\n"
        f"Busque en base/{nombre} y en overrides/{consola}/{nombre}.{ayuda}\n\n"
        "Si el nombre esta bien escrito, lo que falta es bajarlo:\n"
        "  py scripts/sync_official.py"
    )


def revision_oficial(plataforma: str) -> int:
    base = BASE_DIR / f"{plataforma}.json"
    if not base.exists():
        return 0
    valor = leer_json(base).get("revisionNumber", 0)
    return valor if isinstance(valor, int) else 0


def construir(consolas: dict, lock: dict, usuario: str, repo: str, branch: str) -> tuple[dict, dict, list[str]]:
    """Arma todo en memoria. Devuelve (salidas, lock_nuevo, novedades)."""
    salidas: dict[str, dict] = {}   # ruta relativa -> contenido JSON
    lock_nuevo = json.loads(json.dumps(lock))  # copia; conserva entradas viejas
    lock_nuevo.setdefault("consolas", {})
    novedades: list[str] = []

    for consola, cfg in consolas.items():
        base_uri = f"{RAW}/{usuario}/{repo}/{branch}/dist/{consola}/"
        estado_consola = lock_nuevo["consolas"].setdefault(consola, {})
        lista_index = []
        ids_vistos: dict[str, str] = {}

        for plataforma in cfg["plataformas"]:
            ruta, origen = archivo_fuente(consola, plataforma)
            datos = leer_json(ruta)
            if not isinstance(datos, dict) or "platform" not in datos:
                raise ErrorClaro(f"{ruta} no parece un JSON de plataforma de Daijisho (le falta 'platform').")

            plat = datos["platform"]
            for campo in ("name", "uniqueId", "shortname"):
                if not plat.get(campo):
                    raise ErrorClaro(f"{ruta}: a 'platform' le falta el campo '{campo}'.")

            uid = plat["uniqueId"]
            if uid in ids_vistos:
                raise ErrorClaro(
                    f"La consola '{consola}' tiene dos plataformas con el mismo uniqueId '{uid}': "
                    f"{ids_vistos[uid]} y {plataforma}. Daijisho las mezclaria."
                )
            ids_vistos[uid] = plataforma

            huella = hash_contenido(datos)
            anterior = estado_consola.get(plataforma)
            oficial = revision_oficial(plataforma)

            if anterior and anterior.get("hash") == huella:
                revision = anterior["revision"]
            else:
                previa = anterior["revision"] if anterior else 0
                revision = max(previa + 1, oficial)
                que = "nueva" if not anterior else "cambio"
                novedades.append(f"{consola}/{plataforma} ({que}) -> revision {revision}")

            estado_consola[plataforma] = {"hash": huella, "revision": revision}

            salida = dict(datos)
            salida["revisionNumber"] = revision
            salidas[f"dist/{consola}/{plataforma}.json"] = salida

            lista_index.append({
                "filename": f"{plataforma}.json",
                "platformName": plat["name"],
                "platformShortname": plat["shortname"],
                "platformUniqueId": uid,
                "revisionNumber": revision,
            })
            del origen  # solo informativo

        salidas[f"dist/{consola}/index.json"] = {
            "baseUri": base_uri,
            "platformList": lista_index,
        }

    return salidas, lock_nuevo, novedades


def validar(salidas: dict, consolas: dict) -> None:
    """Chequeos finales. Si algo falla, no se escribe nada."""
    problemas: list[str] = []

    for ruta, datos in salidas.items():
        try:
            json.loads(json.dumps(datos, ensure_ascii=False))
        except (TypeError, ValueError) as e:
            problemas.append(f"{ruta}: no se puede serializar como JSON ({e})")

    for consola in consolas:
        clave_index = f"dist/{consola}/index.json"
        if clave_index not in salidas:
            problemas.append(f"Falta generar {clave_index}")
            continue
        index = salidas[clave_index]

        if not index["baseUri"].endswith(f"/dist/{consola}/"):
            problemas.append(f"{clave_index}: baseUri mal armado -> {index['baseUri']}")
        if not index["platformList"]:
            problemas.append(f"{clave_index}: quedo sin plataformas")

        for entrada in index["platformList"]:
            destino = f"dist/{consola}/{entrada['filename']}"
            if destino not in salidas:
                problemas.append(f"{clave_index}: apunta a {entrada['filename']} pero ese archivo no se genero")
                continue
            rev_archivo = salidas[destino].get("revisionNumber")
            if rev_archivo != entrada["revisionNumber"]:
                problemas.append(
                    f"{destino}: revision {rev_archivo} no coincide con la del index "
                    f"({entrada['revisionNumber']})"
                )

    if problemas:
        raise ErrorClaro("La validacion fallo, NO se genero nada:\n  - " + "\n  - ".join(problemas))


def escribir(salidas: dict, lock_nuevo: dict, consolas: dict) -> list[str]:
    """Escribe dist/ y el lock, y limpia lo que sobra."""
    borrados = []

    # Carpetas de consolas que ya no existen en consolas.yaml
    if DIST_DIR.exists():
        for carpeta in sorted(DIST_DIR.iterdir()):
            if carpeta.is_dir() and carpeta.name not in consolas:
                shutil.rmtree(carpeta)
                borrados.append(f"dist/{carpeta.name}/ (consola eliminada)")
            elif carpeta.is_file():
                carpeta.unlink()
                borrados.append(f"dist/{carpeta.name}")

    for ruta_rel, datos in salidas.items():
        escribir_json(DIST_DIR.parent / ruta_rel, datos)

    # Archivos sueltos dentro de cada consola que ya no se generan
    for consola in consolas:
        carpeta = DIST_DIR / consola
        for archivo in sorted(carpeta.glob("*")):
            if f"dist/{consola}/{archivo.name}" not in salidas:
                archivo.unlink()
                borrados.append(f"dist/{consola}/{archivo.name}")

    escribir_json(LOCK_FILE, lock_nuevo)
    return borrados


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera dist/ para Daijisho.")
    parser.add_argument("--repo", help="USUARIO/REPO de GitHub (si no, se saca del remote de git).")
    parser.add_argument("--branch", default="main", help="Rama del repo (por defecto: main).")
    args = parser.parse_args()

    consolas = cargar_consolas()
    usuario, repo = resolver_repo(args.repo)
    lock = leer_json(LOCK_FILE) if LOCK_FILE.exists() else {"consolas": {}}

    print(f"Repositorio: {usuario}/{repo} (rama {args.branch})")
    print(f"Consolas: {', '.join(consolas)}\n")

    salidas, lock_nuevo, novedades = construir(consolas, lock, usuario, repo, args.branch)
    validar(salidas, consolas)
    borrados = escribir(salidas, lock_nuevo, consolas)

    for consola, cfg in consolas.items():
        print(f"  {consola:16} {len(cfg['plataformas']):3} plataformas  ->  dist/{consola}/index.json")
    if novedades:
        print("\nRevisiones nuevas o actualizadas:")
        for n in novedades:
            print(f"  + {n}")
    else:
        print("\nSin cambios de revision (todo igual que la vez anterior).")
    if borrados:
        print("\nLimpieza:")
        for b in borrados:
            print(f"  - {b}")

    print("\nListo. Links para Daijisho:")
    for consola in consolas:
        print(f"  {consolas[consola]['nombre']}: {RAW}/{usuario}/{repo}/{args.branch}/dist/{consola}/index.json")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ErrorClaro as e:
        print(f"\n{e}\n", file=sys.stderr)
        sys.exit(1)
