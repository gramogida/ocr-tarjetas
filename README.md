# OCR de Tarjetas

Saca una foto de una tarjeta personal, recorta la tarjeta, le hace OCR y devuelve el
texto plano mas los campos separados (nombre, cargo, empresa, email, telefonos, web,
direccion, CUIT). Exporta a `.txt`, `.csv` y contacto `.vcf`.

## Uso en la PC

1. Doble clic en `iniciar.bat` (abre solo el navegador en `http://localhost:8765`).
2. **Encender camara** -> encuadrar la tarjeta -> **Capturar**.
3. La app detecta sola el borde de la tarjeta y lee. Si el recuadro azul quedo mal,
   corregilo con el mouse (arrastrar adentro lo mueve, arrastrar una esquina lo
   redimensiona, arrastrar afuera dibuja uno nuevo) y toca **Leer seleccion**.
4. Los datos salen en el panel 3 y el texto crudo, editable, en el panel 4.
   Si corregis el texto a mano, **Re-analizar** vuelve a llenar los campos.

También podés usar una foto ya tomada con el selector de archivo.

## El recorte es lo que más importa

Medido con la misma foto (tarjeta en la mano, galpon de fondo, reflejo):

| | Teléfonos | Email |
|---|---|---|
| Tesseract sobre la foto entera | `+54 41...`, `+54 14...` mal | mal |
| Tesseract sobre el recorte | correctos | mal |
| Windows OCR sobre la foto entera | correctos | casi |
| Windows OCR sobre el recorte | correctos | perfecto |

Por eso la app recorta primero y recién después lee.

## Motores de OCR

La app elige el mejor disponible y podés cambiarlo en el desplegable del panel 4:

1. **Windows OCR (nativo)** — el mismo motor de la Herramienta de Recortes. Es el mejor
   con diferencia y no descarga nada. Solo en Windows y solo si la app corre con
   `server.py` (el navegador le manda el recorte al servidor local, que lo procesa con
   `ocr_win.ps1`). Idioma detectado en esta PC: es-MX.
2. **OCR del sistema (Android)** — la API `TextDetector` del navegador, respaldada por
   ML Kit. Aparece sola cuando la app corre en Chrome de Android.
3. **Tesseract.js (universal)** — respaldo que funciona en cualquier lado. Descarga
   ~15 MB la primera vez y después queda cacheado.

## Para usarla en Android

La app es una PWA: `index.html` + `manifest.webmanifest` + `sw.js` + iconos son todo lo
que necesita, sin servidor. Dos caminos:

- **Subir la carpeta a cualquier hosting estatico con HTTPS** (GitHub Pages, Netlify,
  Cloudflare Pages). Abrís la URL en el celular y "Agregar a pantalla de inicio".
  Funciona offline después de la primera carga.
- **Servirla desde esta PC** para probar en la red local. Ojo: la camara exige HTTPS o
  localhost, así que por `http://192.168.x.x` Chrome la va a bloquear. Para probar rápido
  conviene un túnel HTTPS o directamente el hosting estático.

En Android el motor `win` no aparece (es exclusivo de Windows) y se usa `TextDetector`,
que da una calidad parecida.

## Archivos

| | |
|---|---|
| `index.html` | toda la app: camara, recorte, OCR, parseo, exportacion |
| `server.py` | servidor local + puente al OCR nativo (`/api/ocr`, `/api/engines`) |
| `ocr_win.ps1` | OCR con `Windows.Media.Ocr` |
| `iniciar.bat` | lanza `server.py` |
| `manifest.webmanifest`, `sw.js`, `icon-*.png` | lo que la hace instalable en Android |

## Notas

- Todo es local: la imagen nunca sale de la maquina. El servidor escucha solo en
  `127.0.0.1`.
- La `@` es lo que mas confunde al OCR (la lee como `Q` u `O`) y suele partir los
  dominios con espacios; la app repara ambas cosas cuando el final es un dominio
  conocido (`.com`, `.com.ar`, etc.).
- Si una tarjeta de fondo oscuro sale mal, probá **Forzar blanco y negro** (umbral
  adaptativo, aguanta luz despareja) y volvé a leer.
- El logo suele salir mal leído: es texto estilizado sobre formas. Los datos de
  contacto, que es lo que importa, salen bien.
