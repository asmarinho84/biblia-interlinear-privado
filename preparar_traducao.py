#!/usr/bin/env python3
"""Congela dados_biblia/lexico/entradas.tsv: id, idioma, chave, referência (translit./lema), glosa EN, freq.
Ordenado por frequência (as mais usadas primeiro). Cada ENTRADA é traduzida com seu contexto,
porque a mesma glosa inglesa ('bear') pode servir a raízes diferentes."""
import json, sys
from pathlib import Path
L = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'dados_biblia') / 'lexico'
h = json.load(open(L / 'hebraico_en.json', encoding='utf-8'))
g = json.load(open(L / 'grego_en.json', encoding='utf-8'))
rows = [('H', k, v.get('xlit') or '', v['en'], v['freq']) for k, v in h.items()]
rows += [('G', k, k, v['en'], v['freq']) for k, v in g.items()]
rows.sort(key=lambda r: (-r[4], r[0], r[1]))
with open(L / 'entradas.tsv', 'w', encoding='utf-8') as f:
    for i, (lg, k, ref, en, fr) in enumerate(rows, 1):
        assert '\t' not in en and '|' not in en and '|' not in ref, (k, en)
        f.write(f'{i}\t{lg}\t{k}\t{ref}\t{en}\t{fr}\n')
print(len(rows), 'entradas;', sum(1 for r in rows if r[0] == 'H'), 'hebraicas,', sum(1 for r in rows if r[0] == 'G'), 'gregas')
