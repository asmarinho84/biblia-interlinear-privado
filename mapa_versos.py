"""Mapa de versículos: referência do texto original (hebraico WLC / grego SBLGNT) -> versículos da ARC (numeração em português/inglesa).
Fonte do mapa: STEPBible TVTMS (CC BY 4.0), colunas 'English KJV' e 'Hebrew'. Onde o mapa não fecha, não se mostra texto (nunca texto errado)."""
import re, glob, json, collections
from pathlib import Path
ABR = {'Gen':1,'Exo':2,'Lev':3,'Num':4,'Deu':5,'Jos':6,'Jdg':7,'Rut':8,'1Sa':9,'2Sa':10,'1Ki':11,'2Ki':12,'1Ch':13,'2Ch':14,'Ezr':15,'Neh':16,'Est':17,'Job':18,'Psa':19,'Pro':20,'Ecc':21,'Sng':22,'Isa':23,'Jer':24,'Lam':25,'Ezk':26,'Dan':27,'Hos':28,'Jol':29,'Amo':30,'Oba':31,'Jon':32,'Mic':33,'Nam':34,'Hab':35,'Zep':36,'Hag':37,'Zec':38,'Mal':39}
REF = re.compile(r'^(\w{3}|\d\w\w|\d\w\w)\.(\d+):(\d+|Title)(?:\.\w+)?(?:-(?:(\d+):)?(\d+))?')

def _ref(s):
    m = REF.match(s.strip())
    if not m: return None
    b, c, v, c2, v2 = m.groups()
    if b not in ABR or v == 'Title': return None
    c = int(c); v = int(v); v2 = int(v2) if v2 else v; c2 = int(c2) if c2 else c
    return ABR[b], c, v, c2, v2

def carregar_tvtms(path):
    L = open(path, encoding='utf-8-sig').read().split('\n')[161:]
    m = {}  # (livro,cap,ver hebraico) -> [(cap,ver) ARC]
    for ln in L:
        c = ln.split('\t')
        if c[0] not in ('OneToOne', 'SubdividedVerse', 'MergedPrevVerse', 'MergedVerse', 'StartDifferent') or len(c) < 3: continue
        e, h = _ref(c[1]), _ref(c[2])
        if not e or not h or e[0] != h[0]: continue
        he = [(h[1], v) for v in range(h[2], h[4] + 1)] if h[1] == h[3] else None
        en = [(e[1], v) for v in range(e[2], e[4] + 1)] if e[1] == e[3] else None
        if not he or not en: continue
        if len(he) == len(en): pares = [(a, [b]) for a, b in zip(he, en)]
        elif len(he) == 1: pares = [(he[0], en)]
        elif len(en) == 1: pares = [(a, en) for a in he]
        else: continue
        for a, bs in pares: m.setdefault((h[0],) + a, bs)
    return m


MANUAL = {}
for _v in range(1, 15): MANUAL[(11, 5, _v)] = [(4, 20 + _v)]       # 1Reis: hebr. 5:1-14 = ARC 4:21-34
for _v in range(15, 33): MANUAL[(11, 5, _v)] = [(5, _v - 14)]      # hebr. 5:15-32 = ARC 5:1-18
for _v in range(1, 68): MANUAL[(16, 7, _v)] = [(7, _v)]           # Neemias 7: hebr. 7:68-72 = ARC 7:69-73
for _v in range(68, 73): MANUAL[(16, 7, _v)] = [(7, _v + 1)]
for _v in range(1, 4): MANUAL[(13, 12, _v)] = [(12, _v)]          # 1Crônicas 12: hebr. 12:4-5 = ARC 12:4
MANUAL[(13, 12, 4)] = [(12, 4)]; MANUAL[(13, 12, 5)] = [(12, 4)]
for _v in range(6, 42): MANUAL[(13, 12, _v)] = [(12, _v - 1)]

# 1Reis 22: a ARC 1911 segue a numeração hebraica (53 versículos; o 54 hebraico foi unido ao 53)
for _v in range(1, 54): MANUAL[(11, 22, _v)] = [(22, _v)]
MANUAL[(11, 22, 54)] = [(22, 53)]


def construir(tvtms_path, arc):
    """devolve dict (livro,cap,ver original) -> lista de (cap,ver) ARC. Ausente = sem correspondência segura (mostrar —)."""
    m = carregar_tvtms(tvtms_path)
    m.update(MANUAL)
    caps_map = {(b, c) for (b, c, v), t in m.items() if t != [(c, v)]}
    return m, caps_map


def alvo(m, caps_map, livro, cap, ver, arc):
    """lista de (cap,ver) ARC ou None"""
    if livro > 39:                                   # NT: mesma numeração; versículo pode faltar em um dos lados
        alv = [(cap, ver)]
    elif (livro, cap, ver) in m:
        alv = m[(livro, cap, ver)]
    elif (livro, cap) in caps_map:                   # capítulo remapeado, versículo sem par (ex.: título de salmo)
        return None
    else:
        alv = [(cap, ver)]
    ch = arc[livro - 1]['chapters']
    for c, v in alv:
        if c - 1 >= len(ch) or v - 1 >= len(ch[c - 1]): return None
    return alv


def alinhar_janelas(m, contagem_orig, arc, livro):
    """Livros do AT (exceto Salmos): onde a contagem de versículos por capítulo difere, as duas numerações são só
    deslocamentos de ordem (nenhum versículo é omitido), então alinha-se por posição dentro da janela de capítulos
    consecutivos cujas somas se igualam. Sobrescreve m para esses capítulos."""
    ch = arc[livro - 1]['chapters']
    Lh = contagem_orig; Le = [len(c) for c in ch]
    n = max(len(Lh), len(Le)); i = 0; jan = []
    get = lambda L, k: L[k] if k < len(L) else 0
    while i < n:
        if get(Lh, i) == get(Le, i): i += 1; continue
        j = i; sh = se = 0
        while j < n:
            sh += get(Lh, j); se += get(Le, j); j += 1
            if sh == se: break
        if sh != se: return jan, False
        H = [(c + 1, v) for c in range(i, j) for v in range(1, get(Lh, c) + 1)]
        E = [(c + 1, v) for c in range(i, j) for v in range(1, get(Le, c) + 1)]
        for h, e in zip(H, E): m[(livro,) + h] = [e]
        jan.append((i + 1, j)); i = j
    return jan, True


def textos_arc(m, caps_map, arc, livro, verses, com_alvos=False):
    """verses: [(cap, ver, palavras)] do original. Devolve ({(cap,ver): texto ARC}, nº de versículos sem correspondência)."""
    if livro <= 39 and livro != 19:
        Lh = collections.defaultdict(int)
        for c, v, _ in verses: Lh[c] = max(Lh[c], v)
        L = [Lh[c] for c in range(1, max(Lh) + 1)] if Lh else []
        m = dict(m); caps_map = set(caps_map)
        alinhar_janelas(m, L, arc, livro)
        caps_map |= {(livro, c) for (b, c, v), t in m.items() if b == livro and t != [(c, v)]}
    if livro <= 39:        # capítulo com o mesmo nº de versículos nas duas numerações: correspondência direta
        Lh = collections.defaultdict(int)
        for c, v, _ in verses: Lh[c] = max(Lh[c], v)
        m = dict(m); caps_map = set(caps_map)
        for c, n in Lh.items():
            if c <= len(arc[livro - 1]['chapters']) and len(arc[livro - 1]['chapters'][c - 1]) == n and (livro, c) not in {(b, cc) for (b, cc, v) in MANUAL}:
                caps_map.discard((livro, c))
                for v in range(1, n + 1): m.pop((livro, c, v), None)
    ch = arc[livro - 1]['chapters']
    out, sem, alvos = {}, 0, {}
    for c, v, _ in verses:
        a = alvo(m, caps_map, livro, c, v, arc)
        if not a: sem += 1; continue
        alvos[(c, v)] = a
        txt = ' '.join(ch[cc - 1][vv - 1].strip() for cc, vv in a)
        out[(c, v)] = re.sub(r' ([,.;:!?])', r'\1', txt)
    return (out, sem, alvos) if com_alvos else (out, sem)
