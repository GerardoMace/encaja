"""Procesa las imágenes de Gemini para Cat Evolution.

Lee las imágenes de la carpeta de Drive (fondo blanco liso), quita el fondo,
borra la marca de agua y manchas sueltas, recorta, ajusta el tamaño y escribe
arte/manifest.json, que el juego lee al arrancar.

Uso:  python procesar_arte.py [carpeta_origen] [carpeta_destino]
      python procesar_arte.py --hoja imagen.png prefijo [carpeta_destino]   (solo cortar una hoja, sin nombres)
Por defecto: origen G:/Mi unidad/videogame/arte, destino CatEvolution/arte

Las imágenes pueden venir sueltas (esfinge.png) o en hojas (hoja_egipto.png): cada hoja
trae varios objetos en un orden fijo (ver HOJAS) y el programa los separa y los nombra.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

AQUI = Path(__file__).resolve().parent
_args = [] if '--hoja' in sys.argv else sys.argv[1:]
DESTINO = Path(_args[1]) if len(_args) > 1 else AQUI.parent / 'arte'
ORIGEN = Path(_args[0]) if _args else Path('G:/Mi unidad/videogame/arte')

# Hojas de Gemini: objetos de arriba a abajo y de izquierda a derecha, en este orden
HOJAS = {
    'hoja_gatos': ['gato_frente', 'gato_lado_1', 'gato_estira', 'gato_acostado', 'gato_sentado_lado', 'gato_agazapado'],
    'hoja_gatos_2': ['gato_lado_2', 'gato_colgado', 'gato_dormido'],
    'hoja_ofrendas': ['pescado', 'esqueleto', 'raton', 'pollo', 'estambre', 'hierba_gatera'],
    'hoja_piramide': ['bloque_caliza', 'bloque_granito', 'bloque_lapislazuli', 'bloque_turquesa', 'bloque_oro', 'bloque_basalto', 'icono_piedra'],
    'hoja_egipto': ['esfinge', 'esfinge_piedra', 'sarcofago', 'altar', 'obelisco', 'estandarte', 'estanque', 'icono_ofrenda'],
    'hoja_casa_nieve': ['arbol_gato', 'canasta', 'plato', 'muneco_nieve', 'iglu', 'fogata'],
    # hojas de animación: cuadros en orden
    'hoja_caminar': ['gato_caminar_1', 'gato_caminar_2', 'gato_caminar_3', 'gato_caminar_4'],
    'hoja_accesorios': ['acc_cascabel', 'acc_mono', 'acc_usekh', 'acc_luna', 'acc_bufanda', 'acc_nemes'],
    'hoja_acicalar': ['gato_acicalar_1', 'gato_acicalar_2', 'gato_acicalar_3', 'gato_acicalar_4'],
    'hoja_saltar': ['gato_saltar_1', 'gato_saltar_2', 'gato_saltar_3', 'gato_saltar_4'],
    'hoja_comer': ['gato_comer_1', 'gato_comer_2', 'gato_comer_3'],
    'hoja_jugar': ['gato_jugar_1', 'gato_jugar_2', 'gato_jugar_3', 'gato_jugar_4'],
}
# en la hoja caminan hacia la izquierda; el juego los usa mirando a la derecha
ESPEJO = {'gato_lado_1', 'gato_lado_2'}
# cuadros de animación que deben quedar del mismo tamaño, alineados abajo y a la derecha (la nariz),
# para que al pasarlos rápido la cabeza no tiemble
ANIMACIONES = {'gato_caminar_': 4}

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
    'gato_colgado': ('recorte', 512), 'gato_estira': ('recorte', 512), 'gato_acostado': ('recorte', 512),
    'gato_sentado_lado': ('recorte', 512), 'gato_agazapado': ('recorte', 512), 'gato_dormido': ('recorte', 512),
    # cuadros de animación
    **{f'gato_caminar_{i}': ('recorte', 512) for i in range(1, 5)},
    # accesorios sueltos que el juego pone sobre el gato
    'acc_cascabel': ('recorte', 256),
    'acc_mono': ('recorte', 256),
    'acc_usekh': ('recorte', 256),
    'acc_luna': ('recorte', 256),
    'acc_bufanda': ('recorte', 256),
    'acc_nemes': ('recorte', 256),
    **{f'gato_acicalar_{i}': ('recorte', 512) for i in range(1, 5)},
    **{f'gato_saltar_{i}': ('recorte', 512) for i in range(1, 5)},
    **{f'gato_comer_{i}': ('recorte', 512) for i in range(1, 4)},
    **{f'gato_jugar_{i}': ('recorte', 512) for i in range(1, 5)},
}
CLAVE = (255, 0, 255)


def quitar_fondo(img, solo_principal=True):
    """Fondo blanco conectado a las orillas → transparente. Devuelve RGBA.
    solo_principal: borra la marca de agua y manchas sueltas (no se usa al cortar hojas)."""
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
    # orilla sin halo: en la franja pegada al fondo, lo claro se vuelve transparente (el contorno
    # del dibujo es oscuro) y lo semitransparente toma el color del contorno
    borde = ndimage.binary_dilation(fondo, iterations=4) & ~fondo
    brillo = original.mean(axis=2)
    suave = np.clip((200 - brillo) / 120 * 255, 0, 255).astype(np.uint8)
    alfa = np.where(borde, np.minimum(alfa, suave), alfa)
    tinta = borde & (alfa < 255)
    original[tinta] = (45, 30, 56)
    rgb = Image.fromarray(original.astype(np.uint8), 'RGB')
    # quedarse con el objeto principal: borra la marca de agua y manchas sueltas
    solido = alfa > 0
    etiquetas, n = ndimage.label(solido)
    if n > 1 and solo_principal:
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
    hechos, faltan, avisos = [], [], []
    piezas = {}
    for hoja, nombres in HOJAS.items():
        archivo = buscar(hoja)
        if not archivo:
            continue
        sueltas = piezas_de_hoja(Image.open(archivo))
        if len(sueltas) != len(nombres):
            cortar_hoja(archivo, hoja, ORIGEN / 'recortes')
            avisos.append(f'{hoja}: se esperaban {len(nombres)} objetos y salieron {len(sueltas)}. '
                          f'No les puse nombre; quedaron numerados en recortes/ para revisarlos.')
            continue
        for nombre, pieza in zip(nombres, sueltas):
            piezas[nombre] = pieza.transpose(Image.FLIP_LEFT_RIGHT) if nombre in ESPEJO else pieza
    for nombre in [k for k in piezas if k.startswith('acc_')]:
        piezas[nombre] = quitar_huecos(piezas[nombre])
    for prefijo, n in ANIMACIONES.items():
        cuadros = [piezas.get(f'{prefijo}{i}') for i in range(1, n + 1)]
        if all(cuadros):
            ancho, alto = max(c.width for c in cuadros), max(c.height for c in cuadros)
            for i, c in enumerate(cuadros, start=1):
                lienzo = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
                lienzo.paste(c, (ancho - c.width, alto - c.height), c)
                piezas[f'{prefijo}{i}'] = lienzo
    for nombre, (tipo, tam) in ASSETS.items():
        if nombre in piezas and tipo in ('recorte', 'cuadro', 'par'):
            pieza = piezas[nombre]
            salida = a_cuadro(pieza, tam) if tipo == 'cuadro' else ajustar(pieza, tam)
            archivo = nombre + '.png'
            salida.save(DESTINO / archivo, optimize=True)
            manifiesto['assets'][nombre] = {'file': archivo, 'w': salida.width, 'h': salida.height}
            hechos.append(f'{nombre} ({salida.width}×{salida.height}, de una hoja)')
            continue
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
    for a in avisos:
        print('  ⚠', a)


def quitar_huecos(pieza):
    """Vuelve transparentes las zonas blancas encerradas que sean grandes (no los brillos chicos)."""
    d = np.array(pieza)
    claro = (d[..., :3].min(axis=2) > 225) & (d[..., 3] > 0)
    etiquetas, n = ndimage.label(claro)
    for i in range(1, n + 1):
        zona = etiquetas == i
        if zona.sum() > d.shape[0] * d.shape[1] * 0.02:
            d[..., 3][ndimage.binary_dilation(zona, iterations=1) & (d[..., :3].min(axis=2) > 200)] = 0
    return Image.fromarray(d, 'RGBA')


def piezas_de_hoja(img):
    """Separa una hoja en objetos (RGBA recortados), de arriba a abajo y de izquierda a derecha."""
    rgba = quitar_fondo(img, solo_principal=False)
    datos = np.array(rgba)
    solido = datos[..., 3] > 0
    # junta los pedacitos cercanos (bigotes, colas sueltas) con su objeto
    unido = ndimage.binary_dilation(solido, iterations=max(6, img.width // 180))
    etiquetas, n = ndimage.label(unido)
    piezas = []
    for i, (ys, xs) in enumerate(ndimage.find_objects(etiquetas), start=1):
        if (solido & (etiquetas == i)).sum() < solido.sum() * 0.01:
            continue
        piezas.append({'i': i, 'ys': ys, 'xs': xs, 'cy': (ys.start + ys.stop) / 2, 'cx': (xs.start + xs.stop) / 2})
    # filas: objetos cuyo centro está cerca en altura
    filas = []
    for p in sorted(piezas, key=lambda q: q['cy']):
        if filas and p['cy'] - filas[-1][0]['cy'] < img.height * 0.15:
            filas[-1].append(p)
        else:
            filas.append([p])
    orden = [p for fila in filas for p in sorted(fila, key=lambda q: q['cx'])]
    salida = []
    for p in orden:
        recorte = datos[p['ys'], p['xs']].copy()
        recorte[..., 3] = np.where(etiquetas[p['ys'], p['xs']] == p['i'], recorte[..., 3], 0)
        salida.append(recortar(Image.fromarray(recorte, 'RGBA')))
    return salida


def cortar_hoja(archivo, prefijo, destino):
    """Guarda cada objeto de una hoja como prefijo_1.png, prefijo_2.png…"""
    destino.mkdir(parents=True, exist_ok=True)
    salida = []
    for k, pieza in enumerate(piezas_de_hoja(Image.open(archivo)), start=1):
        nombre = f'{prefijo}_{k}.png'
        ajustar(pieza, 640).save(destino / nombre, optimize=True)
        salida.append(f'{nombre} ({pieza.width}×{pieza.height})')
    return salida


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--hoja':
        # python procesar_arte.py --hoja imagen.png prefijo [carpeta_destino]
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
        dest = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(sys.argv[2]).parent / 'recortes'
        for linea in cortar_hoja(Path(sys.argv[2]), sys.argv[3], dest):
            print('  ✓', linea)
    else:
        main()
