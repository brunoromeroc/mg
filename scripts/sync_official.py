"""Baja del repo oficial de Daijisho los JSON de las plataformas que usan tus consolas.

Uso:
    py scripts/sync_official.py

Deja los archivos en base/. No toca overrides/ ni dist/.
"""

from __future__ import annotations

import argparse
import difflib
import sys
import urllib.error
import urllib.request

from common import BASE_DIR, ErrorClaro, cargar_consolas, plataformas_usadas

INDEX_OFICIAL = "https://raw.githubusercontent.com/TapiocaFox/Daijishou/main/platforms/index.json"


def bajar(url: str) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": "marketgamer-daijisho"})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise ErrorClaro(f"No pude descargar {url} (error {e.code}).") from e
    except urllib.error.URLError as e:
        raise ErrorClaro(f"No pude descargar {url}: {e.reason}\n¿Tenes internet?") from e


def carpeta_del_index(url_index: str) -> str:
    return url_index.rsplit("/", 1)[0] + "/"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza base/ con el repo oficial de Daijisho.")
    parser.add_argument("--index-url", default=INDEX_OFICIAL, help="URL del index.json oficial.")
    args = parser.parse_args()

    consolas = cargar_consolas()
    usadas = plataformas_usadas(consolas)
    print(f"Consolas en consolas.yaml: {len(consolas)}")
    print(f"Plataformas distintas usadas: {len(usadas)}")

    print(f"\nBajando el indice oficial...\n  {args.index_url}")
    import json

    indice = json.loads(bajar(args.index_url))
    entradas = {e["filename"].removesuffix(".json"): e for e in indice["platformList"]}
    print(f"El indice oficial tiene {len(entradas)} plataformas.")

    # --- Validar que todos los nombres de consolas.yaml existan ---------------
    faltantes = sorted(usadas - set(entradas))
    if faltantes:
        lineas = [
            "",
            "ERROR: estos nombres de consolas.yaml no existen en el indice oficial de Daijisho:",
            "",
        ]
        for f in faltantes:
            parecidos = difflib.get_close_matches(f, entradas, n=3, cutoff=0.6)
            sugerencia = f"   ¿Quisiste decir: {', '.join(parecidos)}?" if parecidos else ""
            lineas.append(f"  - {f}{sugerencia}")
        lineas += [
            "",
            "Los nombres van EXACTO como el archivo oficial, sin el '.json' y respetando",
            "mayusculas y minusculas. Lista completa:",
            "  https://github.com/TapiocaFox/Daijishou/tree/main/platforms",
        ]
        raise ErrorClaro("\n".join(lineas))

    # --- Descargar ------------------------------------------------------------
    carpeta = carpeta_del_index(args.index_url)
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    nuevos, actualizados, iguales = [], [], []
    for nombre in sorted(usadas):
        destino = BASE_DIR / f"{nombre}.json"
        contenido = bajar(carpeta + f"{nombre}.json")
        try:
            json.loads(contenido)  # se valida antes de guardar
        except json.JSONDecodeError as e:
            raise ErrorClaro(f"Lo que baje para {nombre} no es un JSON valido: {e}") from e

        anterior = destino.read_bytes() if destino.exists() else None
        if anterior is None:
            nuevos.append(nombre)
        elif anterior != contenido:
            actualizados.append(nombre)
        else:
            iguales.append(nombre)
            continue
        destino.write_bytes(contenido)
        rev = entradas[nombre]["revisionNumber"]
        print(f"  {'NUEVO  ' if anterior is None else 'ACTUALIZ'} {nombre} (revision oficial {rev})")

    # --- Limpiar plataformas que ya no usa ninguna consola ---------------------
    borrados = []
    for archivo in sorted(BASE_DIR.glob("*.json")):
        if archivo.stem not in usadas:
            archivo.unlink()
            borrados.append(archivo.stem)
            print(f"  BORRADO  {archivo.stem} (ya no lo usa ninguna consola)")

    print("\nResumen del sync:")
    print(f"  nuevos:       {len(nuevos)}")
    print(f"  actualizados: {len(actualizados)}")
    print(f"  sin cambios:  {len(iguales)}")
    print(f"  borrados:     {len(borrados)}")
    if nuevos or actualizados:
        print("  cambiaron: " + ", ".join(sorted(nuevos + actualizados)))
    print("\nListo. Ahora corre: py scripts/build.py")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ErrorClaro as e:
        print(f"\n{e}\n", file=sys.stderr)
        sys.exit(1)
