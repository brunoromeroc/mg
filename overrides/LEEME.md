# overrides/

Carpeta para cambios propios de un modelo puntual de consola.

Si querés que **una sola consola** use una configuración distinta a la oficial
(por ejemplo, que la RG DS abra la Nintendo DS con otro emulador), copiás el
archivo desde `base/` a `overrides/<consola>/` y lo editás ahí.

Ejemplo:

    base/NintendoDS.json           ->  lo usan todas las consolas
    overrides/rg-ds/NintendoDS.json ->  solo lo usa rg-ds

El generador siempre prefiere el archivo de `overrides/` si existe.

`sync_official.py` **nunca** toca esta carpeta: tus cambios no se pisan.
