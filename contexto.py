#!/usr/bin/env python3
"""
contexto.py — escolha do sentido da glosa pelo CONTEXTO, só entre sentidos do dicionário.

As regras ficam em dados_biblia/lexico/contexto.tsv (auditável), uma por linha:
    lang <TAB> chave <TAB> condições <TAB> glosa <TAB> classe <TAB> motivo
  lang    H (hebraico/aramaico) ou G (grego)
  chave   H: número Strong do radical ('1980' vale para '1980', '1980 a'...); G: lema grego
  condições  cláusulas separadas por ';' — todas precisam valer. campo=v1|v2  /  campo!=v  /  vazio = sempre
  glosa   texto em português.  Prefixo '=' = substitui a palavra inteira (inclusive prefixos hebraicos).
          Sufixo '~' = já está flexionada (não acrescenta "(pl)").
          Se termina em '-de' e há sufixo pronominal: 'diante-de' + sufixo -> 'diante-dele'.
  classe  A = a forma gramatical (caso, tema verbal, gênero, número) já decide o sentido no dicionário
          B = escolha pelo contexto entre os sentidos listados no dicionário
          C = locução de duas ou mais palavras (idiomatismo)
A 1ª regra que casar, na ordem do arquivo, vence.

Campos de condição (hebraico): stem vt ps g n st pos pref prefs suf prev next next2 near nearprev nextpref nextpos book
Campos de condição (grego):    cmp(=1 se há comparativo nas 4 palavras anteriores) pos pe te vo mo ca nu ge form prev next next2 near nearprev nextca prevca nextpos prevpos punct book
  prev/next/near = número Strong (hebraico) ou lema (grego) das palavras vizinhas no mesmo versículo.
"""
import re
from pathlib import Path

REGRAS = {'H': {}, 'G': {}}
USADAS = {}


def _cond(txt):
    out = []
    for cl in [c.strip() for c in txt.split(';') if c.strip()]:
        m = re.match(r'^(\w+)(!?=)(.*)$', cl)
        if not m:
            raise ValueError('condição inválida: ' + cl)
        campo, op, val = m.groups()
        out.append((campo, op == '!=', [val] if campo == 'form' else val.split('|')))
    return out


def carregar(dados):
    REGRAS['H'].clear(); REGRAS['G'].clear(); USADAS.clear()
    p = Path(dados) / 'lexico' / 'contexto.tsv'
    if not p.exists():
        return 0
    n = 0
    for ln, linha in enumerate(open(p, encoding='utf-8'), 1):
        linha = linha.rstrip('\n')
        if not linha.strip() or linha.startswith('#'):
            continue
        c = linha.split('\t')
        if len(c) != 6:
            raise ValueError(f'contexto.tsv linha {ln}: esperava 6 colunas, achei {len(c)}')
        lang, chave, cond, gloss, cls, why = c
        if lang not in 'HG' or cls not in ('A', 'B', 'C'):
            raise ValueError(f'contexto.tsv linha {ln}: lang/classe inválidos')
        REGRAS[lang].setdefault(chave.strip(), []).append({'cond': _cond(cond), 'gloss': gloss.strip(), 'cls': cls, 'why': why.strip(), 'ln': ln})
        n += 1
    return n


def _casa(feat, cond):
    for campo, neg, vals in cond:
        v = feat.get(campo)
        if campo == 'form':
            ok = any(re.search(x, v or '') for x in vals)
        elif campo == 'book':
            ok = any(_dentro(v, x) for x in vals)
        elif campo in ('near', 'nearprev', 'nearprev3'):
            ok = bool(set(vals) & set(v or ()))
        elif campo == 'prefs':
            ok = (v or '') in vals
        elif campo == 'pref':
            ok = any(x in (v or '') for x in vals)
        else:
            ok = (str(v) if v is not None else '') in vals
        if ok == neg:
            return False
    return True


def _dentro(book, rng):
    if book is None:
        return False
    if '-' in rng:
        a, b = rng.split('-'); return int(a) <= book <= int(b)
    return book == int(rng)


def aplicar(lang, chave, feat):
    """devolve a regra que casar (dict) ou None"""
    base = re.match(r'\S+', chave).group()
    for k in (chave, base):
        for r in REGRAS[lang].get(k, ()):
            if _casa(feat, r['cond']):
                USADAS[r['ln']] = USADAS.get(r['ln'], 0) + 1
                return r
    return None


# ---------------------------------------------------------------------------------------------
# características de contexto
# ---------------------------------------------------------------------------------------------
SEP_G = ',.;·'


def info_hebr(rec):
    """extrai (num, prefixos, morfema do radical) de um registro hebraico"""
    lem = rec.get('lemma') or ''
    mor = rec.get('morph') or ''
    if not lem or not rec.get('lido', True):
        return None
    lp = lem.split('/'); mp = mor[1:].split('/')
    prefs, num, si = [], '', None
    for i, p in enumerate(lp):
        if re.match(r'^\d', p):
            num = re.match(r'\d+', p).group(); si = i
        else:
            prefs.append(p)
    sm = mp[si] if si is not None and si < len(mp) else ''
    return {'num': num, 'prefs': ''.join(prefs), 'sm': sm, 'suf': any(m[:1] == 'S' for m in mp[len(lp):])}


def feats_hebr(words, i, book):
    """words: registros do versículo; i: posição"""
    me = info_hebr(words[i])
    if me is None:
        return {}
    inf = [info_hebr(w) for w in words]
    def n(j):
        return inf[j]['num'] if 0 <= j < len(inf) and inf[j] else ''
    sm = me['sm']
    f = {'book': book, 'pref': me['prefs'], 'prefs': ''.join(sorted(me['prefs'])), 'suf': '1' if me['suf'] else '',
         'prev': n(i - 1), 'next': n(i + 1), 'next2': n(i + 2),
         'near': [n(j) for j in range(i + 1, i + 5)], 'nearprev': [n(j) for j in range(i - 4, i)],
         'nextpref': inf[i + 1]['prefs'] if i + 1 < len(inf) and inf[i + 1] else '',
         'nextpos': (inf[i + 1]['sm'][:1] if i + 1 < len(inf) and inf[i + 1] else ''),
         'prevpos': (inf[i - 1]['sm'][:1] if i > 0 and inf[i - 1] else ''),
         'pos': sm[:1]}
    if sm[:1] == 'V':
        f['stem'] = sm[1:2]; f['vt'] = sm[2:3]
        if sm[2:3] in 'rs':
            f['g'], f['n'], f['st'] = sm[3:4], sm[4:5], sm[5:6]
        else:
            f['ps'], f['g'], f['n'] = sm[3:4], sm[4:5], sm[5:6]
    elif sm[:1] in 'NA':
        f['g'], f['n'], f['st'] = sm[2:3], sm[3:4], sm[4:5]
    elif sm[:1] == 'P':
        f['ps'], f['g'], f['n'] = sm[2:3], sm[3:4], sm[4:5]
    return f


def feats_grego(words, i, book):
    r = words[i]
    pe, te, vo, mo, ca, nu, ge, gr = r['parse'] if len(r['parse']) == 8 else ('-',) * 8
    def w(j):
        return words[j] if 0 <= j < len(words) else None
    def lem(j):
        x = w(j); return x['lemma'] if x else ''
    nx, pv = w(i + 1), w(i - 1)
    texto_prev = (pv.get('texto') or pv.get('orig') or '') if pv else ''
    return {'book': book, 'pos': r['pos'], 'pe': pe, 'te': te, 'vo': vo, 'mo': mo, 'ca': ca, 'nu': nu, 'ge': ge,
            'form': r.get('norm') or '', 'prev': lem(i - 1), 'next': lem(i + 1), 'next2': lem(i + 2),
            'near': [lem(j) for j in range(i + 1, i + 6)], 'nearprev': [lem(j) for j in range(i - 5, i)],
            'nearprev3': [lem(j) for j in range(i - 3, i)],
            'nextca': nx['parse'][4] if nx and len(nx['parse']) == 8 else '', 'prevca': pv['parse'][4] if pv and len(pv['parse']) == 8 else '',
            'nextpos': nx['pos'] if nx else '', 'prevpos': pv['pos'] if pv else '',
            'cmp': '1' if any((w(j) and ((len(w(j)['parse']) == 8 and w(j)['parse'][7] == 'C') or w(j)['lemma'] == 'μᾶλλον')) for j in range(i - 4, i)) else '',
            'punct': '1' if (pv is None or (texto_prev and texto_prev[-1] in SEP_G)) else ''}
