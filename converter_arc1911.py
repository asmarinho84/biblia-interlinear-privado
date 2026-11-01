#!/usr/bin/env python3
"""Converte o canon Markdown da ARC 1911 (Project Gutenberg #62383, via github.com/mazza/biblia-arc1911, CC0/domínio público)
para o formato usado pelo projeto (arc/pt_arc.json: lista de livros {abbrev,name,chapters:[[versículos]]}).
O texto é mantido na grafia de 1911 (sem modernizar). Removidos apenas: chamadas de nota [^..] e os asteriscos de itálico."""
import json, re, sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parent
canon = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / 'dados_biblia' / 'arc' / 'arc1911_fonte' / 'canon'
saida = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / 'dados_biblia' / 'arc' / 'pt_arc1911.json'
COMMIT = 'eda2823f85894a2b09f5c191186325467410739f'  # github.com/mazza/biblia-arc1911 (texto do Gutenberg #62383, sha256 bf9c6053…)
if not canon.is_dir():  # baixa e extrai o canon fixado por commit
    import urllib.request, zipfile, io
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(f'https://codeload.github.com/mazza/biblia-arc1911/zip/{COMMIT}').read()))
    destino = canon.parent; destino.mkdir(parents=True, exist_ok=True)
    for n in z.namelist():
        r = n.split('/', 1)[1]
        if r.startswith(('canon/', 'LICENSE', 'NOTICE.md')) and not n.endswith('/'):
            (destino / r).parent.mkdir(parents=True, exist_ok=True); (destino / r).write_bytes(z.read(n))
V = re.compile(r'^\*\*(\d+)\*\*\s+(.*)$')
livros = []
for pasta in sorted(p for p in canon.iterdir() if p.is_dir()):
    caps = []; titulos = {}
    for f in sorted(pasta.glob('*.md')):
        vs = {}
        tt = []
        for ln in f.read_text(encoding='utf-8').splitlines():
            if ln.startswith('#### '): tt.append(ln[5:].strip())
            m = V.match(ln.strip())
            if not m: continue
            t = re.sub(r'\s*\[\^[^\]]+\]', '', m.group(2)).replace('*', '')
            t = re.sub(r'\s+', ' ', t).strip()
            vs[int(m.group(1))] = t
        n = len(vs)
        assert sorted(vs) == list(range(1, n + 1)), (f, 'versículos não sequenciais')
        caps.append([vs[i] for i in range(1, n + 1)])
        if tt: titulos[len(caps)] = re.sub(r'\s+', ' ', ' '.join(re.sub(r'\s*\[\^[^\]]+\]', '', x).replace('*', '') for x in tt)).strip()
    livros.append({'abbrev': pasta.name.split('-')[1].lower(), 'name': pasta.name, 'chapters': caps, 'titles': titulos})
saida.write_text(json.dumps(livros, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(len(livros), 'livros', sum(len(l['chapters']) for l in livros), 'caps', sum(len(c) for l in livros for c in l['chapters']), 'versículos ->', saida)
