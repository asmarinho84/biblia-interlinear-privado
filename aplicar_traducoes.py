#!/usr/bin/env python3
"""
aplicar_traducoes.py — junta lexico/entradas.tsv (lista congelada) com lexico/pt_por_id.txt
(traduções id|pt) e gera:
  lexico/hebraico_pt.json  {chave "1254 a": {pt, en, pos, xlit, freq, morf}}
  lexico/grego_pt.json     {lema: {pt, en, pos, strongs, freq}}
Verifica cobertura de 100%, ids sem lacunas, sem duplicatas e sem glosa vazia.
"""
import json
import sys
from pathlib import Path

DADOS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'dados_biblia'
LEX = DADOS / 'lexico'


def main():
    pt = {}
    for n, ln in enumerate(open(LEX / 'pt_por_id.txt', encoding='utf-8'), 1):
        a, _, b = ln.rstrip('\n').partition('|')
        i = int(a)
        if i in pt:
            sys.exit(f'id duplicado {i} (linha {n})')
        if not b.strip():
            sys.exit(f'tradução vazia para id {i}')
        pt[i] = b.strip()
    ent = [ln.rstrip('\n').split('\t') for ln in open(LEX / 'entradas.tsv', encoding='utf-8')]
    ids = {int(e[0]) for e in ent}
    if ids != set(pt):
        sys.exit(f'ids diferentes: faltam {sorted(ids - set(pt))[:10]} sobram {sorted(set(pt) - ids)[:10]}')
    h_en = json.load(open(LEX / 'hebraico_en.json', encoding='utf-8'))
    g_en = json.load(open(LEX / 'grego_en.json', encoding='utf-8'))
    h, g = {}, {}
    for e in ent:
        i, lang, key = int(e[0]), e[1], e[2]
        if lang == 'H':
            d = dict(h_en[key])
            d['pt'] = pt[i]
            h[key] = d
        else:
            d = dict(g_en[key])
            d['pt'] = pt[i]
            g[key] = d
    if len(h) != len(h_en) or len(g) != len(g_en):
        sys.exit(f'cobertura incompleta: H {len(h)}/{len(h_en)}  G {len(g)}/{len(g_en)}')
    json.dump(h, open(LEX / 'hebraico_pt.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump(g, open(LEX / 'grego_pt.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'OK  hebraico {len(h)}  grego {len(g)}  (100% traduzido)')


if __name__ == '__main__':
    main()
