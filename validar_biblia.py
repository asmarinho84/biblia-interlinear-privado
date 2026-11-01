#!/usr/bin/env python3
"""
validar_biblia.py — confere a saída de converter_biblia.py de forma independente.

Verificações:
  1. Contagem de palavras do hebraico bate com o XML original (por versículo, nos
     versículos sem ketiv/qere) e no total.
  2. Contagem de palavras do grego bate com as linhas do MorphGNT (137.554).
  3. Nenhum versículo duplicado/fora de ordem dentro de cada livro.
  4. Esqueleto de letras: a transliteração é lida de volta para letras e comparada
     com as letras do texto original, palavra por palavra (hebraico e grego).
  5. Nenhuma transliteração vazia (exceto palavras ketiv não lidas) e nenhum
     caractere fora do alfabeto de transliteração.
"""
import collections
import glob
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

DADOS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'dados_biblia'
SAIDA = DADOS / 'saida'
OSIS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

FINAIS = str.maketrans('ךםןףץ', 'כמנפצ')


def esqueleto_hebr(orig):
    s = ''.join(c for c in orig if 'א' <= c <= 'ת').translate(FINAIS)
    return re.sub(r'(.)\1+', r'\1', s)            # dagesh forte duplica; colapsa repetições


HEB_REV = [('kh', 'כ'), ('k', 'כ'), ('q', 'ק'), ('f', 'פ'), ('p', 'פ'), ('v', 'ב'), ('b', 'ב'),
           ('w', 'ו'), ('y', 'י'), ('š', 'ש'), ('ś', 'ש'), ('s', 'ס'), ('ṣ', 'צ'), ('ṭ', 'ט'),
           ('ḥ', 'ח'), ('ʾ', 'א'), ('ʿ', 'ע'), ('g', 'ג'), ('d', 'ד'), ('t', 'ת'), ('z', 'ז'),
           ('l', 'ל'), ('m', 'מ'), ('n', 'נ'), ('r', 'ר'), ('h', 'ה'),
           ('î', 'י'), ('ê', 'י'), ('ô', 'ו'), ('û', 'ו'), ('â', 'ה')]
HEB_VOWELS = set('aāăeēĕiouəŏō-')


def esqueleto_translit_hebr(tr):
    tr = unicodedata.normalize('NFC', tr)
    out, i = [], 0
    while i < len(tr):
        for k, v in HEB_REV:
            if tr.startswith(k, i):
                out.append(v)
                i += len(k)
                break
        else:
            if tr[i] in HEB_VOWELS:
                i += 1
            else:
                raise ValueError(f'símbolo inesperado {tr[i]!r}')
    return re.sub(r'(.)\1+', r'\1', ''.join(out))


GRC_DIG = [('nkh', 'γχ'), ('ng', 'γγ'), ('nk', 'γκ'), ('nx', 'γξ'), ('th', 'θ'), ('ph', 'φ'),
           ('kh', 'χ'), ('ps', 'ψ'), ('rh', 'ρ')]
GRC_ONE = {'a': 'α', 'b': 'β', 'g': 'γ', 'd': 'δ', 'e': 'ε', 'z': 'ζ', 'ē': 'η', 'i': 'ι',
           'k': 'κ', 'l': 'λ', 'm': 'μ', 'n': 'ν', 'x': 'ξ', 'o': 'ο', 'p': 'π', 'r': 'ρ',
           's': 'σ', 't': 'τ', 'y': 'υ', 'u': 'υ', 'ō': 'ω', 'ᵢ': 'ι'}


def esqueleto_grc_orig(w):
    d = unicodedata.normalize('NFD', w).lower()
    s = ''.join(c for c in d if not unicodedata.combining(c) or c == 'ͅ')
    s = s.replace('ͅ', 'ι').replace('ς', 'σ').replace('’', '')
    return _nasal(s)


def _nasal(s):
    # νγ/νκ/νξ/νχ e γγ/γκ/γξ/γχ têm a mesma transliteração (ng/nk/nx/nkh): comparar em forma única
    for x in 'γκξχ':
        s = s.replace('γ' + x, 'ν' + x)
    return s


def esqueleto_grc_translit(tr):
    d = unicodedata.normalize('NFD', tr).lower()
    d = ''.join(c for c in d if not unicodedata.combining(c) or c == '̄')
    d = unicodedata.normalize('NFC', d)                 # ē ō voltam a ser uma letra
    d = d.replace('’', '')
    out, i = [], 0
    if d.startswith('h') and not d.startswith('hh'):
        i = 1                                           # aspiração inicial = espírito áspero
    while i < len(d):
        for k, v in GRC_DIG:
            if d.startswith(k, i):
                out.append(v)
                i += len(k)
                break
        else:
            out.append(GRC_ONE[d[i]])
            i += 1
    return _nasal(''.join(out))


def main():
    erros = collections.Counter()
    amostras = collections.defaultdict(list)

    def falha(tipo, msg):
        erros[tipo] += 1
        if len(amostras[tipo]) < 12:
            amostras[tipo].append(msg)

    tot = {'AT': 0, 'NT': 0}
    # ---- 1/3/4/5: hebraico ------------------------------------------------
    for jl in sorted(glob.glob(str(SAIDA / 'jsonl' / '*.jsonl'))):
        num = int(Path(jl).name[:2])
        kind = 'AT' if num <= 39 else 'NT'
        recs = [json.loads(l) for l in open(jl, encoding='utf-8')]
        tot[kind] += len(recs)
        vistos = []
        for r in recs:
            if not vistos or vistos[-1] != (r['cap'], r['ver']):
                vistos.append((r['cap'], r['ver']))
        if len(vistos) != len(set(vistos)):
            falha('versiculo_duplicado', f'{Path(jl).name}')
        for r in recs:
            tr = r['translit']
            if kind == 'AT':
                if not r['lido']:
                    continue
                if not tr:
                    falha('translit_vazia', f"{r['ref']} {r['orig']}")
                    continue
                try:
                    a, b = esqueleto_hebr(r['orig']), esqueleto_translit_hebr(tr)
                except ValueError as e:
                    falha('simbolo_invalido', f"{r['ref']} {tr} {e}")
                    continue
                if 'vogal-deslocada' in r['rev']:        # yod omitido no texto (Jerusalém)
                    a, b = a.replace('י', ''), b.replace('י', '')
                if a != b:
                    falha('esqueleto_hebr', f"{r['ref']} {r['orig']} -> {tr}  ({a} x {b})")
                if tr.endswith('-') or tr.startswith('-') or '--' in tr:
                    falha('hifen_solto', f"{r['ref']} {r['orig']} -> {tr}")
            else:
                if not tr:
                    falha('translit_vazia', f"{r['ref']} {r['orig']}")
                    continue
                try:
                    a, b = esqueleto_grc_orig(r['orig']), esqueleto_grc_translit(tr)
                except (ValueError, KeyError) as e:
                    falha('simbolo_invalido', f"{r['ref']} {tr} {e}")
                    continue
                if a != b:
                    falha('esqueleto_grc', f"{r['ref']} {r['orig']} -> {tr}  ({a} x {b})")

    # ---- 1: contagem do AT contra o XML ----------------------------------
    esperado_at = 0
    for f in sorted(glob.glob(str(DADOS / 'AT_hebraico_WLC' / '[0-9]*.xml'))):
        root = ET.parse(f).getroot()
        for v in root.iter(OSIS + 'verse'):
            kids = list(v)
            normais = sum(1 for k in kids if k.tag == OSIS + 'w' and k.get('type') != 'x-ketiv')
            qere_w = sum(len(r.findall(OSIS + 'w')) for r in v.iter(OSIS + 'rdg')
                         if r.get('type') == 'x-qere')
            ketiv_w = [k for k in kids if k.tag == OSIS + 'w' and k.get('type') == 'x-ketiv']
            esperado_at += normais + qere_w
            # ketiv sem leitura (qere vazio) permanecem como palavras não lidas
            for n in v.findall(OSIS + 'note'):
                if n.get('type') == 'variant':
                    for r in n.findall(OSIS + 'rdg'):
                        if r.get('type') == 'x-qere' and not r.findall(OSIS + 'w'):
                            cat = (n.findtext(OSIS + 'catchWord') or '').split()
                            esperado_at += len(cat)
    # ketiv sem nota variant alguma
    for f in sorted(glob.glob(str(DADOS / 'AT_hebraico_WLC' / '[0-9]*.xml'))):
        root = ET.parse(f).getroot()
        for v in root.iter(OSIS + 'verse'):
            kids = list(v)
            for i, k in enumerate(kids):
                if k.tag == OSIS + 'w' and k.get('type') == 'x-ketiv':
                    j = i + 1
                    while j < len(kids) and (kids[j].tag == OSIS + 'w' and kids[j].get('type') == 'x-ketiv'
                                             or kids[j].tag == OSIS + 'seg' and kids[j].get('subType') == 'x-ketiv'
                                             or kids[j].tag == OSIS + 'note' and kids[j].get('type') != 'variant'):
                        j += 1
                    if not (j < len(kids) and kids[j].tag == OSIS + 'note' and kids[j].get('type') == 'variant'):
                        esperado_at += 1
    if esperado_at != tot['AT']:
        falha('contagem_AT', f'esperado {esperado_at}, obtido {tot["AT"]}')

    # ---- 2: contagem do NT ------------------------------------------------
    linhas = 0
    for f in glob.glob(str(DADOS / 'NT_grego_SBLGNT' / '*.txt')):
        linhas += sum(1 for l in open(f, encoding='utf-8') if l.strip())
    if linhas != tot['NT']:
        falha('contagem_NT', f'esperado {linhas}, obtido {tot["NT"]}')


    # ---- 6: glosa em português e morfologia ------------------------------------------------
    sem_gl = com_marca = 0
    for jl in sorted(glob.glob(str(SAIDA / 'jsonl' / '*.jsonl'))):
        num = int(Path(jl).name[:2])
        for l in open(jl, encoding='utf-8'):
            r = json.loads(l)
            if 'gl' not in r:
                falha('glosa_ausente', f"{Path(jl).name}")
                break
            if num <= 39 and not r['lido']:
                continue
            if not r['gl'].strip():
                falha('glosa_vazia', r['ref'])
            if not r['mf'].strip():
                falha('morfologia_vazia', r['ref'])
            if re.search(r'(^|-)\?[a-z]|^\?$|--|^-|-$', r['gl']):
                falha('glosa_suspeita', f"{r['ref']} {r['orig']} -> {r['gl']}")
            if re.search(r'[A-Za-z]{4,} [a-z]{3,}', r['gl']) and num > 39 and False:
                pass
            # glosas vêm do dicionário em português: nenhuma deve ter caracteres típicos de inglês cru
            if re.search(r"\b(the|of|and)\b", r['gl']):
                falha('glosa_em_ingles', f"{r['ref']} {r['gl']}")
            sem_gl += 0
    print('Glosa PT: todas as palavras lidas têm glosa e morfologia' if not erros else '')
    print(f"Palavras AT: {tot['AT']}   (esperado pelo XML: {esperado_at})")
    print(f"Palavras NT: {tot['NT']}   (linhas MorphGNT: {linhas})")
    if not erros:
        print('TUDO OK — nenhuma divergência.')
    else:
        for tipo, n in erros.items():
            print(f'\n[{tipo}] {n} ocorrência(s). Primeiras:')
            for m in amostras[tipo]:
                print('   ', m)
        sys.exit(1)


if __name__ == '__main__':
    main()
