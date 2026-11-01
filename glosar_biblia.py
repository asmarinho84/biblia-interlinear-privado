#!/usr/bin/env python3
"""
glosar_biblia.py — acrescenta ao interlinear a linha de GLOSA EM PORTUGUÊS (feita só a partir dos
dicionários) e a linha MORFOLÓGICA, palavra sob palavra.

Entrada : dados_biblia/saida/jsonl/NN_Sigla.jsonl   (gerado por converter_biblia.py)
          dados_biblia/lexico/hebraico_pt.json, grego_pt.json   (gerados por aplicar_traducoes.py)
Saída   : os mesmos .jsonl ganham os campos  gl (glosa curta), gl_full (todos os sentidos), mf (morfologia)
          dados_biblia/saida/html/NN_Sigla.html  regenerados com 4 linhas por palavra:
              original / transliteração / glosa PT / morfologia
          dados_biblia/saida/index.html, relatorio_glosa.json

Princípios
  * A glosa é o 1º sentido do dicionário, em forma de lema (verbo no infinitivo, substantivo no
    singular). Número, gênero, pessoa, tempo etc. ficam na linha morfológica; plural/dual de
    substantivos e adjetivos também é marcado na glosa como (pl)/(du).
  * Hebraico: prefixos (e, o/a, em, como, para, de, que) e sufixos pronominais são glosados
    morfema por morfema e ligados por hífen: "e-o-céu(pl)", "semente-dele", "criar-o".
  * Nenhuma tradução bíblica é usada. A glosa do artigo é a única forma "flexionada"
    (o/a/os/as), porque o artigo é palavra funcional.
"""
import argparse
import collections
import glob
import json
import re
import sys
from pathlib import Path

import converter_biblia as C
import contexto as CT
import mapa_versos as MV

# ---------------------------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------------------------


def primeiro_sentido(pt):
    """1º sentido da glosa (corta na 1ª vírgula/ponto-e-vírgula fora de parênteses e colchetes)."""
    nivel = 0
    for i, c in enumerate(pt):
        if c in '([':
            nivel += 1
        elif c in ')]':
            nivel -= 1
        elif c in ',;' and nivel == 0:
            return pt[:i].strip()
    return pt.strip()


ARTIGO_INICIAL = re.compile(r'^(?:um|uma|uns|umas|o|a|os|as)\s+(?=\S)', re.I)
MANTER_ARTIGO = {'o quê?', 'o que?'}
AJUSTES = {}
IRREG_PP = {'fazer': 'feito', 'dizer': 'dito', 'abrir': 'aberto', 'escrever': 'escrito', 'pôr': 'posto',
            'ver': 'visto', 'cobrir': 'coberto', 'vir': 'vindo', 'ganhar': 'ganho', 'gastar': 'gasto',
            'aceitar': 'aceito', 'prender': 'preso', 'entregar': 'entregue', 'pagar': 'pago', 'ter': 'tido'}


def particip_passado(inf):
    """infinitivo → particípio passado ('abençoar' → 'abençoado'); None se não for verbo simples regular."""
    if not re.fullmatch(r'[a-zçãõáéíóúâêôà]+', inf or ''):
        return None
    if inf in IRREG_PP:
        return IRREG_PP[inf]
    if inf.endswith('ar'):
        return inf[:-2] + 'ado'
    if inf.endswith('er') or inf.endswith('ir'):
        return inf[:-2] + 'ido'
    return None


CST_SEM_DE = {'3605'}    # 'todo' em construto não leva '-de'
SEM_PLURAL = {'430', '410', '113', '136'}   # 'Deus'/'Senhor' no plural de majestade: sem marca (pl)


def carregar_ajustes(dados):
    AJUSTES.clear()
    p = Path(dados) / 'lexico' / 'ajustes_exibicao.tsv'
    if p.exists():
        for ln in open(p, encoding='utf-8'):
            ln = ln.rstrip('\n')
            if ln and not ln.startswith('#'):
                lang, chave, texto = ln.split('\t')
                AJUSTES[(lang, chave)] = texto


def exibir(lang, chave, pt):
    """glosa curta de exibição: ajuste curado (se houver) ou 1º sentido sem artigo inicial."""
    if (lang, chave) in AJUSTES:
        return AJUSTES[(lang, chave)]
    s = primeiro_sentido(pt)
    if s not in MANTER_ARTIGO and not s.startswith('['):
        t = ARTIGO_INICIAL.sub('', s)
        if len(t) >= 2:
            s = t
    return s


def artigo(g, n):
    """g: m/f/b/c/n ; n: s/p/d"""
    if g in ('b',):
        return 'os/as' if n in ('p', 'd') else 'o/a'
    if n in ('p', 'd'):
        return 'as' if g == 'f' else 'os'
    return 'a' if g == 'f' else 'o'


CONTRACAO = {  # prefixo + artigo
    'b': {'o': 'no', 'a': 'na', 'os': 'nos', 'as': 'nas'},
    'l': {'o': 'ao', 'a': 'à', 'os': 'aos', 'as': 'às'},
    'm': {'o': 'do', 'a': 'da', 'os': 'dos', 'as': 'das'},
    'k': {'o': 'como o', 'a': 'como a', 'os': 'como os', 'as': 'como as'},
}
PREFIXO = {'c': 'e', 'b': 'em', 'k': 'como', 'l': 'para', 'm': 'de', 's': 'que', 'i': 'acaso'}

# sufixos pronominais  (pessoa+gênero+número)
SUF_POSS = {'1cs': 'de-mim', '2ms': 'de-ti', '2fs': 'de-ti(f)', '3ms': 'dele', '3fs': 'dela', '1cp': 'de-nós',
            '2mp': 'de-vós', '2fp': 'de-vós(f)', '3mp': 'deles', '3fp': 'delas', '3cs': 'dele',
            '3cp': 'deles', '2cs': 'de-ti', '2cp': 'de-vós', '3bs': 'dele', '3bp': 'deles'}
SUF_OBJ = {'1cs': 'me', '2ms': 'te', '2fs': 'te(f)', '3ms': 'o', '3fs': 'a', '1cp': 'nos',
           '2mp': 'vos', '2fp': 'vos(f)', '3mp': 'os', '3fp': 'as', '3cs': 'o', '3cp': 'os',
           '2cs': 'te', '2cp': 'vos', '3bs': 'o', '3bp': 'os'}
SUF_PRON = {'1cs': 'mim', '2ms': 'ti', '2fs': 'ti(f)', '3ms': 'ele', '3fs': 'ela', '1cp': 'nós',
            '2mp': 'vós', '2fp': 'vós(f)', '3mp': 'eles', '3fp': 'elas', '3cs': 'ele', '3cp': 'eles',
            '2cs': 'ti', '2cp': 'vós', '3bs': 'ele', '3bp': 'eles'}

# ---------------------------------------------------------------------------------------------
# morfologia hebraica (OSHB)
# ---------------------------------------------------------------------------------------------
H_STEM = {'q': 'Qal', 'N': 'Nifal', 'p': 'Piel', 'P': 'Pual', 'h': 'Hifil', 'H': 'Hofal', 't': 'Hitpael',
          'o': 'Polel', 'O': 'Polal', 'r': 'Hitpolel', 'm': 'Poel', 'M': 'Poal', 'k': 'Palel', 'K': 'Pulal',
          'Q': 'Qal pas.', 'l': 'Pilpel', 'L': 'Polpal', 'f': 'Hitpalpel', 'D': 'Nitpael', 'j': 'Pealal',
          'i': 'Pilel', 'u': 'Hotpaal', 'c': 'Hitpalel', 'v': 'Nitpolel', 'w': 'Hotpaal', 'y': 'Tifil',
          'z': 'Hishtafel'}
A_STEM = {'q': 'Peal', 'Q': 'Peil', 'u': 'Hitpeel', 'p': 'Pael', 'P': 'Itpaal', 'M': 'Hitpaal', 'a': 'Afel',
          'h': 'Hafel', 's': 'Safel', 'e': 'Xafel', 'H': 'Hofal', 'i': 'Itpeal', 't': 'Hishtafel',
          'v': 'Ishtafel', 'w': 'Hitafel', 'o': 'Polel', 'z': 'Itpoel', 'r': 'Hitpolel', 'f': 'Hitpalpel',
          'b': 'Hefal', 'c': 'Hitpaal', 'm': 'Pamel', 'N': 'Nifal'}
H_TIPO = {'p': 'perf', 'q': 'perf seq', 'i': 'imperf', 'w': 'wayyiqtol', 'h': 'coortativo', 'j': 'jussivo',
          'v': 'imperativo', 'r': 'part at', 's': 'part pas', 'a': 'inf abs', 'c': 'inf cst'}
GEN = {'m': 'm', 'f': 'f', 'b': 'm/f', 'c': 'c', 'x': ''}
NUM = {'s': 'sg', 'p': 'pl', 'd': 'du', 'x': ''}
EST = {'a': 'abs', 'c': 'cst', 'd': 'det'}
H_PRON = {'p': 'pess', 'd': 'dem', 'f': 'indef', 'i': 'interr', 'r': 'rel'}
H_PART = {'a': 'afirm', 'd': 'art', 'e': 'excl', 'i': 'interr', 'j': 'interj', 'm': 'dem', 'n': 'neg',
          'o': 'obj', 'r': 'rel'}


def _gn(g='', n='', e=''):
    return ' '.join(x for x in (GEN.get(g, g), NUM.get(n, n), EST.get(e, e)) if x)


def morf_hebr(cod, aramaico=False):
    """cod: morfema OSHB sem a letra de língua, p.ex. 'Vqp3ms', 'Ncfsa'."""
    if not cod:
        return ''
    p = cod[0]
    r = cod[1:]
    try:
        if p == 'N':
            sub = {'c': 'Subst', 'g': 'Subst gent', 'p': 'Nome próprio'}.get(r[:1], 'Subst')
            return (sub + ' ' + _gn(*r[1:4])).strip()
        if p == 'A':
            sub = {'a': 'Adj', 'c': 'Num card', 'g': 'Adj gent', 'o': 'Num ord'}.get(r[:1], 'Adj')
            return (sub + ' ' + _gn(*r[1:4])).strip()
        if p == 'V':
            stem = (A_STEM if aramaico else H_STEM).get(r[0], 'tema:' + r[0])
            tipo = H_TIPO.get(r[1], r[1])
            if r[1] in 'rs':
                return f'V {stem} {tipo} ' + _gn(*r[2:5])
            if r[1] in 'ac':
                return f'V {stem} {tipo}'
            pess, g, n = r[2], r[3], r[4]
            return f'V {stem} {tipo} {pess}{"" if g in "x" else g}{n}'.strip()
        if p == 'P':
            sub = H_PRON.get(r[:1], '')
            q = r[1:]
            pess = q[0] if q and q[0] in '123' else ''
            resto = q[1:] if pess else q[1:] if q[:1] == 'x' else q
            g = resto[0] if len(resto) > 0 else ''
            n = resto[1] if len(resto) > 1 else ''
            return f'Pron {sub} {pess}{"" if g == "x" else g}{n}'.replace('  ', ' ').strip()
        if p == 'R':
            return 'Prep'
        if p == 'C':
            return 'Conj'
        if p == 'D':
            return 'Adv'
        if p == 'T':
            return 'Part ' + H_PART.get(r[:1], r)
        if p == 'S':
            if r[:1] == 'p':
                return 'suf ' + r[1:]
            return {'d': 'suf direc', 'h': 'suf parag', 'n': 'suf parag'}.get(r[:1], 'suf ' + r)
    except IndexError:
        pass
    return cod


# ---------------------------------------------------------------------------------------------
# glosa hebraica
# ---------------------------------------------------------------------------------------------

def chave_lema(parte):
    return parte.replace('+', '').strip()


def glosa_hebr(rec, lex, alertas, feat=None):
    lem = rec.get('lemma') or ''
    mor = (rec.get('morph') or '')
    if not lem or not rec.get('lido', True):
        return '', '', '', None
    aram = mor[:1] == 'A'
    mparts = mor[1:].split('/')
    lparts = lem.split('/')
    prefs, stem_i, stem_key = [], None, None
    for i, p in enumerate(lparts):
        if re.match(r'^\d', p):
            stem_i, stem_key = i, chave_lema(p)
        else:
            prefs.append(p)
    stem_m = mparts[stem_i] if stem_i is not None and stem_i < len(mparts) else ''
    # sufixos = morfemas depois das partes do lema
    sufs = [m for m in mparts[len(lparts):] if m[:1] == 'S']
    # glosa do radical
    full = ''
    core = ''
    ctx = None
    sem_pl = False
    absorve = False
    if stem_key is not None:
        ent = lex.get(stem_key)
        if ent is None:
            alertas['sem_lexico'] += 1
            alertas['_ex_sem_lexico'] = alertas.get('_ex_sem_lexico') or f'{rec["ref"]} {stem_key}'
            core, full = '?', '?'
        else:
            full = ent['pt']
            core = exibir('H', stem_key, full)
            regra = CT.aplicar('H', stem_key, feat) if feat else None
            if regra:
                g = regra['gloss']
                ctx = {'c': regra['cls'], 'n': regra['why'], 'b': core}
                absorve = g.startswith('=')
                sem_pl = g.endswith('~') or absorve
                core = g.lstrip('=').rstrip('~')
            if ctx is None and stem_m[:1] == 'V' and ((stem_m[1:3] == 'qs') or (stem_m[1:2] in 'PH' and stem_m[2:3] == 'r')):
                pp = particip_passado(core)
                if pp:
                    ctx = {'c': 'A', 'n': 'Particípio passivo: forma de particípio passado em português.', 'b': core}
                    core = pp
            if stem_m[:1] in ('N', 'A') or stem_m[:2] in ('Vr', 'Vs') or (stem_m[:1] == 'V' and len(stem_m) > 2 and stem_m[2] in 'rs'):
                numero = None
                if stem_m[:1] == 'N':
                    numero = stem_m[3:4]
                elif stem_m[:1] == 'A':
                    numero = stem_m[3:4]
                else:
                    numero = stem_m[4:5]
                if stem_key in SEM_PLURAL or sem_pl:
                    pass
                elif numero == 'p':
                    core += '(pl)'
                elif numero == 'd':
                    core += '(du)'
    # prefixos
    pre = []
    i = 0
    g_art, n_art = 'm', 's'
    if stem_m[:1] in 'NA':
        g_art, n_art = stem_m[2:3] or 'm', stem_m[3:4] or 's'
    elif stem_m[:1] == 'V' and len(stem_m) > 4 and stem_m[2] in 'rs':
        g_art, n_art = stem_m[3:4] or 'm', stem_m[4:5] or 's'
    art = artigo(g_art, n_art)
    if absorve:
        prefs = [p for p in prefs if p == 'c']
    while i < len(prefs):
        p = prefs[i]
        if p == 'd':
            pre.append(art)
        elif p in CONTRACAO and i + 1 < len(prefs) and prefs[i + 1] == 'd':
            pre.append(CONTRACAO[p].get(art, PREFIXO[p] + '-' + art))
            i += 1
        else:
            pre.append(PREFIXO.get(p, '?' + p))
        i += 1
    # prefixo que é o próprio núcleo (preposição com sufixo, sem radical numérico)
    head_prefix = stem_key is None
    partes = list(pre)
    if core:
        partes.append(core)
    # sufixo pronominal
    suf_txt = ''
    for s in sufs:
        if s[:2] == 'Sp':
            cod = s[2:5]
            if head_prefix:
                suf_txt = SUF_PRON.get(cod, cod)
            elif stem_m[:1] == 'V' and not (len(stem_m) > 2 and stem_m[2] in 'rs'):
                suf_txt = SUF_OBJ.get(cod, cod)
            elif stem_m[:1] in ('N', 'A'):
                suf_txt = SUF_POSS.get(cod, cod)
            elif stem_m[:1] == 'V':      # particípio: construto = "pastor de mim"; absoluto = objeto
                suf_txt = (SUF_POSS if stem_m.endswith('c') else SUF_OBJ).get(cod, cod)
            else:
                suf_txt = SUF_PRON.get(cod, cod)
        elif s[:2] == 'Sd':
            suf_txt = suf_txt or 'rumo'
    if ctx and suf_txt and core.endswith(' de'):
        partes[-1] = core[:-3] + ' ' + suf_txt          # 'diante de' + 3ms -> 'diante dele'
    elif suf_txt:
        partes.append(suf_txt)
    elif (stem_key is not None and core and not core.endswith(' de') and chave_lema(stem_key).split()[0] not in CST_SEM_DE
          and ((stem_m[:2] == 'Nc' and stem_m[4:5] == 'c')
               or (stem_m[:1] == 'V' and stem_m[2:3] in ('r', 's') and stem_m[5:6] == 'c'))):
        partes[-1] = partes[-1] + '-de'                  # substantivo/particípio em construto: "palavra-de"
    gl = '-'.join(partes)
    # morfologia: radical (ou prefixo-núcleo) + sufixo
    if stem_i is not None:
        mf = morf_hebr(stem_m, aram)
    else:
        mf = morf_hebr(mparts[len(lparts) - 1], aram) if mparts else ''
    for s in sufs:
        mf += ' +' + morf_hebr(s, aram)
    if full and pre:
        full = ' + '.join([x for x in pre] + [full]) if len(pre) else full
    mf = mf.strip() or '[sem código na fonte]'
    return gl, full, mf, ctx


# ---------------------------------------------------------------------------------------------
# grego (MorphGNT)
# ---------------------------------------------------------------------------------------------
G_POS = {'N-': 'Subst', 'V-': 'V', 'RA': 'Art', 'RP': 'Pron pess', 'RD': 'Pron dem', 'RR': 'Pron rel',
         'RI': 'Pron interr/indef', 'A-': 'Adj', 'C-': 'Conj', 'D-': 'Adv', 'P-': 'Prep', 'X-': 'Part',
         'I-': 'Interj'}
G_TEMPO = {'P': 'Pres', 'I': 'Imperf', 'F': 'Fut', 'A': 'Aor', 'X': 'Perf', 'Y': 'Mais-q-perf'}
G_VOZ = {'A': 'At', 'M': 'Méd', 'P': 'Pas'}
G_MODO = {'I': 'Ind', 'D': 'Imp', 'S': 'Subj', 'O': 'Opt', 'N': 'Inf', 'P': 'Part'}
G_CASO = {'N': 'nom', 'G': 'gen', 'D': 'dat', 'A': 'acu', 'V': 'voc'}
G_NUM = {'S': 'sg', 'P': 'pl'}
G_GEN = {'M': 'm', 'F': 'f', 'N': 'n'}
G_GRAU = {'C': 'comp', 'S': 'sup'}


def morf_grego(pos, parse):
    base = G_POS.get(pos, pos)
    if len(parse) != 8:
        return base
    pe, te, vo, mo, ca, nu, ge, gr = parse
    t = []
    if pos == 'V-':
        t.append(G_TEMPO.get(te, ''))
        t.append(G_VOZ.get(vo, ''))
        t.append(G_MODO.get(mo, ''))
        if mo in 'IDSO' and pe != '-':
            t.append(pe + G_NUM.get(nu, ''))
        else:
            t += [G_CASO.get(ca, ''), G_NUM.get(nu, ''), G_GEN.get(ge, '')]
    else:
        if pe != '-':
            t.append(pe)
        t += [G_CASO.get(ca, ''), G_NUM.get(nu, ''), G_GEN.get(ge, ''), G_GRAU.get(gr, '')]
    return (base + ' ' + ' '.join(x for x in t if x)).strip()


def glosa_grego(rec, lex, alertas, feat=None):
    ent = lex.get(rec['lemma'])
    if ent is None:
        alertas['sem_lexico'] += 1
        alertas['_ex_sem_lexico'] = alertas.get('_ex_sem_lexico') or f'{rec["ref"]} {rec["lemma"]}'
        return '?', '?', morf_grego(rec['pos'], rec['parse']), None
    full = ent['pt']
    pe, te, vo, mo, ca, nu, ge, gr = rec['parse'] if len(rec['parse']) == 8 else ('-',) * 8
    ctx = None
    if rec['pos'] == 'RA':
        gl = artigo({'F': 'f'}.get(ge, 'm'), 's' if nu != 'P' else 'p')
    else:
        gl = exibir('G', rec['lemma'], full)
        regra = CT.aplicar('G', rec['lemma'], feat) if feat else None
        sem_pl = False
        if regra:
            g = regra['gloss']
            ctx = {'c': regra['cls'], 'n': regra['why'], 'b': gl}
            sem_pl = g.endswith('~')
            gl = g.rstrip('~')
        if nu == 'P' and not sem_pl and (rec['pos'] in ('N-', 'A-') or (rec['pos'] == 'V-' and mo == 'P')):
            gl += '(pl)'
    return gl, full, morf_grego(rec['pos'], rec['parse']), ctx


# ---------------------------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------------------------
CSS_EXTRA = """.arc{margin:.2em 0 1.1em;padding:.35em .6em;border-left:3px solid var(--mut,#888);font-size:.95em;line-height:1.5}.arc b{font-size:.75em;letter-spacing:.06em;margin-right:.4em;color:var(--mut,#888)}

.g{font-size:.92rem;color:var(--fg);font-weight:600;direction:ltr;unicode-bidi:isolate;white-space:nowrap;margin-top:.05rem}
.m{font-size:.7rem;color:var(--mut);direction:ltr;unicode-bidi:isolate;white-space:nowrap;margin-bottom:.15rem}
.w{padding:0 .15rem}
.x .g{border-bottom:2px dotted #c28a00}.xA .g{border-bottom-color:#3b7a3b}.xC .g{border-bottom-color:#7a4bb0}
details{margin:.6rem 0;font-size:.82rem;color:var(--mut)}summary{cursor:pointer}
"""

LEGENDA = (
    '<details><summary>Como ler</summary><p>Cada palavra é uma coluna com quatro linhas: '
    '<b>original</b> · <i>transliteração</i> · <b>glosa em português</b> (sentido do dicionário, em forma de lema; ver abaixo quando o contexto escolheu outro sentido) · '
    'morfologia. Glosas ligadas por hífen são morfemas da mesma palavra (e-o-céu, semente-dele). '
    '<code>(pl)</code>/<code>(du)</code> = plural/dual. Pessoa, gênero, número, tempo e demais traços estão na '
    'linha morfológica: <code>3ms</code> = 3ª pessoa masc. sing.; <code>sg/pl/du</code> = singular/plural/dual; '
    '<code>abs/cst/det</code> = estado absoluto/construto/determinado. Passe o cursor (ou toque) sobre a palavra para ver '
    'todos os sentidos do dicionário. As glosas vêm de dicionários (OpenScriptures HebrewLexicon e MorphGNT lexicon, '
    'traduzidos para o português), não de outra Bíblia.</p>'
    '<p><b>Sentido escolhido pelo contexto:</b> palavras com sublinhado pontilhado tiveram o sentido escolhido entre os do dicionário '
    'conforme o contexto (toque para ver o motivo): <b style="color:#3b7a3b">A</b> = a forma gramatical (tema verbal, caso, gênero, número) decide; '
    '<b style="color:#c28a00">B</b> = escolha pelo contexto entre os sentidos do dicionário; <b style="color:#7a4bb0">C</b> = locução de duas ou mais palavras. '
    'Substantivos hebraicos em construto levam “-de” (palavra-de); pronomes gregos seguem o caso (dele, a-ele).</p></details>')


def html_book_gl(num, sigla, nome, kind, verses, arc=None):
    arc = arc or {}
    rtl = kind == 'AT'
    direcao = 'rtl' if rtl else 'ltr'
    lang = 'he' if rtl else 'grc'
    sub = ('Texto hebraico/aramaico (WLC) — leitura da direita para a esquerda' if rtl
           else 'Texto grego (SBLGNT) — leitura da esquerda para a direita')
    out = [f'<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{C.esc(nome)} — interlinear</title><style>{C.CSS}{CSS_EXTRA}</style>'
           f'<p><a href="../index.html">← Índice</a> · <a href="../referencias.html">Referências</a> · <a href="../auditoria_sentidos.html">Auditoria de sentidos</a></p>'
           f'<h1>{C.esc(nome)}<small>{sub}</small></h1>{LEGENDA}']
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
            tip = []
            if w.get('ketiv'):
                cls += ' q'
                tip.append(f'ketiv: {w["ketiv"]}')
            if not w.get('lido', True):
                cls += ' nl'
            if not w.get('escrito', True):
                cls += ' qs'
                tip.append('lido (qere), mas não escrito no manuscrito')
            if w.get('gl_ctx'):
                cls += ' x x' + w['gl_ctx']['c']
                tip.append(f"[{w['gl_ctx']['c']}] {w['gl_ctx']['n']} (padrão do dicionário: {w['gl_ctx']['b']})")
            if w.get('gl_full'):
                tip.append(w['gl_full'])
            if rtl:
                o = w['orig'] + w['depois'] + w['par']
                t = w['translit'] or '∅'
                if w['depois']:
                    t += ''.join({'־': '-', '׃': '', ' ׀': ' |'}.get(c, '') for c in w['depois'])
            else:
                o = re.sub(r'[⸀-⸅⟦⟧]', '', w['texto'])
                t = w['translit']
            title = f' title="{C.esc(" · ".join(tip))}"' if tip else ''
            out.append(f'<span class="{cls}"{title}><span class="o">{C.esc(o)}</span>'
                       f'<span class="t">{C.esc(t)}</span>'
                       f'<span class="g">{C.esc(w.get("gl") or "—")}</span>'
                       f'<span class="m">{C.esc(w.get("mf") or "")}</span></span>')
        out.append('</div>')
        if arc is not None:
            t = arc.get((cap, ver))
            out.append(f'<p class="arc" dir="ltr" lang="pt-BR"><b>ARC</b> {C.esc(t) if t else "—"}</p>')
    out.append('</section>')
    return ''.join(out)


# ---------------------------------------------------------------------------------------------
# execução
# ---------------------------------------------------------------------------------------------

def carregar(path):
    return [json.loads(l) for l in open(path, encoding='utf-8')]


def agrupar(recs):
    verses, atual, chave = [], None, None
    for r in recs:
        k = (r['cap'], r['ver'])
        if k != chave:
            atual = []
            verses.append((r['cap'], r['ver'], atual))
            chave = k
        atual.append(r)
    return verses


def run(args):
    dados = Path(args.dados)
    saida = dados / 'saida'
    carregar_ajustes(dados)
    n_regras = CT.carregar(dados)
    por_classe = collections.Counter()
    por_livro = collections.defaultdict(collections.Counter)
    h_lex = json.load(open(dados / 'lexico' / 'hebraico_pt.json', encoding='utf-8'))
    g_lex = json.load(open(dados / 'lexico' / 'grego_pt.json', encoding='utf-8'))
    arc_json = dados / 'arc' / 'pt_arc1911.json'
    ARC = json.load(open(arc_json, encoding='utf-8-sig')) if arc_json.exists() else None
    if ARC:
        tv = next((dados / 'arc').glob('TVTMS*.txt'))
        MAPA, CAPS = MV.construir(str(tv), ARC)
    rel_arc = {}
    rel = {'livros': {}, 'sem_lexico': 0, 'sem_glosa': 0, 'exemplos': []}
    alertas = collections.Counter()
    nomes = {f'{i:02d}_{s}': (i, s, n, 'AT') for i, (o, s, n) in enumerate(C.AT, start=1)}
    nomes.update({f'{i:02d}_{s}': (i, s, n, 'NT') for i, (p, s, n) in enumerate(C.NT, start=40)})
    for jl in sorted(glob.glob(str(saida / 'jsonl' / '*.jsonl'))):
        base = Path(jl).stem
        num, sig, nome, kind = nomes[base]
        if args.livro and sig != args.livro:
            continue
        recs = carregar(jl)
        vazias = 0
        for cap, ver, words in agrupar(recs):
            for i, r in enumerate(words):
                if kind == 'AT':
                    feat = CT.feats_hebr(words, i, num)
                    gl, full, mf, ctx = glosa_hebr(r, h_lex, alertas, feat)
                    if not gl and r.get('lido', True):
                        vazias += 1
                else:
                    feat = CT.feats_grego(words, i, num)
                    gl, full, mf, ctx = glosa_grego(r, g_lex, alertas, feat)
                r['gl'], r['gl_full'], r['mf'] = gl, full, mf
                r.pop('gl_ctx', None)
                if ctx:
                    r['gl_ctx'] = ctx
                    por_classe[ctx['c']] += 1
                    por_livro[base][ctx['c']] += 1
        with open(jl, 'w', encoding='utf-8') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        arc_v = None
        if ARC:
            arc_v, sem_arc = MV.textos_arc(MAPA, CAPS, ARC, num, agrupar(recs))
            rel_arc[base] = {'versiculos': len(agrupar(recs)), 'sem_arc': sem_arc}
        (saida / 'html' / f'{base}.html').write_text(
            html_book_gl(num, sig, nome, kind, agrupar(recs), arc_v), encoding='utf-8')
        rel['livros'][base] = {'nome': nome, 'palavras': len(recs), 'sem_glosa': vazias}
        rel['sem_glosa'] += vazias
        print(f'{base:10s} {nome:18s} {len(recs):6d} palavras   sem glosa: {vazias}')
    rel['regras_contexto'] = {'total_regras': n_regras, 'aplicacoes_por_classe': dict(por_classe),
                              'regras_nunca_usadas': sorted(set(ln for rs in list(CT.REGRAS['H'].values()) + list(CT.REGRAS['G'].values()) for r_ in rs for ln in [r_['ln']]) - set(CT.USADAS)) if not args.livro else None}
    rel['arc'] = rel_arc
    rel['sem_lexico'] = alertas['sem_lexico']
    rel['exemplo_sem_lexico'] = alertas.get('_ex_sem_lexico')
    (saida / 'relatorio_glosa.json').write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.livro:
        import titulos_livros as TL
        T = TL.titulos()
        def _linha(k, v):
            lg, o, tr, pt = T[int(k.split('_')[0]) - 1]
            d, cl = ('rtl', 'hebraico') if lg == 'he' else ('ltr', 'grego')
            return (f'<li class="lv"><a href="html/{k}.html"><span class="lo" dir="{d}" lang="{"he" if lg == "he" else "el"}">{C.esc(o)}</span> '
                    f'<span class="lt">{C.esc(tr)}</span> <span class="lp">{C.esc(v["nome"])}</span></a> '
                    f'{"" if pt.split(" ",1)[-1] == v["nome"].split(" ",1)[-1] else "<small>“" + C.esc(pt) + "”</small> "}'
                    f'<small style="color:var(--mut)">{cl} · {v["palavras"]} palavras</small></li>')
        li = ''.join(_linha(k, v) for k, v in rel['livros'].items())
        (saida / 'index.html').write_text(
            f'<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Bíblia interlinear</title><style>{C.CSS}{CSS_EXTRA}.lv{{margin:.6em 0;list-style:none;break-inside:avoid}}ul{{columns:1!important}}.lv a{{display:flex;flex-wrap:wrap;gap:.1em .6em;align-items:baseline}}.lv .lo{{font-size:1.25em;margin-right:.4em}}.lv .lt{{font-style:italic;margin-right:.4em}}.lv .lp{{font-weight:bold}}</style>'
            f'<h1>Bíblia — 66 livros<small>original · transliteração · glosa em português (dicionário) · '
            f'morfologia</small></h1><p><a href="referencias.html"><b>📚 Referências e fontes</b></a> — lista de tudo que foi usado e como.</p><p><a href="auditoria_sentidos.html"><b>🔎 Sentidos escolhidos por contexto</b></a> — o que mudou, por quê e onde.</p>{LEGENDA}<ul style="padding-left:0">{li}</ul>', encoding='utf-8')
    import gerar_auditoria
    gerar_auditoria.main(dados)
    import gerar_referencias
    gerar_referencias.DADOS = dados
    gerar_referencias.main()
    print(f'\nsem léxico: {rel["sem_lexico"]}   sem glosa (palavras lidas): {rel["sem_glosa"]}')
    return rel


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dados', default=str(Path(__file__).resolve().parent / 'dados_biblia'))
    ap.add_argument('--livro')
    run(ap.parse_args())


if __name__ == '__main__':
    main()
