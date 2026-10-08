"""Hoja de revisión de pelajes con el código real del juego (lo que se ve es lo mismo que en el juego).

Uso:
  python hoja_pelajes.py salida.png calico carey:cascabel siames:luna   (pelaje[:accesorio][:semilla])
  opciones: --titulo "Texto"  --grande (poses más grandes, para revisar detalles)

Necesita Microsoft Edge. Arma una página de prueba con prueba_base.html (una partida guardada de ejemplo)
+ index.html, y le toma captura.
"""
import os, re, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
JUEGO = AQUI.parent
EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'

args = sys.argv[1:]
grande = '--grande' in args
titulo = 'Pelajes'
if '--titulo' in args:
    i = args.index('--titulo'); titulo = args[i + 1]; del args[i:i + 2]
args = [a for a in args if a != '--grande']
salida, gatos = args[0], args[1:]

filas = []
for g in gatos:
    p = g.split(':')
    filas.append({'fur': p[0], 'acc': p[1] if len(p) > 1 and p[1] else 'ninguno', 'seed': int(p[2]) if len(p) > 2 else 3})

esc = 2 if grande else 1
poses = [('frente', 'De frente', 150), ('sentado', 'Sentado', 150), ('acostado', 'Acostado', 130), ('caminar1', 'Caminando', 110),
         ('caminar4', 'Caminando', 110), ('dormido', 'Dormido', 110), ('colgado', 'Al levantarlo', 200)]
js_poses = '[' + ','.join(f"['{a}','{b}',{c * esc}]" for a, b, c in poses) + ']'
js_filas = '[' + ','.join("{fur:'%s',acc:'%s',seed:%d,sex:'f',pat:'parejo',eyes:'normal'}" % (f['fur'], f['acc'], f['seed']) for f in filas) + ']'

head = (AQUI / 'prueba_base.html').read_text(encoding='utf-8')
src = (JUEGO / 'index.html').read_text(encoding='utf-8')
gancho = "  if (hot && typeof hot.ready"
src = src.replace(gancho, "  window.__ce = { catArtURL, NAMES_OF };\n" + gancho)
pagina = head + src + r'''<style>#cat{position:fixed;inset:0;z-index:99999;background:#131b4a;color:#fff;font-family:Nunito,sans-serif;padding:16px 20px;overflow:hidden}
#cat h1{font-family:"Bagel Fat One";font-weight:400;margin:0 0 6px;font-size:2rem}#cat h3{font-family:"Bagel Fat One";font-weight:400;margin:12px 0 6px;font-size:1.2rem}
#cat .row{display:flex;gap:8px;align-items:flex-end}#cat figure{margin:0;background:#f3e2bf;border-radius:12px;padding:6px;text-align:center;color:#2a1f35}#cat figure img{display:block}#cat figcaption{font-weight:900;font-size:.74rem}</style>
<script>setTimeout(()=>{try{const C=window.__ce;const poses=POSES_JS;let h='<h1>TITULO</h1>';
for(const g of FILAS_JS){h+=`<h3>${C.NAMES_OF[g.fur]||g.fur}${g.acc!=='ninguno'?' · '+(C.NAMES_OF[g.acc]||g.acc):''}</h3><div class="row">`+poses.map(([p,l,hh])=>`<figure><img style="height:${hh}px" src="${C.catArtURL(g,p,false)}"><figcaption>${l}</figcaption></figure>`).join('')+'</div>'}
const d=document.createElement('div');d.id='cat';d.innerHTML=h;document.body.appendChild(d)}catch(e){document.title='ERROR '+e.message}},3500)</script>'''.replace('POSES_JS', js_poses).replace('FILAS_JS', js_filas).replace('TITULO', titulo)

tmp = JUEGO / '_hoja_pelajes.html'
tmp.write_text(pagina, encoding='utf-8')
url = 'file:///' + str(tmp).replace('\\', '/').replace(' ', '%20')
ancho = 1010 * esc if grande else 1010
alto = 110 + len(filas) * (275 * esc)
try:
    r = subprocess.run([EDGE, '--headless=new', '--disable-gpu', '--allow-file-access-from-files', '--virtual-time-budget=8000', '--dump-dom', url],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore')
    m = re.search(r'<title>([^<]*)</title>', r.stdout)
    if m and m.group(1).startswith('ERROR'):
        print(m.group(1))
    subprocess.run([EDGE, '--headless=new', '--disable-gpu', '--allow-file-access-from-files', f'--window-size={ancho},{alto}',
                    '--virtual-time-budget=9000', f'--screenshot={Path(salida).resolve()}', url], capture_output=True)
    print('Hoja guardada en', salida)
finally:
    os.remove(tmp)
