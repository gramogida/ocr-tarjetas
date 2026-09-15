#!/usr/bin/env python3
"""
Servidor local de la app OCR de Tarjetas.

- Sirve los archivos estaticos (index.html, sw.js, manifest).
- Expone /api/engines  -> que motores hay disponibles en esta maquina.
- Expone /api/ocr      -> POST con un PNG; corre el OCR nativo de Windows y
                          devuelve el texto. Solo funciona en Windows; en otras
                          plataformas la app usa los motores del navegador.

Escucha unicamente en 127.0.0.1 (no queda expuesto en la red).
"""
import http.server
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import webbrowser

RAIZ = os.path.dirname(os.path.abspath(__file__))
PS1 = os.path.join(RAIZ, 'ocr_win.ps1')
PUERTO = int(os.environ.get('PUERTO', '8765'))
MAX_BYTES = 25 * 1024 * 1024

_win_ocr = None  # cache de disponibilidad


def powershell(args, timeout=90):
    return subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass'] + args,
        capture_output=True, timeout=timeout,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )


def hay_ocr_windows():
    """True si Windows.Media.Ocr tiene al menos un idioma instalado."""
    global _win_ocr
    if _win_ocr is not None:
        return _win_ocr
    _win_ocr = False
    if sys.platform == 'win32' and os.path.exists(PS1):
        try:
            cmd = ('[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]'
                   '::AvailableRecognizerLanguages.Count')
            r = powershell(['-Command', cmd], timeout=40)
            _win_ocr = r.returncode == 0 and int(r.stdout.decode('ascii', 'ignore').strip() or 0) > 0
        except Exception:
            _win_ocr = False
    return _win_ocr


def ocr_windows(png_bytes):
    """Corre el OCR nativo sobre los bytes PNG recibidos. Devuelve dict."""
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    try:
        tmp.write(png_bytes)
        tmp.close()
        r = powershell(['-File', PS1, '-Path', tmp.name])
        salida = r.stdout.decode('utf-8', 'replace').strip()
        if not salida:
            return {'ok': False, 'error': r.stderr.decode('utf-8', 'replace')[:400] or 'sin salida'}
        try:
            return json.loads(salida)
        except json.JSONDecodeError:
            return {'ok': False, 'error': 'respuesta ilegible: ' + salida[:300]}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'el OCR nativo tardo demasiado'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=RAIZ, **kw)

    def log_message(self, fmt, *args):
        if '/api/' in (self.path or ''):
            sys.stderr.write('  %s %s\n' % (self.command, self.path))

    def _json(self, obj, code=200):
        cuerpo = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path.startswith('/api/engines'):
            return self._json({'windows': hay_ocr_windows()})
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith('/api/ocr'):
            return self._json({'ok': False, 'error': 'ruta desconocida'}, 404)
        if not hay_ocr_windows():
            return self._json({'ok': False, 'error': 'OCR nativo no disponible en esta maquina'}, 501)
        try:
            n = int(self.headers.get('Content-Length', 0))
        except ValueError:
            n = 0
        if n <= 0 or n > MAX_BYTES:
            return self._json({'ok': False, 'error': 'imagen vacia o demasiado grande'}, 400)
        datos = self.rfile.read(n)
        res = ocr_windows(datos)
        return self._json(res, 200 if res.get('ok') else 500)


class Servidor(socketserver.ThreadingTCPServer):
    # En Windows SO_REUSEADDR deja que dos procesos compartan el puerto y las
    # peticiones caen en cualquiera de los dos; asi el aviso de "puerto ocupado"
    # nunca saltaria. En el resto evita el TIME_WAIT al reiniciar.
    allow_reuse_address = (sys.platform != 'win32')
    daemon_threads = True


def main():
    url = 'http://localhost:%d/index.html' % PUERTO
    try:
        srv = Servidor(('127.0.0.1', PUERTO), Handler)
    except OSError as e:
        print('No se pudo abrir el puerto %d: %s' % (PUERTO, e))
        print('Quizas ya hay otra copia del servidor corriendo. Proba abrir %s' % url)
        input('Enter para salir...')
        return
    nativo = 'SI' if hay_ocr_windows() else 'no (se usaran los motores del navegador)'
    print('')
    print('  OCR de Tarjetas')
    print('  ---------------')
    print('  Direccion .......: %s' % url)
    print('  OCR nativo Windows: %s' % nativo)
    print('  Deja esta ventana abierta mientras usas la app. Ctrl+C para cerrar.')
    print('')
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n  Servidor detenido.')
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
