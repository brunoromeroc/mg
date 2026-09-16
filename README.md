# marketgamer-daijisho

Configuraciones de plataformas de **Daijisho** para las consolas que vendo en
**Market Gamer**.

Cada modelo de consola tiene su propio link fijo. Se pega una sola vez en
Daijisho y la consola se actualiza sola cuando yo publico cambios acá.

---

## Links para pegar en Daijisho

| Consola | Link |
|---|---|
| Anbernic RG DS | `https://raw.githubusercontent.com/brunoromeroc/marketgamer-daijisho/main/dist/rg-ds/index.json` |

### Cómo se pega en la consola

1. Abrir **Daijisho** → menú (tres rayas) → **Settings**.
2. Entrar en **Library** → **Import platforms from index**  *(en algunas
   versiones aparece como "Sync platforms" o "Index URL")*.
3. Pegar el link de la tabla y confirmar.
4. Elegir las plataformas a importar → **Import**.

Para actualizar más adelante: se repite el mismo paso con el mismo link.
Daijisho compara los números de revisión y ofrece sólo lo que cambió.

---

## Qué hay en cada carpeta

| Carpeta / archivo | Para qué sirve | ¿Lo edito? |
|---|---|---|
| `consolas.yaml` | La lista de consolas y qué plataformas lleva cada una | **SÍ** |
| `overrides/<consola>/` | Cambios propios de un modelo puntual | Sí, si hace falta |
| `base/` | Copia de los JSON oficiales de Daijisho | No, se baja solo |
| `dist/<consola>/` | Lo que realmente leen las consolas | **No**, se genera solo |
| `revisions.lock.json` | Memoria de los números de versión | **No, nunca** |
| `scripts/` | Los dos programas que hacen el trabajo | No |

---

## Cómo agrego un modelo nuevo de consola

Todo desde la web de GitHub, sin instalar nada:

1. Entrar al repo y hacer clic en el archivo **`consolas.yaml`**.
2. Clic en el **lápiz** (Edit this file), arriba a la derecha.
3. Ir al final del archivo y agregar un bloque nuevo, copiando el formato del
   que ya está. Por ejemplo:

   ```yaml
   rg-35xx:
     nombre: Anbernic RG 35XX
     plataformas:
       - NintendoGameBoyAdvance
       - SonyPlayStation
       - SuperNintendoEntertainmentSystem
   ```

   Tres cosas a respetar:
   - La primera línea (`rg-35xx:`) es el nombre corto: **minúsculas, sin
     espacios ni acentos**. Ese texto es el que va a aparecer en el link.
   - La **sangría** (los espacios del principio de cada línea) tiene que quedar
     igual que en el bloque de arriba.
   - Cada plataforma se escribe **exactamente** como el archivo oficial, sin el
     `.json`. La lista completa está en:
     <https://github.com/TapiocaFox/Daijishou/tree/main/platforms>

4. Botón verde **Commit changes** → **Commit changes**.
5. Esperar ~1 minuto. En la pestaña **Actions** se ve el proceso; cuando queda
   con un tilde verde, ya está.
6. El link nuevo es:
   `https://raw.githubusercontent.com/brunoromeroc/marketgamer-daijisho/main/dist/rg-35xx/index.json`
   (cambiando `rg-35xx` por el nombre corto que pusiste).

> Si el nombre de una plataforma está mal escrito, el proceso falla a propósito
> y **no publica nada roto**. En la pestaña Actions aparece en rojo, y el mensaje
> de error dice qué nombre está mal e incluso sugiere el correcto.

---

## Cómo hago un cambio sólo para un modelo

Sirve para, por ejemplo, cambiar el emulador que usa una consola puntual sin
tocar a las demás.

1. En el repo, entrar a la carpeta **`base/`** y abrir el archivo de la
   plataforma que querés cambiar (ej.: `NintendoDS.json`).
2. Clic en **Copy raw contents** (el ícono de copiar, arriba a la derecha).
3. Volver a la raíz del repo → **Add file** → **Create new file**.
4. En el nombre escribir la ruta completa, con barras:
   `overrides/rg-ds/NintendoDS.json`
   *(al escribir cada `/` GitHub va creando las carpetas solo)*
5. Pegar el contenido copiado y hacer los cambios que quieras.
6. **Commit changes**.

Desde ese momento, **rg-ds** usa tu versión y el resto sigue con la oficial.
El número de revisión sube solo, así que las consolas ya vendidas detectan la
actualización.

Para volver atrás: borrás el archivo de `overrides/` y listo.

---

## Automatizaciones

| Cuándo | Qué hace |
|---|---|
| Cada vez que edito `consolas.yaml`, `base/` u `overrides/` | Regenera `dist/` y lo publica |
| Todos los lunes 9:00 (hora Argentina) | Revisa si Daijisho actualizó algo oficial y, si sí, lo trae y republica |

La sincronización semanal también se puede disparar a mano:
pestaña **Actions** → *Sincronizar con Daijisho oficial* → **Run workflow**.

---

## Sobre los números de revisión

Daijisho detecta que hay una actualización cuando el `revisionNumber` de una
plataforma es **más alto** que el que la consola tiene guardado.

El generador se encarga solo:

- Si el contenido no cambió → se mantiene el número de antes (la consola no
  molesta al usuario con una actualización vacía).
- Si cambió → el número sube. Nunca baja, ni siquiera si vuelvo atrás un cambio.

Ese historial vive en `revisions.lock.json`. **No hay que editarlo nunca**: si
se borra o se toca a mano, los números pueden quedar más bajos que los que ya
tienen las consolas en la calle y esas consolas dejarían de ver las
actualizaciones.

---

## Para correrlo en la computadora (opcional)

Normalmente no hace falta: GitHub lo hace solo. Pero si querés probar local:

```bash
pip install pyyaml
python scripts/sync_official.py   # baja los JSON oficiales a base/
python scripts/build.py           # genera dist/
```

---

## Qué NO va en este repositorio

Sólo configuraciones (`.json`, `.yaml`) y scripts.
**Nada de ROMs, BIOS ni APKs.**

Los archivos de `base/` son de
[Daijishou](https://github.com/TapiocaFox/Daijishou) (de TapiocaFox), traídos
tal cual del repositorio oficial.
