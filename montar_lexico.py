#!/usr/bin/env python3
"""
montar_lexico.py — monta o léxico lema -> glosa curta (em inglês) a partir DOS DICIONÁRIOS
(nenhuma Bíblia é usada) e lista as glosas únicas que faltam traduzir para o português.

Fontes:
  Hebraico/aramaico: OpenScriptures HebrewLexicon  (LexicalIndex.xml, def curta por entrada;
                     HebrewStrong.xml como reserva — só <def>, nunca o campo <usage>, que é KJV)
  Grego:             MorphGNT morphological-lexicon (lexemes.yaml, campo gloss)

Saída (em dados_biblia/lexico/):
  hebraico_en.json   chave "1254 a" -> {en, pos, xlit, fonte, freq}
  grego_en.json      lema          -> {en, pos, fonte, freq}
  pendentes.tsv      glosa_en <TAB> frequência no texto   (as que ainda não têm tradução PT)
"""
import collections
import glob
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

DADOS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'dados_biblia'
NS = '{http://openscriptures.github.com/morphhb/namespace}'
LEX = DADOS / 'lexico'
LEX.mkdir(exist_ok=True)


def chaves_hebraicas_do_corpus():
    freq = collections.Counter()
    morf = {}
    for jl in sorted(glob.glob(str(DADOS / 'saida' / 'jsonl' / '*.jsonl')))[:39]:
        for l in open(jl, encoding='utf-8'):
            r = json.loads(l)
            lem = r['lemma'] or ''
            partes = lem.split('/')
            mparts = (r['morph'] or '')[1:].split('/')
            # alinhar partes numéricas do lemma com os morfemas (prefixos têm letra, não número)
            for i, p in enumerate(partes):
                if re.match(r'^\d', p):
                    k = p.replace('+', '').strip()
                    freq[k] += 1
                    if i < len(mparts):
                        morf.setdefault(k, mparts[i])
    return freq, morf


def hebraico():
    freq, morf = chaves_hebraicas_do_corpus()
    root = ET.parse(DADOS / 'dicionarios' / 'hebraico_LexicalIndex.xml').getroot()
    idx = collections.defaultdict(list)                  # (strong, aug) -> [(def,pos,xlit)]
    for e in root.iter(NS + 'entry'):
        d = e.find(NS + 'def')
        x = e.find(NS + 'xref')
        w = e.find(NS + 'w')
        if d is None or x is None or x.get('strong') is None:
            continue
        pos = e.find(NS + 'pos')
        idx[(x.get('strong'), x.get('aug') or '')].append(
            ((d.text or '').strip(), pos.text if pos is not None else '', w.get('xlit') if w is not None else ''))
    hs = ET.parse(DADOS / 'dicionarios' / 'hebraico_HebrewStrong.xml').getroot()
    strong_def = {}
    for e in hs.iter(NS + 'entry'):
        m = e.find(NS + 'meaning')
        d = m.find(NS + 'def') if m is not None else None
        if d is not None and d.text:
            strong_def[e.get('id')] = d.text.strip()
    out, falta = {}, []
    for k, n in freq.items():
        num, _, aug = k.partition(' ')
        cand = idx.get((num, aug)) or idx.get((num, ''))
        if not cand and aug:
            cand = idx.get((num, 'a'))
        if cand:
            en, pos, xl = cand[0]
            fonte = 'LexicalIndex'
        elif ('H' + num) in strong_def:
            en, pos, xl, fonte = strong_def['H' + num], morf.get(k, ''), '', 'HebrewStrong'
        else:
            falta.append(k)
            continue
        out[k] = {'en': en, 'pos': pos or morf.get(k, '')[:2], 'xlit': xl, 'fonte': fonte, 'freq': n,
                  'morf': morf.get(k, '')}
    return out, falta


def grego():
    lex = yaml.safe_load(open(DADOS / 'dicionarios' / 'grego_lexemes.yaml', encoding='utf-8'))
    por_nfc = {unicodedata.normalize('NFC', k): v for k, v in lex.items()}
    freq = collections.Counter()
    for jl in sorted(glob.glob(str(DADOS / 'saida' / 'jsonl' / '*.jsonl')))[39:]:
        for l in open(jl, encoding='utf-8'):
            freq[json.loads(l)['lemma']] += 1
    out, falta = {}, []
    # lemas ausentes do lexemes.yaml (definição de dicionário, preenchida à mão)
    manual = {'μήν': 'month', 'συναπάγομαι': 'be carried away with'}
    for lem, n in freq.items():
        v = por_nfc.get(unicodedata.normalize('NFC', lem))
        if (v is None or not v.get('gloss')) and lem in manual:
            out[lem] = {'en': manual[lem], 'pos': 'N' if lem == 'μήν' else 'V', 'fonte': 'manual',
                        'strongs': None, 'freq': n}
            continue
        if v is None or not v.get('gloss'):
            falta.append(lem)
            continue
        out[lem] = {'en': str(v['gloss']).strip(), 'pos': v.get('pos', ''), 'fonte': 'MorphGNT',
                    'strongs': v.get('strongs'), 'freq': n}
    return out, falta


def main():
    h, hf = hebraico()
    g, gf = grego()
    print(f'Hebraico: {len(h)} chaves com glosa, {len(hf)} sem: {hf[:20]}')
    print(f'Grego:    {len(g)} lemas com glosa, {len(gf)} sem: {gf[:20]}')
    json.dump(h, open(LEX / 'hebraico_en.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump(g, open(LEX / 'grego_en.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump({'hebraico': hf, 'grego': gf}, open(LEX / 'sem_glosa.json', 'w', encoding='utf-8'),
              ensure_ascii=False)
    tr = {}
    p = LEX / 'traducoes_pt.tsv'
    if p.exists():
        for ln in open(p, encoding='utf-8'):
            if '\t' in ln:
                a, b = ln.rstrip('\n').split('\t', 1)
                tr[a] = b
    unicas = collections.Counter()
    for d in (h, g):
        for v in d.values():
            unicas[v['en']] += v['freq']
    pend = [(en, n) for en, n in unicas.most_common() if en not in tr]
    with open(LEX / 'pendentes.tsv', 'w', encoding='utf-8') as f:
        for en, n in pend:
            f.write(f'{en}\t{n}\n')
    print(f'glosas únicas: {len(unicas)}  já traduzidas: {len(unicas) - len(pend)}  pendentes: {len(pend)}')


if __name__ == '__main__':
    main()
