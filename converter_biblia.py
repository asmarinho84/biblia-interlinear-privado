#!/usr/bin/env python3
"""
converter_biblia.py — ETAPA 2: organiza e translitera (sem traduzir).

Lê ./dados_biblia (baixado por baixar_biblia.py) e gera, para cada um dos 66 livros:

  saida/jsonl/NN_Sigla.jsonl   uma linha JSON por palavra, na ordem de leitura
  saida/html/NN_Sigla.html     interlinear: cada palavra em coluna, original em cima
                               e transliteração embaixo
  saida/index.html             índice
  saida/relatorio.json         contagens e alertas

ORDEM DE ESCRITA / LEITURA
  Hebraico e aramaico (AT): direita -> esquerda  (HTML com dir="rtl")
  Grego (NT):               esquerda -> direita  (HTML com dir="ltr")
  Nos arquivos JSONL as palavras ficam sempre em ordem LÓGICA de leitura
  (1ª palavra do versículo = 1ª linha), independente do sentido visual.

TRANSLITERAÇÃO (PT-BR acadêmica, baseada em regras; tabelas abaixo)
  Hebraico: a partir do texto pontuado (WLC), com regras para dagesh forte/leve,
            shevá vocal/silencioso, matres lectionis, patach furtivo, ketiv/qere.
  Grego:    letra por letra, com espíritos, acentos tônicos, iota subscrito,
            ditongos e nasalização do gama.

USO
  python3 converter_biblia.py              # converte tudo e valida
  python3 converter_biblia.py --teste      # só os testes unitários de transliteração
  python3 converter_biblia.py --livro Gn   # só um livro (sigla PT-BR: Gn, Mt, Jo ...)
"""
import argparse
import collections
import html
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baixar_biblia import AT, NT  # listas (id, sigla, nome)

OSIS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

# =====================================================================
# 1. TABELAS DE TRANSLITERAÇÃO (edite aqui se quiser outro padrão)
# =====================================================================

# Hebraico: letra -> (forma com dagesh/oclusiva, forma sem dagesh/fricativa)
CONS = {
    # Só ב כ פ mudam de som com/sem dagesh (b/v, k/kh, p/f). ג ד ת não são distinguidos.
    'א': ('ʾ', 'ʾ'), 'ב': ('b', 'v'), 'ג': ('g', 'g'), 'ד': ('d', 'd'),
    'ה': ('h', 'h'), 'ו': ('w', 'w'), 'ז': ('z', 'z'), 'ח': ('ḥ', 'ḥ'),
    'ט': ('ṭ', 'ṭ'), 'י': ('y', 'y'), 'כ': ('k', 'kh'), 'ך': ('k', 'kh'),
    'ל': ('l', 'l'), 'מ': ('m', 'm'), 'ם': ('m', 'm'), 'נ': ('n', 'n'),
    'ן': ('n', 'n'), 'ס': ('s', 's'), 'ע': ('ʿ', 'ʿ'), 'פ': ('p', 'f'),
    'ף': ('p', 'f'), 'צ': ('ṣ', 'ṣ'), 'ץ': ('ṣ', 'ṣ'), 'ק': ('q', 'q'),
    'ר': ('r', 'r'), 'ש': ('š', 'š'), 'ת': ('t', 't'),
}
BGDKPT = set('בגדכךפףת')

VOWMARK = {0x5B0: 'sheva', 0x5B1: 'hsegol', 0x5B2: 'hpatah', 0x5B3: 'hqamats',
           0x5B4: 'hiriq', 0x5B5: 'tsere', 0x5B6: 'segol', 0x5B7: 'patah',
           0x5B8: 'qamats', 0x5B9: 'holam', 0x5BA: 'holamv', 0x5BB: 'qubuts'}
VOWOUT = {'hsegol': 'ĕ', 'hpatah': 'ă', 'hqamats': 'ŏ', 'hiriq': 'i', 'tsere': 'ē',
          'segol': 'e', 'patah': 'a', 'qamats': 'ā', 'holam': 'ō', 'holamv': 'ō',
          'qubuts': 'u'}
MATER_Y = {'hiriq': 'î', 'tsere': 'ê', 'segol': 'ê'}          # vogal + yod
MATER_H = {'qamats': 'â', 'segol': 'eh', 'tsere': 'ēh',       # vogal + he final
           'hiriq': 'ih', 'holam': 'ōh'}

# Qamets qatan (o breve) x gadol (ā): decidido pela MORFOLOGIA do OSHB (ver decide_qamets)
QATAN_ABSOLUTO = {3605}          # kol (כָּל): sempre qatan
# substantivos cujo qamets é gadol mesmo antes de shevá (ex.: יָדְךָ yādəkhā, דָּמְךָ dāməkhā)
GADOL_NOME = {3027, 1818}
# advérbios/palavras aramaicas com qamets qatan antes de shevá: ʾomnām (551), ʾomnâ (546),
# ʾosparnā (629), qŏvēl (6903)
QATAN_LISTA = {546, 551, 629, 6903}

# Grego
GRBASE = {'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'ē',
          'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x',
          'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'ς': 's', 'τ': 't', 'υ': 'y',
          'φ': 'ph', 'χ': 'kh', 'ψ': 'ps', 'ω': 'ō'}
GRVOWEL = set('αεηιουω')
GRDIPH = {('α', 'ι'): 'ai', ('ε', 'ι'): 'ei', ('ο', 'ι'): 'oi', ('υ', 'ι'): 'ui',
          ('α', 'υ'): 'au', ('ε', 'υ'): 'eu', ('η', 'υ'): 'ēu', ('ο', 'υ'): 'ou'}
IOTA_SUB = 'ᵢ'

# =====================================================================
# 2. HEBRAICO
# =====================================================================


class Cl:
    """Um 'cluster': consoante + seus sinais (pontos vocálicos, dagesh, acentos)."""
    __slots__ = ('c', 'dag', 'rafe', 'dot', 'vow', 'acc', 'meteg', 'fim', 'v', 'kind',
                 'forte', 'vocal', 'voiced', 'long', 'qatan', 'furtive', 'extra', 'mi', 'mudo')

    def __init__(self, c):
        self.c = c
        self.dag = self.rafe = self.acc = self.meteg = self.fim = False
        self.dot = None
        self.vow = []
        self.v = None
        self.kind = None
        self.extra = ''          # 'yi' / 'y': yod omitido cuja vogal foi deslocada (ex.: Jerusalém)
        self.mi = 0              # índice do morfema dentro da palavra
        self.forte = self.vocal = self.voiced = self.long = self.qatan = self.furtive = False
        self.mudo = False        # consoante muda (ש sem ponto em Issacar)


def parse_hebr(word):
    cls = []
    for ch in word:
        o = ord(ch)
        if ch == '/':
            if cls:
                cls[-1].fim = True
            continue
        if 0x5D0 <= o <= 0x5EA:
            cls.append(Cl(ch))
            continue
        if not cls:
            raise ValueError(f"sinal sem letra em {word!r}: U+{o:04X}")
        cl = cls[-1]
        if o in VOWMARK:
            cl.vow.append(VOWMARK[o])
        elif o == 0x5BC:
            cl.dag = True
        elif o == 0x5BF:
            cl.rafe = True
        elif o == 0x5C1:
            cl.dot = 'shin'
        elif o == 0x5C2:
            cl.dot = 'sin'
        elif o == 0x5BD:
            cl.meteg = True
        elif 0x591 <= o <= 0x5AF:
            cl.acc = True
        elif o in (0x5C4, 0x5C5):
            pass                                   # pontos extraordinários
        else:
            raise ValueError(f"caractere hebraico desconhecido U+{o:04X} em {word!r}")
    return cls


def strong_num(lemma):
    if not lemma:
        return None
    m = re.search(r'(\d+)', lemma.split('/')[-1])
    return int(m.group(1)) if m else None


def decide_qamets(cl, parts, strong):
    """True = qamets qatan (o); False = gadol (ā); None = ambíguo (usa ā e marca para revisão).
    Só é chamada para qamets sem acento/meteg seguido de shevá (sílaba possivelmente fechada)."""
    if cl.fim:                       # qamets que é um prefixo inteiro (artigo hā-, lā-): gadol
        return False
    if cl.mi >= len(parts):
        return None
    p = parts[cl.mi]
    t = p[:1]
    if t == 'V':
        stem, asp = p[1:2], p[2:3]
        if stem == 'H':              # hofal: hoqṭal
            return True
        if stem == 'q' and asp == 'c' and any(x.startswith('S') for x in parts):
            return True              # infinitivo construto qal + sufixo: qoṭlô (šomʿô)
        return False                 # perfeito/imperfeito/particípio...: qāṭəlû (vocal)
    if t in 'NA':                    # substantivo/adjetivo/nome próprio: qorbān, ḥokhmâ
        return False if cl.mi == cl.mi and strong in GADOL_NOME else True
    return None


def translit_hebr(word, strong=None, morph=None):
    """Retorna (transliteração, [alertas])."""
    cls = parse_hebr(word)
    n = len(cls)
    flags = []
    if n == 0:
        return '', flags
    mi = 0
    for cl in cls:
        cl.mi = mi
        if cl.fim:
            mi += 1
    parts = morph[1:].split('/') if morph else []

    # --- vogais deslocadas / sinais duplos --------------------------------
    for i, cl in enumerate(cls):
        if len(cl.vow) < 2:
            continue
        vs = set(cl.vow)
        prev = cls[i - 1] if i else None
        if cl.c == 'ו' and 'holam' in vs and len(vs) == 2 and prev is not None and not prev.vow:
            outro = [x for x in cl.vow if x != 'holam'][0]    # holam pertence à letra anterior
            prev.vow, cl.vow = ['holam'], [outro]
        elif 'hiriq' in vs and vs & {'patah', 'qamats'}:       # Jerusalém: hiriq do yod omitido
            cl.vow = [x for x in cl.vow if x in ('patah', 'qamats')][:1]
            cl.extra = 'yi'
            flags.append('vogal-deslocada')
        elif 'sheva' in vs and vs & {'patah', 'qamats'}:
            cl.vow = [x for x in cl.vow if x in ('patah', 'qamats')][:1]
            cl.extra = 'y'
            flags.append('vogal-deslocada')
        elif 'sheva' in vs:
            cl.vow = [x for x in cl.vow if x != 'sheva'][:1]
        else:
            flags.append('multivogal')
    for cl in cls:
        cl.v = cl.vow[0] if cl.vow else None

    # --- matres lectionis -------------------------------------------------
    for i, cl in enumerate(cls):
        prev = cls[i - 1] if i else None
        if cl.c == 'ו':
            if cl.v is None and cl.dag:
                cl.kind = 'shureq'                              # û
            elif cl.v == 'holam' and prev is not None and prev.kind is None and prev.v is None:
                cl.kind = 'mater_o'                             # ô
        elif cl.c == 'י':
            if cl.v is None and not cl.dag and prev is not None and prev.kind is None \
                    and prev.v in MATER_Y:
                cl.kind = 'mater_y'                             # î ê
        elif cl.c == 'ה':
            if i == n - 1 and i > 0 and cl.v is None and not cl.dag and \
                    (prev.kind == 'mater_o' or (prev.kind is None and prev.v in MATER_H)):
                cl.kind = 'mater_h'                             # â eh ēh

    # --- qamets gadol x qatan --------------------------------------------
    for i, cl in enumerate(cls):
        if cl.v != 'qamats':
            continue
        nxt = cls[i + 1] if i + 1 < n else None
        sem_tonica = not (cl.acc or cl.meteg)
        fechada = nxt is not None and nxt.v == 'sheva' and i + 1 < n - 1
        if strong in QATAN_ABSOLUTO:
            cl.qatan = True
        elif strong in QATAN_LISTA and fechada and sem_tonica:
            cl.qatan = True
        elif fechada and sem_tonica and nxt.c != cl.c:
            d = decide_qamets(cl, parts, strong)
            if d is None:
                flags.append('qamets?')                         # ambíguo: padrão = gadol (ā)
            else:
                cl.qatan = d

    # --- esquerda -> direita: dagesh, shevá, sonoridade ------------------
    for i, cl in enumerate(cls):
        prev = cls[i - 1] if i else None
        nxt = cls[i + 1] if i + 1 < n else None
        if cl.dag and cl.kind != 'shureq' and not (cl.c == 'ה' and i == n - 1):
            if cl.c in BGDKPT:
                cl.forte = prev is not None and prev.voiced      # senão: dagesh leve
            else:
                cl.forte = prev is not None
        if cl.v == 'sheva':
            if i == 0 or cl.forte:
                cl.vocal = True
            elif i == n - 1:
                cl.vocal = False
            elif prev.v == 'sheva':
                cl.vocal = not prev.vocal
            elif nxt.v == 'sheva':
                cl.vocal = False
            elif nxt.c == cl.c:
                cl.vocal = True
            else:
                # álef quiescente (sem vogal) não conta: יֹאמְרוּ tōʾmərû, shevá vocal após ō
                p = prev
                if p.c == 'א' and p.v is None and p.kind is None and i >= 2:
                    p = cls[i - 2]
                cl.vocal = p.long
        cl.voiced = (cl.kind in ('shureq', 'mater_o', 'mater_y', 'mater_h') or
                     (cl.v not in (None, 'sheva')) or (cl.v == 'sheva' and cl.vocal))
        cl.long = (cl.kind in ('shureq', 'mater_o', 'mater_y', 'mater_h') or
                   cl.v in ('tsere', 'holam', 'holamv') or (cl.v == 'qamats' and not cl.qatan))

    # --- patach furtivo --------------------------------------------------
    last = cls[-1]
    if n > 1 and last.v == 'patah' and (last.c in 'חע' or (last.c == 'ה' and last.dag)):
        p = cls[-2]
        if p.kind in ('mater_y', 'mater_o', 'shureq') or p.v in ('tsere', 'holam', 'hiriq', 'qubuts'):
            last.furtive = True

    # --- ש sem ponto logo após שׂ (Issacar, יִשָּׂשכָר): consoante muda --------
    for i, cl in enumerate(cls):
        if (cl.c == 'ש' and cl.dot is None and cl.v is None and i > 0
                and cls[i - 1].c == 'ש' and cls[i - 1].dot == 'sin'):
            cl.mudo = True

    # --- saída -------------------------------------------------------------
    outs = []
    for i, cl in enumerate(cls):
        nxt = cls[i + 1] if i + 1 < n else None
        k = cl.kind
        if k == 'shureq':
            s = 'û'
        elif k == 'mater_o':
            s = 'ô'
        elif k == 'mater_y':
            s = ''
        elif k == 'mater_h':
            s = 'h' if cls[i - 1].kind == 'mater_o' else ''
        elif cl.mudo:
            s = ''
        else:
            if cl.c == 'ש':
                if cl.dot is None:
                    flags.append('shin-sem-ponto')
                base = 'ś' if cl.dot == 'sin' else 'š'
            elif cl.c in BGDKPT:
                base = CONS[cl.c][0] if (cl.dag and not cl.rafe) else CONS[cl.c][1]
            else:
                base = CONS[cl.c][0]
            if cl.forte:
                base = base * 2
            v = cl.v
            if cl.furtive:
                vo = ''
                base = 'a' + base
            elif v is None:
                vo = ''
            elif v == 'sheva':
                vo = 'ə' if cl.vocal else ''
            elif v == 'qamats':
                vo = 'o' if cl.qatan else 'ā'
            else:
                vo = VOWOUT[v]
            if nxt is not None and nxt.kind == 'mater_y' and v in MATER_Y:
                vo = MATER_Y[v]
            elif nxt is not None and nxt.kind == 'mater_h' and v in MATER_H and not cl.furtive:
                vo = MATER_H[v]
            s = base + vo + cl.extra
        outs.append(s)
    # hífens entre morfemas; se a fronteira cai antes de uma mater (que já foi absorvida
    # pela vogal anterior), o hífen vai para depois dela; nunca no fim da palavra
    hif = [False] * n
    for i, cl in enumerate(cls):
        if cl.fim and i < n - 1:
            if cl.v is None and cl.kind is None and cls[i + 1].kind in ('mater_o', 'shureq'):
                continue                     # לוֹ lô, ל+וֹ: consoante sem vogal própria, sem hífen
            j = i
            while j + 1 < n and cls[j + 1].kind in ('mater_y', 'mater_h'):
                j += 1
            if j < n - 1:
                hif[j] = True
    return ''.join(o + ('-' if hif[i] else '') for i, o in enumerate(outs)), flags


# =====================================================================
# 3. GREGO
# =====================================================================
ACUTE, GRAVE, CIRC = '́', '̀', '͂'
PSILI, DASIA, DIAL, YPO = '̓', '̔', '̈', 'ͅ'


def translit_grc(word, lemma=False):
    d = unicodedata.normalize('NFD', word)
    units = []
    for ch in d:
        if unicodedata.combining(ch):
            if not units:
                raise ValueError(f"sinal sem letra em {word!r}")
            units[-1]['m'].add(ch)
        elif ch == '’' or ch == "'":
            units.append({'b': '’', 'u': False, 'm': set()})
        elif lemma and ch in '()-':          # lemas como οὕτω(ς) trazem parênteses
            units.append({'b': ch, 'u': False, 'm': set()})
        else:
            lo = ch.lower()
            if lo not in GRBASE:
                raise ValueError(f"caractere grego desconhecido {ch!r} (U+{ord(ch):04X}) em {word!r}")
            units.append({'b': lo, 'u': ch != lo, 'm': set()})
    if not units:
        return ''
    out = []
    rough = any(DASIA in u['m'] for u in units)
    initial_rho_rough = units[0]['b'] == 'ρ' and DASIA in units[0]['m']
    if rough and not initial_rho_rough:
        out.append('h')

    def acc(u):
        m = u['m']
        # perispômeni vira circunflexo latino (U+0302): o til U+0342 renderiza mal em letras latinas
        return (ACUTE if ACUTE in m else GRAVE if GRAVE in m else '̂' if CIRC in m else '')

    i, n = 0, len(units)
    while i < n:
        u = units[i]
        b = u['b']
        nb = units[i + 1]['b'] if i + 1 < n else None
        if b in '’()-':
            out.append(b)
        elif b == 'ρ':
            out.append('rh' if (i == 0 and DASIA in u['m']) else 'r')
        elif b == 'γ':
            out.append('n' if nb in ('γ', 'κ', 'ξ', 'χ') else 'g')
        elif b in GRVOWEL:
            nxt = units[i + 1] if i + 1 < n else None
            if (nxt is not None and (b, nxt['b']) in GRDIPH and DIAL not in nxt['m']
                    and YPO not in u['m']):
                dip = GRDIPH[(b, nxt['b'])]
                first, second = dip[:-1], dip[-1]
                out.append(unicodedata.normalize('NFC', first + (acc(u))))
                out.append(unicodedata.normalize('NFC', second + acc(nxt)))
                i += 2
                continue
            s = GRBASE[b]
            if DIAL in u['m']:
                s += DIAL
            s += acc(u)
            if YPO in u['m']:
                s += IOTA_SUB
            out.append(unicodedata.normalize('NFC', s))
        else:
            out.append(GRBASE[b])
        i += 1
    res = ''.join(out)
    if units[0]['u'] and res:
        res = res[0].upper() + res[1:]
    return unicodedata.normalize('NFC', res)


# =====================================================================
# 4. LEITURA DOS ARQUIVOS
# =====================================================================
def tag(e):
    return e.tag.replace(OSIS, '')


def wtext(w):
    return ''.join(w.itertext()).strip()


def hebr_word(w, lang_hint=None):
    seg = wtext(w)
    morph = w.get('morph', 'H')
    lang = 'arc' if morph[:1] == 'A' else 'hbo'
    st = strong_num(w.get('lemma'))
    tr, flags = translit_hebr(seg, st, morph)
    return {'lang': lang, 'orig': seg.replace('/', ''), 'seg': seg, 'translit': tr,
            'lemma': w.get('lemma'), 'strong': st, 'morph': morph, 'lido': True,
            'escrito': True, 'ketiv': None, 'depois': '', 'par': '', 'rev': flags}


def read_hebrew_book(path, book_idx, sigla):
    root = ET.parse(path).getroot()
    verses = []
    for v in root.iter(OSIS + 'verse'):
        oid = v.get('osisID', '').split()[0]
        parts = oid.split('.')
        cap, ver = int(parts[-2]), int(parts[-1])
        words = []
        kids = list(v)
        i = 0
        while i < len(kids):
            k = kids[i]
            t = tag(k)
            if t == 'w' and k.get('type') == 'x-ketiv':
                ketivs = [k]
                j = i + 1
                note = None
                while j < len(kids):
                    kj, tj = kids[j], tag(kids[j])
                    if tj == 'w' and kj.get('type') == 'x-ketiv':
                        ketivs.append(kj)
                    elif tj == 'seg' and kj.get('subType') == 'x-ketiv':
                        pass
                    elif tj == 'note' and kj.get('type') == 'variant':
                        note = kj
                        break
                    elif tj == 'note':
                        pass
                    else:
                        break
                    j += 1
                ketiv_txt = ' '.join(wtext(x).replace('/', '') for x in ketivs)
                rdg = None
                if note is not None:
                    for r in note.iter(OSIS + 'rdg'):
                        if r.get('type') == 'x-qere':
                            rdg = r
                if rdg is not None and rdg.findall(OSIS + 'w'):
                    first = True
                    for rk in rdg:
                        rt = tag(rk)
                        if rt == 'w':
                            wd = hebr_word(rk)
                            if first:
                                wd['ketiv'] = ketiv_txt
                                first = False
                            words.append(wd)
                        elif rt == 'seg' and words:
                            _attach(words[-1], rk)
                else:
                    # ketiv sem qere: escrito mas não lido
                    for x in ketivs:
                        seg = wtext(x)
                        words.append({'lang': 'hbo', 'orig': seg.replace('/', ''), 'seg': seg,
                                      'translit': '', 'lemma': x.get('lemma'),
                                      'strong': strong_num(x.get('lemma')), 'morph': x.get('morph'),
                                      'lido': False, 'escrito': True, 'ketiv': ketiv_txt,
                                      'depois': '', 'par': '', 'rev': []})
                i = j + 1 if note is not None else j
                continue
            if t == 'w':
                words.append(hebr_word(k))
            elif t == 'seg' and words:
                _attach(words[-1], k)
            elif t == 'note' and k.get('type') == 'variant':
                # qere sem ketiv: palavra LIDA mas NÃO ESCRITA no manuscrito (ex.: Rt 3:5)
                for r in k.iter(OSIS + 'rdg'):
                    if r.get('type') != 'x-qere':
                        continue
                    for rk in r:
                        rt = tag(rk)
                        if rt == 'w':
                            wd = hebr_word(rk)
                            wd['escrito'] = False
                            words.append(wd)
                        elif rt == 'seg' and words:
                            _attach(words[-1], rk)
            i += 1
        verses.append((cap, ver, words))
    return verses


def _attach(word, seg):
    ty = seg.get('type')
    txt = (seg.text or '').strip()
    if ty == 'x-maqqef':
        word['depois'] += '־'
    elif ty == 'x-sof-pasuq':
        word['depois'] += '׃'
    elif ty == 'x-paseq':
        word['depois'] += ' ׀'
    elif ty in ('x-pe', 'x-samekh', 'x-reversednun'):
        word['par'] += txt


def read_greek_book(path):
    verses = collections.OrderedDict()
    for ln in Path(path).read_text(encoding='utf-8').splitlines():
        if not ln.strip():
            continue
        f = ln.split(' ')
        ref, pos, parse, texto, orig, norm, lemma = f
        cap, ver = int(ref[2:4]), int(ref[4:6])
        k = texto.find(orig)
        antes = texto[:k] if k >= 0 else ''
        depois = texto[k + len(orig):] if k >= 0 else ''
        w = {'lang': 'grc', 'orig': orig, 'translit': translit_grc(orig), 'texto': texto,
             'antes': antes, 'depois': depois, 'pos': pos, 'parse': parse, 'norm': norm,
             'lemma': lemma, 'lemma_translit': translit_grc(lemma, lemma=True), 'rev': []}
        verses.setdefault((cap, ver), []).append(w)
    return [(c, v, ws) for (c, v), ws in verses.items()]


# =====================================================================
# 5. SAÍDA
# =====================================================================
CSS = """
:root{--bg:#fff;--fg:#1d1d1f;--mut:#8a8a8f;--tr:#0a6b4b;--ln:#e2e2e6}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--fg:#ececf0;--mut:#8f8f96;--tr:#4fd1a1;--ln:#2c2c30}}
body{background:var(--bg);color:var(--fg);font-family:system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:1rem 1.2rem 4rem}
h1{font-size:1.5rem;margin:.6rem 0 .2rem}h1 small{display:block;font-size:.8rem;color:var(--mut);font-weight:400;margin-top:.2rem}
h2{font-size:1.05rem;margin:2rem 0 .8rem;border-bottom:1px solid var(--ln);padding-bottom:.3rem}
.v{display:flex;flex-wrap:wrap;gap:.1rem 1rem;margin:0 0 .9rem;padding-bottom:.7rem;border-bottom:1px dotted var(--ln)}
.nv{align-self:flex-start;font-size:.72rem;font-weight:600;color:var(--mut);padding-top:.35rem;min-width:1.4rem;text-align:center}
.w{display:flex;flex-direction:column;align-items:center;text-align:center}
.o{font-size:1.75rem;line-height:1.55;font-family:"SBL Hebrew","Ezra SIL","Noto Serif Hebrew","Times New Roman",serif}
.grc .o{font-family:"SBL Greek","Gentium Plus","Cardo","Noto Serif","Times New Roman",serif;font-size:1.5rem}
.t{font-style:italic;font-size:.88rem;color:var(--tr);direction:ltr;unicode-bidi:isolate;white-space:nowrap}
.q .o{border-bottom:1px dashed var(--mut)}.qs .o{border-bottom:1px dotted var(--mut);opacity:.8}.nl .o{opacity:.45}.nl .t{color:var(--mut)}
a{color:inherit}ul{columns:2;list-style:none;padding:0}li{padding:.15rem 0}
"""


def esc(s):
    return html.escape(s, quote=True)


def html_book(num, sigla, nome, lang_kind, verses):
    rtl = lang_kind == 'AT'
    direcao = 'rtl' if rtl else 'ltr'
    lang = 'he' if rtl else 'grc'
    sub = ('Texto hebraico/aramaico (WLC) — leitura da direita para a esquerda' if rtl
           else 'Texto grego (SBLGNT) — leitura da esquerda para a direita')
    out = [f'<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{esc(nome)} — interlinear</title><style>{CSS}</style>'
           f'<h1>{esc(nome)}<small>{sub}</small></h1>']
    cap_atual = None
    for cap, ver, words in verses:
        if cap != cap_atual:
            if cap_atual is not None:
                out.append('</section>')
            out.append(f'<section><h2>Capítulo {cap}</h2>')
            cap_atual = cap
        out.append(f'<div class="v{"" if rtl else " grc"}" dir="{direcao}" lang="{lang}">'
                   f'<span class="nv">{ver}</span>')
        for w in words:
            cls = 'w'
            title = ''
            if w.get('ketiv'):
                cls += ' q'
                title = f' title="ketiv: {esc(w["ketiv"])}"'
            if not w.get('lido', True):
                cls += ' nl'
            if not w.get('escrito', True):
                cls += ' qs'
                title = ' title="lido (qere), mas não escrito no manuscrito"'
            if rtl:
                o = w['orig'] + w['depois'] + w['par']
                t = w['translit'] or '∅'
                if w['depois']:
                    t += ''.join({'־': '-', '׃': '', ' ׀': ' |'}.get(c, '') for c in w['depois'])
            else:
                o = re.sub(r'[⸀-⸅⟦⟧]', '', w['texto'])
                t = w['translit']
            out.append(f'<span class="{cls}"{title}><span class="o">{esc(o)}</span>'
                       f'<span class="t">{esc(t)}</span></span>')
        out.append('</div>')
    out.append('</section>')
    return ''.join(out)


def run(args):
    dados = Path(args.dados)
    saida = Path(args.saida)
    (saida / 'jsonl').mkdir(parents=True, exist_ok=True)
    (saida / 'html').mkdir(parents=True, exist_ok=True)
    livros = []
    for i, (osis, sig, nome) in enumerate(AT, start=1):
        livros.append((i, sig, nome, 'AT', dados / 'AT_hebraico_WLC' / f'{i:02d}_{sig}.xml'))
    for i, (pref, sig, nome) in enumerate(NT, start=40):
        livros.append((i, sig, nome, 'NT', dados / 'NT_grego_SBLGNT' / f'{i:02d}_{sig}.txt'))
    rel = {'livros': {}, 'alertas': collections.Counter()}
    for num, sig, nome, kind, path in livros:
        if args.livro and sig != args.livro:
            continue
        if not path.exists():
            print(f'FALTA {path}', file=sys.stderr)
            sys.exit(1)
        verses = read_hebrew_book(path, num, sig) if kind == 'AT' else read_greek_book(path)
        nw = nv = 0
        with open(saida / 'jsonl' / f'{num:02d}_{sig}.jsonl', 'w', encoding='utf-8') as fj:
            for cap, ver, words in verses:
                nv += 1
                for pos, w in enumerate(words, start=1):
                    rec = {'ref': f'{sig} {cap}:{ver}', 'livro': num, 'cap': cap, 'ver': ver, 'i': pos}
                    rec.update(w)
                    for fl in w['rev']:
                        rel['alertas'][fl] += 1
                    fj.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    nw += 1
        (saida / 'html' / f'{num:02d}_{sig}.html').write_text(
            html_book(num, sig, nome, kind, verses), encoding='utf-8')
        rel['livros'][f'{num:02d}_{sig}'] = {'nome': nome, 'versiculos': nv, 'palavras': nw}
        print(f'{num:02d} {sig:4s} {nome:20s} {nv:5d} versículos  {nw:6d} palavras')
    rel['alertas'] = dict(rel['alertas'])
    (saida / 'relatorio.json').write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.livro:
        li = ''.join(f'<li><a href="html/{k}.html">{esc(v["nome"])}</a> '
                     f'<small style="color:var(--mut)">({v["palavras"]} palavras)</small></li>'
                     for k, v in rel['livros'].items())
        (saida / 'index.html').write_text(
            f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Bíblia interlinear</title>'
            f'<style>{CSS}</style><h1>Bíblia — 66 livros<small>original + transliteração</small></h1>'
            f'<ul>{li}</ul>', encoding='utf-8')
    return rel


# =====================================================================
# 6. TESTES UNITÁRIOS
# =====================================================================
TESTES_HEBR = [
    ('בְּ/רֵאשִׁית', None, 'bə-rēʾšît'), ('בָּרָא', None, 'bārāʾ'),
    ('אֱלֹהִים', None, 'ʾĕlōhîm'), ('אֵת', None, 'ʾēt'),
    ('הַ/שָּׁמַיִם', None, 'ha-ššāmayim'), ('וְ/אֵת', None, 'wə-ʾēt'),
    ('הָ/אָרֶץ', None, 'hā-ʾāreṣ'), ('שָׁלוֹם', None, 'šālôm'),
    ('רוּחַ', None, 'rûaḥ'), ('מֹשֶׁה', None, 'mōšeh'), ('תּוֹרָה', None, 'tôrâ'),
    ('יְהוָה', None, 'yəhwâ'), ('וַ/יֹּאמֶר', None, 'wa-yyōʾmer'),
    ('מֶלֶךְ', None, 'melekh'), ('דָּבָר', None, 'dāvār'), ('כָּל', 3605, 'kol'),
    ('שָׁמַע', None, 'šāmaʿ'), ('שָׁמֵעַ', None, 'šāmēaʿ'), ('בֵּית', None, 'bêt'),
    ('אָדָם', None, 'ʾādām'), ('מִצְוֹת', None, 'miṣwōt'), ('אַתָּה', None, 'ʾattâ'),
    ('לֹא', None, 'lōʾ'), ('קוֹל', None, 'qôl'), ('בָּנִים', None, 'bānîm'),
    ('בְּנֵי', None, 'bənê'), ('חָכְמָה', 2451, 'ḥokhmâ', 'HNcfsa'), ('יִשְׂרָאֵל', None, 'yiśrāʾēl'),
    ('וַ/יְהִי', None, 'wa-yhî'), ('מִזְבֵּחַ', None, 'mizbēaḥ'),
    # com morfologia (qamets qatan x gadol)
    ('שָׁמְעוֹ', 8085, 'šomʿô', 'HVqc/Sp3ms'), ('קָרְבָּן', 7133, 'qorbān', 'HNcmsa'),
    ('יָדְךָ', 3027, 'yādəkhā', 'HNcfsc/Sp2ms'), ('וְ/אָמְרוּ', 559, 'wə-ʾāmərû', 'HC/Vqp3cp'),
    ('מָרְדֳּכַי', 4782, 'mordŏkhay', 'HNp'), ('הָ/רְבִיעִי', 7243, 'hā-rəvîʿî', 'HTd/Aoamsa'),
    ('נָתְנוּ', 5414, 'nātənû', 'HVqp3cp'), ('מָשְׁזָר', 7806, 'mošzār', 'HVHsmsa'),
    # Jerusalém (hiriq do yod omitido), Issacar (ש muda), Rt 3:5 não, sufixo -î sem hífen solto
    ('יְרוּשָׁלִַם', 3389, 'yərûšālayim'), ('יִשָּׂשכָר', 3485, 'yiśśākhār'),
    ('רֹעִ/י', 7462, 'rōʿî'), ('בְּשָׂרִ/י', 1320, 'bəśārî'),
    ('וַ/יֹּאמְרוּ', 559, 'wa-yyōʾmərû'), ('תֹּאמְרִי', 559, 'tōʾmərî'), ('ל/וֹ', 3808, 'lô'),
    ('אָמְנָם', 551, 'ʾomnām', 'HD'),
]
TESTES_GRC = [
    ('Ἐν', 'En'), ('ἀρχῇ', 'arkhē̂ᵢ'), ('λόγος', 'lógos'), ('θεός', 'theós'),
    ('Ἰησοῦς', 'Iēsoûs'), ('ὁ', 'ho'), ('καὶ', 'kaì'), ('ἄγγελος', 'ángelos'),
    ('ῥῆμα', 'rhē̂ma'), ('Χριστός', 'Khristós'), ('εὐαγγέλιον', 'euangélion'),
    ('υἱός', 'huiós'), ('Ἑβραῖος', 'Hebraîos'), ('δι’', 'di’'), ('πνεῦμα', 'pneûma'),
    ('ἅγιος', 'hágios'), ('ψυχή', 'psykhḗ'), ('ἀγάπη', 'agápē'),
]


def testes():
    ok = True
    for t in TESTES_HEBR:
        w, st, esp = t[:3]
        got, _ = translit_hebr(w, st, t[3] if len(t) > 3 else None)
        if unicodedata.normalize('NFC', got) != unicodedata.normalize('NFC', esp):
            ok = False
            print(f'  ✗ hebraico {w}: obtido {got!r}, esperado {esp!r}')
    for w, esp in TESTES_GRC:
        got = translit_grc(w)
        if got != unicodedata.normalize('NFC', esp):
            ok = False
            print(f'  ✗ grego {w}: obtido {got!r}, esperado {esp!r}')
    print(f'testes: {len(TESTES_HEBR)} hebraico + {len(TESTES_GRC)} grego —', 'OK' if ok else 'FALHAS')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dados', default=str(Path(__file__).resolve().parent / 'dados_biblia'))
    ap.add_argument('--saida', default=str(Path(__file__).resolve().parent / 'dados_biblia' / 'saida'))
    ap.add_argument('--livro')
    ap.add_argument('--teste', action='store_true')
    args = ap.parse_args()
    if not testes():
        sys.exit(2)
    if args.teste:
        return
    run(args)


if __name__ == '__main__':
    main()
