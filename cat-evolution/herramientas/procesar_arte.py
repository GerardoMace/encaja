"""Procesa las imágenes de Gemini para Cat Evolution.

Lee las imágenes de la carpeta de Drive (fondo blanco liso), quita el fondo,
borra la marca de agua y manchas sueltas, recorta, ajusta el tamaño y escribe
arte/manifest.json, que el juego lee al arrancar.

Uso:  python procesar_arte.py [carpeta_origen] [carpeta_destino]
Por defecto: origen G:/Mi unidad/videogame/arte, destino CatEvolution/arte
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

AQUI = Path(__file__).resolve().parent
DESTINO = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI.parent / 'arte'
ORIGEN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('G:/Mi unidad/videogame/arte')

# nombre: (tipo, tamaño máximo en px)
#   recorte = quitar fondo blanco y recortar al objeto
#   cuadro  = quitar fondo y ajustar a un cuadro (piezas y bloques)
#   fondo   = escenario completo, recortado a la proporción 400:560
#   icono   = imagen completa cuadrada, sin quitar fondo
ASSETS = {
    # escenarios: 3 hábitats × 3 horas del día
    **{f'fondo_{h}_{m}': ('fondo', 1120) for h in ('egipto', 'casa', 'nieve') for m in ('dia', 'atardecer', 'noche')},
    # Egipto
    'esfinge': ('recorte', 640), 'esfinge_piedra': ('recorte', 640),
    'sarcofago': ('recorte', 384), 'altar': ('recorte', 384), 'estanque': ('recorte', 512),
    'obelisco': ('recorte', 512), 'estandarte': ('recorte', 256),
    # Casa
    'arbol_gato': ('recorte', 640), 'canasta': ('recorte', 384), 'plato': ('recorte', 384),
    # Nieve
    'muneco_nieve': ('recorte', 640), 'iglu': ('recorte', 384), 'fogata': ('recorte', 384),
    # Abuelo Colmillo (el de ojos brillantes se recorta con el mismo encuadre que el normal)
    'abuelo': ('recorte', 512), 'abuelo_brillo': ('par', 512),
    # piezas de Ofrendas
    'pescado': ('cuadro', 192), 'esqueleto': ('cuadro', 192), 'raton': ('cuadro', 192),
    'pollo': ('cuadro', 192), 'estambre': ('cuadro', 192), 'hierba_gatera': ('cuadro', 192),
    # bloques de Pirámide
    'bloque_caliza': ('cuadro', 160), 'bloque_granito': ('cuadro', 160), 'bloque_lapislazuli': ('cuadro', 160),
    'bloque_turquesa': ('cuadro', 160), 'bloque_oro': ('cuadro', 160), 'bloque_basalto': ('cuadro', 160),
    # íconos
    'icono_ofrenda': ('cuadro', 96), 'icono_piedra': ('cuadro', 96), 'icono_app': ('icono', 512),
    # gato base
    'gato_frente': ('recorte', 512), 'gato_lado_1': ('recorte', 512), 'gato_lado_2': ('recorte', 512),
}
CLAVE = (255, 0, 255)


def quitar_fondo(img):
    """Fondo blanco conectado a las orillas → transparente. Devuelve RGBA."""
    rgb = img.convert('RGB')
    w, h = rgb.size
    marcado = rgb.copy()
    paso = max(8, min(w, h) // 64)
    semillas = [(x, 0) for x in range(0, w, paso)] + [(x, h - 1) for x in range(0, w, paso)] + \
               [(0, y) for y in range(0, h, paso)] + [(w - 1, y) for y in range(0, h, paso)]
    for s in semillas:
        r, g, b = marcado.getpixel(s)
        if min(r, g, b) >= 200 and max(r, g, b) - min(r, g, b) < 30:
            # thresh suma la diferencia de los 3 canales: 100 ≈ 33 por canal, se lleva sombras muy claras
            ImageDraw.floodfill(marcado, s, CLAVE, thresh=100)
    a = np.array(marcado)
    fondo = (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)
    original = np.array(rgb).astype(np.int32)
    alfa = np.where(fondo, 0, 255).astype(np.uint8)
    # orilla suave: píxeles claros pegados al fondo quedan semitransparentes
    borde = ndimage.binary_dilation(fondo, iterations=2) & ~fondo
    brillo = original.mean(axis=2)
    suave = np.clip((255 - brillo) / 55 * 255, 0, 255).astype(np.uint8)
    alfa = np.where(borde, np.minimum(alfa, suave), alfa)
    # quedarse con el objeto principal: borra la marca de agua y manchas sueltas
    solido = alfa > 0
    etiquetas, n = ndimage.label(solido)
    if n > 1:
        tam = ndimage.sum(solido, etiquetas, range(1, n + 1))
        mayor = tam.max()
        conservar = [i + 1 for i, t in enumerate(tam) if t >= mayor * 0.04]
        alfa = np.where(np.isin(etiquetas, conservar), alfa, 0).astype(np.uint8)
    rgba = np.dstack([np.array(rgb), alfa])
    return Image.fromarray(rgba, 'RGBA')


def recortar(rgba, margen=0.02):
    caja = rgba.getbbox()
    if not caja:
        return rgba
    x0, y0, x1, y1 = caja
    m = int(max(x1 - x0, y1 - y0) * margen)
    return rgba.crop((max(0, x0 - m), max(0, y0 - m), min(rgba.width, x1 + m), min(rgba.height, y1 + m)))


def ajustar(img, maximo):
    escala = min(1.0, maximo / max(img.size))
    if escala < 1:
        img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)
    return img


def a_cuadro(rgba, lado):
    rgba = ajustar(rgba, lado)
    lienzo = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
    lienzo.paste(rgba, ((lado - rgba.width) // 2, (lado - rgba.height) // 2), rgba)
    return lienzo


def a_fondo(img, alto):
    rgb = img.convert('RGB')
    objetivo = 400 / 560
    w, h = rgb.size
    if w / h > objetivo:          # sobra ancho: recorta los lados
        nw = round(h * objetivo)
        rgb = rgb.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:                         # sobra alto: recorta arriba (el cielo) y deja el piso completo
        nh = round(w / objetivo)
        rgb = rgb.crop((0, h - nh, w, h))
    return rgb.resize((round(alto * objetivo), alto), Image.LANCZOS)


def buscar(nombre):
    for ext in ('.png', '.PNG', '.jpg', '.jpeg', '.JPG', '.JPEG', '.webp'):
        p = ORIGEN / (nombre + ext)
        if p.exists():
            return p
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    DESTINO.mkdir(parents=True, exist_ok=True)
    manifiesto = {'v': 1, 'assets': {}}
    hechos, faltan = [], []
    for nombre, (tipo, tam) in ASSETS.items():
        origen = buscar(nombre)
        if not origen:
            faltan.append(nombre)
            continue
        img = Image.open(origen)
        if tipo == 'fondo':
            salida = a_fondo(img, tam)
            archivo = nombre + '.jpg'
            salida.save(DESTINO / archivo, quality=86, optimize=True)
        elif tipo == 'icono':
            salida = img.convert('RGB').resize((tam, tam), Image.LANCZOS)
            archivo = nombre + '.png'
            salida.save(DESTINO / archivo, optimize=True)
        elif tipo == 'par':
            # mismo recorte que su pareja (abuelo_brillo usa el encuadre de abuelo)
            base = buscar(nombre.replace('_brillo', ''))
            rgba = quitar_fondo(img)
            if base and Image.open(base).size == img.size:
                caja = quitar_fondo(Image.open(base)).getbbox()
                x0, y0, x1, y1 = caja
                m = int(max(x1 - x0, y1 - y0) * 0.02)
                rgba = rgba.crop((max(0, x0 - m), max(0, y0 - m), min(img.width, x1 + m), min(img.height, y1 + m)))
            else:
                rgba = recortar(rgba)
            salida = ajustar(rgba, tam)
            archivo = nombre + '.png'
            salida.save(DESTINO / archivo, optimize=True)
        else:
            rgba = recortar(quitar_fondo(img))
            salida = a_cuadro(rgba, tam) if tipo == 'cuadro' else ajustar(rgba, tam)
            archivo = nombre + '.png'
            salida.save(DESTINO / archivo, optimize=True)
        manifiesto['assets'][nombre] = {'file': archivo, 'w': salida.width, 'h': salida.height}
        hechos.append(f'{nombre} ({salida.width}×{salida.height})')
    # quita del destino lo que ya no está en el manifiesto
    validos = {a['file'] for a in manifiesto['assets'].values()} | {'manifest.json'}
    for p in DESTINO.iterdir():
        if p.name not in validos:
            p.unlink()
    (DESTINO / 'manifest.json').write_text(json.dumps(manifiesto, indent=1), encoding='utf-8')
    print(f'Procesadas {len(hechos)} de {len(ASSETS)}:')
    for h in hechos:
        print('  ✓', h)
    if faltan:
        print(f'Faltan {len(faltan)}:', ', '.join(faltan))


if __name__ == '__main__':
    main()
