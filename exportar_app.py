"""exportar_app.py — gera dados_biblia/app/data/*.js (um arquivo por livro, carregável por <script>, funciona offline/file://)
e copia a interface do app (app_src/) para dados_biblia/app/. Reutiliza a mesma interlinear + linha ARC já validadas."""
import json, glob, re, shutil, sys
from pathlib import Path
import converter_biblia as C
import glosar_biblia as G
import mapa_versos as MV
import titulos_livros as TL

RAIZ = Path(__file__).resolve().parent
D = RAIZ / 'dados_biblia'
OUT = D / 'app'


def palavra(w, rtl):
    cls, tip = [], []
    if w.get('ketiv'): cls.append('q'); tip.append(f'ketiv: {w["ketiv"]}')
    if not w.get('lido', True): cls.append('nl')
    if not w.get('escrito', True): cls.append('qs'); tip.append('lido (qere), mas não escrito no manuscrito')
    ctx = w.get('gl_ctx')
    if ctx:
        cls.append('x' + ctx['c'])
        tip.append(f"[{ctx['c']}] {ctx['n']} (padrão do dicionário: {ctx['b']})")
    if rtl:
        o = w['orig'] + w['depois'] + w['par']
        t = w['translit'] or '∅'
        if w['depois']: t += ''.join({'־': '-', '׃': '', ' ׀': ' |'}.get(c, '') for c in w['depois'])
    else:
        o = re.sub(r'[⸀-⸅⟦⟧]', '', w['texto']); t = w['translit']
    # opções de tradução do dicionário (só quando há mais de uma)
    full = w.get('gl_full') or ''
    nivel, cortes = 0, []
    for i, ch in enumerate(full):
        if ch in '([': nivel += 1
        elif ch in ')]': nivel -= 1
        elif ch in ',;' and nivel == 0: cortes.append(i)
    return [o, t, w.get('gl') or '—', w.get('mf') or '', ' · '.join(tip), ' '.join(cls), full if cortes else '']


def main():
    arc = json.load(open(D / 'arc' / 'pt_arc1911.json', encoding='utf-8-sig'))
    tv = next((D / 'arc').glob('TVTMS*.txt'))
    mapa, caps = MV.construir(str(tv), arc)
    T = TL.titulos()
    busca = []; abertura = {}
    (OUT / 'data').mkdir(parents=True, exist_ok=True)
    livros = []
    n_pal = n_ver = 0
    for jl in sorted(glob.glob(str(D / 'saida' / 'jsonl' / '*.jsonl'))):
        base = Path(jl).stem; num = int(base.split('_')[0])
        rtl = num <= 39
        nome = (C.AT[num - 1][2] if rtl else C.NT[num - 40][2])
        recs = G.carregar(jl)
        verses = G.agrupar(recs)
        arc_v, _, alvos = MV.textos_arc(mapa, caps, arc, num, verses, com_alvos=True)
        caps_out = {}
        for cap, ver, words in verses:
            caps_out.setdefault(cap, []).append([ver, [palavra(w, rtl) for w in words], arc_v.get((cap, ver), '')])
        n = max(caps_out)
        if num == 19:   # a ARC 1911 traz a suscrição do salmo como título (sem número): vai no versículo 1 do original quando ele é só o título
            for cap, lst in caps_out.items():
                t = arc[18].get('titles', {}).get(str(cap))
                if t:
                    for it in lst:
                        if it[0] == 1 and not it[2]: it[2] = '[título] ' + t
        n_ver += sum(len(v) for v in caps_out.values()); n_pal += sum(len(x[1]) for v in caps_out.values() for x in v)
        inv = {}
        for orig_ref, tg in alvos.items():
            for t in tg: inv.setdefault(t, orig_ref)
        ent = []
        for c, vs in enumerate(arc[num - 1]['chapters'], 1):
            for v, txt in enumerate(vs, 1):
                txt = re.sub(r' ([,.;:!?])', r'\1', txt.strip())
                o = inv.get((c, v))
                row = [c, v, txt] if o in (None, (c, v)) and (o is not None or True) else [c, v, txt, o[0], o[1]]
                if o is None: row = [c, v, txt, c, 0]          # sem versículo correspondente no original: abre o capítulo
                ent.append(row)
        busca.append(ent)
        if num == 19:
            ab = {'ref': 'Salmos 1:1-2', 'he': [], 'tr': [], 'arc': []}
            for vv in (1, 2):
                pal = [palavra(w, True) for w in next(x[2] for x in verses if x[0] == 1 and x[1] == vv)]
                ab['he'].append(''.join(p[0] + ('' if p[0].endswith('־') else ' ') for p in pal).strip())
                ab['arc'].append(arc_v.get((1, vv), ''))
            abertura = ab
        lang, o, tr, pt = T[num - 1]
        livros.append({'n': num, 'sigla': base.split('_', 1)[1], 'nome': nome, 't': 'AT' if rtl else 'NT',
                       'o': o, 'tr': tr, 'lit': pt, 'caps': n})
        dados = [caps_out.get(c, []) for c in range(1, n + 1)]
        (OUT / 'data' / f'{num:02d}.js').write_text(
            f'(window.__B=window.__B||{{}})[{num}]=' + json.dumps(dados, ensure_ascii=False, separators=(',', ':')) + ';', encoding='utf-8')
    (OUT / 'data' / 'livros.js').write_text('window.LIVROS=' + json.dumps(livros, ensure_ascii=False, separators=(',', ':')) + ';', encoding='utf-8')
    (OUT / 'data' / 'arc.js').write_text('window.__ARC=' + json.dumps(busca, ensure_ascii=False, separators=(',', ':')) + ';', encoding='utf-8')
    import datetime
    meta = {'versao': '1.2', 'autor': 'servo de Deus', 'build': datetime.date.today().isoformat(), 'livros': len(livros),
            'capitulos': sum(b['caps'] for b in livros), 'versiculos': n_ver, 'palavras': n_pal, 'abertura': abertura}
    (OUT / 'data' / 'meta.js').write_text('window.APP_META=' + json.dumps(meta, ensure_ascii=False) + ';', encoding='utf-8')
    src = RAIZ / 'app_src'
    for f in src.iterdir():
        if f.is_file(): shutil.copy(f, OUT / f.name)
    for f in ('referencias.html',):
        shutil.copy(D / 'saida' / f, OUT / f)
    print('app gerado em', OUT, '—', len(livros), 'livros')


if __name__ == '__main__':
    main()
