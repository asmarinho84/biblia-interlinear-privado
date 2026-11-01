#!/usr/bin/env python3
"""gerar_auditoria.py — gera dados_biblia/saida/auditoria_sentidos.html: uma linha por regra de contexto aplicada
(quantas vezes, exemplos, sentido padrão do dicionário × sentido escolhido, classe A/B/C, motivo)."""
import collections, glob, html, json, re
from pathlib import Path
import converter_biblia as C

NOMES = {f'{i:02d}': s for i, (o, s, n) in enumerate(C.AT, start=1)}
NOMES.update({f'{i:02d}': s for i, (p, s, n) in enumerate(C.NT, start=40)})


def main(dados=None):
    dados = dados or str(Path(__file__).resolve().parent / 'dados_biblia')
    dados = Path(dados)
    g = collections.OrderedDict()
    for jl in sorted(glob.glob(str(dados / 'saida' / 'jsonl' / '*.jsonl'))):
        arq = Path(jl).stem
        for ln in open(jl, encoding='utf-8'):
            r = json.loads(ln)
            c = r.get('gl_ctx')
            if not c:
                continue
            k = (c['c'], c['n'], c['b'])
            e = g.setdefault(k, {'n': 0, 'gl': collections.Counter(), 'ex': [], 'lang': r['lang'], 'orig': collections.Counter()})
            e['n'] += 1
            e['gl'][r['gl']] += 1
            e['orig'][(r['orig'], r['translit'])] += 1
            if len(e['ex']) < 4:
                e['ex'].append((r['ref'], arq))
    ordem = {'B': 0, 'C': 1, 'A': 2}
    linhas = []
    for (cl, why, base), e in sorted(g.items(), key=lambda kv: (ordem[kv[0][0]], -kv[1]['n'])):
        gls = ' · '.join(f'{html.escape(x)} ({n})' for x, n in e['gl'].most_common(4))
        (o, t), _ = e['orig'].most_common(1)[0]
        ex = ' · '.join(f'<a href="html/{a}.html">{html.escape(ref)}</a>' for ref, a in e['ex'])
        linhas.append(f'<tr class="c{cl}"><td><b>{cl}</b></td><td>{e["n"]}</td><td dir="{"rtl" if e["lang"] == "hbo" else "ltr"}">{html.escape(o)}<br><small>{html.escape(t)}</small></td>'
                      f'<td>{html.escape(base)}</td><td><b>{gls}</b></td><td>{html.escape(why)}</td><td><small>{ex}</small></td></tr>')
    tot = collections.Counter({k: sum(e['n'] for kk, e in g.items() if kk[0] == k) for k in 'ABC'})
    css = C.CSS + """
table{border-collapse:collapse;width:100%;font-size:.82rem}td,th{border:1px solid var(--ln);padding:.4rem;vertical-align:top;text-align:left}
th{background:rgba(128,128,128,.12);position:sticky;top:0}.wrap{overflow-x:auto}tr.cA td:first-child{color:#3b7a3b}tr.cB td:first-child{color:#c28a00}tr.cC td:first-child{color:#7a4bb0}
#q{font-size:1rem;padding:.4rem;width:100%;box-sizing:border-box;margin:.5rem 0}small{color:var(--mut)}
"""
    page = (f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Auditoria — sentidos escolhidos por contexto</title><style>{css}</style>'
            f'<p><a href="index.html">← Índice</a> · <a href="referencias.html">Referências</a></p>'
            f'<h1>Sentidos escolhidos por contexto<small>cada linha = uma regra; todas as palavras afetadas aparecem com sublinhado pontilhado nos livros</small></h1>'
            f'<p><b>Como foi feito:</b> o interlinear começa com o 1º sentido do dicionário. Onde o contexto mostra que outro sentido <i>do mesmo dicionário</i> serve melhor para quem lê, '
            f'uma regra (arquivo <code>lexico/contexto.tsv</code>) troca a glosa. Nenhuma outra Bíblia é usada. '
            f'<b>A</b> ({tot["A"]}) = a forma gramatical decide (tema verbal, caso, gênero, número). '
            f'<b>B</b> ({tot["B"]}) = escolha pelo contexto entre os sentidos do dicionário (julgamento de leitura; revise por amostragem). '
            f'<b>C</b> ({tot["C"]}) = locução de duas ou mais palavras.</p>'
            f'<input id="q" placeholder="filtrar (ex.: porque, vento, δέ, 3588)…" oninput="var v=this.value.toLowerCase();document.querySelectorAll(\'tbody tr\').forEach(function(r){{r.style.display=r.innerText.toLowerCase().indexOf(v)<0?\'none\':\'\'}})">'
            f'<div class="wrap"><table><thead><tr><th>Cl.</th><th>Vezes</th><th>Palavra</th><th>Padrão do dicionário</th><th>Glosa escolhida</th><th>Motivo</th><th>Exemplos</th></tr></thead><tbody>{"".join(linhas)}</tbody></table></div>')
    (dados / 'saida' / 'auditoria_sentidos.html').write_text(page, encoding='utf-8')
    print('auditoria_sentidos.html gerado:', len(linhas), 'linhas')


if __name__ == '__main__':
    main()
