"""Copia el juego al repo y a Drive, y deja en files.json los archivos de arte que cambiaron (para el artifact)."""
import shutil, glob, os, json, sys
R = 'C:/Users/Admin/OneDrive/GerardoMtz/Portafolio GitHub/encaja/cat-evolution/'
C = 'C:/Users/Admin/Desktop/Claude Code/CatEvolution/'
D = 'G:/Mi unidad/videogame/Cat Evolution/'
old = open(R + 'index.html', encoding='utf-8').read()
src = open(C + 'index.html', encoding='utf-8').read()
new = old[:old.index('<title>')] + src.rstrip() + old[old.rindex('</script>') + 9:]
open(R + 'index.html', 'w', encoding='utf-8', newline='\n').write(new)
open(D + 'Cat Evolution.html', 'w', encoding='utf-8', newline='\n').write(new)
for f in glob.glob(C + 'arte/*'):
    if os.path.isfile(f):
        shutil.copy2(f, R + 'arte/')
for f in glob.glob(C + 'herramientas/*.py'):
    shutil.copy2(f, R + 'herramientas/')
    shutil.copy2(f, D + 'herramientas/')
files = {'arte/manifest.json': C + 'arte/manifest.json'}
for pat in sys.argv[1:]:
    for f in glob.glob(C + 'arte/' + pat):
        files['arte/' + os.path.basename(f)] = f.replace(os.sep, '/')
print(json.dumps(files))
