#!/usr/bin/env python3
"""gerar_referencias.py — gera dados_biblia/saida/referencias.html (fontes, licenças e como cada uma foi usada)."""
import html
import sys
from pathlib import Path

import converter_biblia as C

DADOS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'dados_biblia'
GH = 'https://github.com/'

FONTES = [
    ('Tradução em português — Almeida Revista e Corrigida (ARC), edição de 1911',
     'João Ferreira de Almeida; edição revista e corrigida, Deposito das Escripturas Sagradas, Lisboa, 1911. Transcrição do Project Gutenberg (eBook nº 62383) por Júlio Reis, abi278, Sergio Queiroz e Distributed Proofreaders; estruturação em Markdown de github.com/mazza/biblia-arc1911 (CC0)',
     'Domínio público (Lei 9.610/1998, Art. 41 e Art. 45, I; Convenção de Berna; EUA: obras anteriores a 1929). Declaração do usuário do projeto, mais a declaração de domínio público do Project Gutenberg; arquivo conferido por SHA-256 (bf9c6053…).',
     'arc/pt_arc1911.json', GH + 'mazza/biblia-arc1911',
     'Mostrada como última linha de cada versículo e usada na busca; grafia de 1911 preservada. Removidas só as chamadas de notas e os itálicos; cinco fronteiras de versículo ajustadas (Jz 5, 1Sm 20, 1Rs 22, 2Co 13, Ap 12). O Gutenberg avisa que algumas referências cruzadas da transcrição estão erradas. Não há revisão jurídica independente: confirme em caso de uso comercial.'),
    ('Tabela de versificação — STEPBible TVTMS',
     'STEPBible.org (Tyndale House)', 'CC BY 4.0',
     'arc/TVTMS_STEPBible.txt', GH + 'STEPBible/STEPBible-Data',
     'Equivalência de numeração de versículos entre o hebraico e as Bíblias em português/inglês (Salmos com título, Joel, Malaquias etc.). Onde a tabela não cobria, alinhei por posição dentro de capítulos vizinhos; versículo sem par seguro (ex.: títulos de Salmos) mostra “—”.'),
    ('Texto hebraico/aramaico do AT — OSHB (Open Scriptures Hebrew Bible)',
     'Open Scriptures · base: Westminster Leningrad Codex (WLC)', 'morphhb (OSHB) — texto WLC em domínio público; marcação morfológica/lemas CC BY 4.0',
     'AT_hebraico_WLC/01_Gn.xml … 39_Ml.xml (39 arquivos, formato OSIS)', GH + 'openscriptures/morphhb',
     'Texto-base de todos os 39 livros do AT. De cada palavra foram extraídos: letras com vogais e acentos, divisão em morfemas (prefixos/radical/sufixos), lema (numeração Strong/BDB) e código morfológico. '
     'Ketiv/qere tratados conforme as notas do XML. Alimenta a transliteração, a glosa (via lema) e a linha de morfologia.'),
    ('Texto grego do NT — MorphGNT / SBLGNT',
     'Society of Biblical Literature + Logos/Faithlife (texto); James Tauber e colaboradores (MorphGNT)', 'SBLGNT: CC BY 4.0 · MorphGNT: CC BY-SA 3.0',
     'NT_grego_SBLGNT/40_Mt.txt … 66_Ap.txt (27 arquivos)', GH + 'morphgnt/sblgnt',
     'Texto-base dos 27 livros do NT. De cada palavra: forma com pontuação, forma normalizada, lema, classe gramatical e análise (pessoa, tempo, voz, modo, caso, número, gênero). '
     'Alimenta transliteração, glosa (via lema) e morfologia. É texto crítico (SBLGNT), não o Textus Receptus.'),
    ('Léxico hebraico — OpenScriptures HebrewLexicon (LexicalIndex.xml)',
     'Open Scriptures (índice léxico baseado em BDB/Strong)', 'CC BY 4.0 (conteúdo de BDB e Strong em domínio público)',
     'dicionarios/hebraico_LexicalIndex.xml', GH + 'openscriptures/HebrewLexicon',
     'Fonte principal das glosas curtas hebraicas (campo <def>) e da transliteração de referência por lema (9.204 entradas). Cada glosa curta (inglês) foi traduzida para o português, uma a uma.'),
    ('Strong hebraico — HebrewStrong.xml',
     'Open Scriptures (dicionário de Strong)', 'Domínio público (Strong) · estrutura CC BY 4.0',
     'dicionarios/hebraico_HebrewStrong.xml', GH + 'openscriptures/HebrewLexicon',
     'Reserva para lemas ausentes do LexicalIndex: usado apenas o campo <meaning><def>. O campo <usage> (que lista traduções da KJV) foi deliberadamente NÃO usado, para não incorporar traduções bíblicas.'),
    ('Léxico grego — MorphGNT morphological-lexicon (lexemes.yaml)',
     'James Tauber / MorphGNT', 'CC BY-SA',
     'dicionarios/grego_lexemes.yaml', GH + 'morphgnt/morphological-lexicon',
     'Fonte das glosas curtas gregas por lema (5.461 lemas; dois lemas ausentes, μήν e συναπάγομαι, foram preenchidos manualmente). Traduzidas para o português uma a uma.'),
    ('Dicionários de Strong (grego e hebraico, versão JS)',
     'Open Scriptures (strongs)', 'Domínio público',
     'dicionarios/grego_strongs.js · dicionarios/hebraico_strongs.js', GH + 'openscriptures/strongs',
     'Baixados como material de consulta (etapa 1). Não entram nas glosas finais.'),
    ('Brown-Driver-Briggs (BDB) — BrownDriverBriggs.xml',
     'Open Scriptures (digitalização do BDB)', 'Domínio público',
     'dicionarios/hebraico_BDB.xml', GH + 'openscriptures/HebrewLexicon',
     'Baixado como dicionário de referência completo (etapa 1). As glosas finais usam o LexicalIndex, que condensa o BDB; o BDB em si não foi processado.'),
    ('Mapa de versículos — VerseMap.xml',
     'Open Scriptures', 'CC BY 4.0',
     'AT_hebraico_WLC/VerseMap.xml', GH + 'openscriptures/morphhb',
     'Baixado, mas ainda NÃO aplicado: a numeração de capítulos/versículos do AT segue o WLC e difere de Bíblias em português em alguns trechos (Salmos com título, Joel, Malaquias etc.).'),
]

PROPRIO = [
    ('Transliteração', 'Regras próprias, escritas para este projeto (converter_biblia.py): hebraico por agrupamentos de consoantes e vogais, dagesh forte/leve, sheva vocal/mudo, matres lectionis, qamets gadol/qatan; '
                       'grego com espíritos, ditongos e iota subscrito. Verificada por teste independente (validar_biblia.py), que converte a transliteração de volta ao esqueleto de letras e compara com o original.'),
    ('Traduções para o português', 'As 14.665 glosas de dicionário (inglês → português) foram traduzidas uma a uma por Claude (IA), a partir do significado do verbete — não de outra Bíblia. '
                                   'Arquivos: lexico/entradas.tsv (lista congelada) e lexico/pt_por_id.txt. Podem conter imprecisões; revisão por especialista é recomendada.'),
    ('Ajustes de exibição', 'Cerca de 100 palavras muito frequentes tiveram a glosa curta escolhida entre os sentidos do próprio dicionário (ex.: ἀρχή → "princípio" em vez de "governante"). Lista em lexico/ajustes_exibicao.tsv.'),
    ('Escolha do sentido pelo contexto', 'Onde o contexto mostra qual sentido do mesmo dicionário serve melhor para quem lê, uma regra troca a glosa (lexico/contexto.tsv, 260+ regras; motor em contexto.py). Só entram sentidos que o dicionário lista; nenhuma tradução bíblica é usada. '
                                         'Classe A = a forma gramatical decide (tema verbal hebraico, caso, gênero e número); B = escolha pelo contexto entre os sentidos do dicionário (julgamento de leitura feito por Claude, a revisar por amostragem); C = locução de duas ou mais palavras (ex.: kî ʾim "mas antes", ʿal-kēn "por isso", οὐ μή). '
                                         'Cada palavra afetada aparece com sublinhado pontilhado nos livros e com o motivo ao toque; a página auditoria_sentidos.html lista todas as regras, quantas vezes valeram e exemplos.'),
    ('Formas para leitura', 'Substantivos e particípios hebraicos em construto levam "-de" (palavra-de, filhos-de); particípios passivos viram particípio passado (abençoado); pronomes gregos seguem o caso (dele, a-ele, de-mim) e, depois de preposição, usam a forma tônica (por meio de ele).'),    ('Regras de glosa por palavra', 'glosar_biblia.py: prefixos hebraicos (e, o/a, em, como, para, de, que), contrações com o artigo, sufixos pronominais, marcas (pl)/(du) e linha morfológica em português.'),
]


def e(s):
    return html.escape(s, quote=True)


def main():
    linhas = ''.join(
        f'<tr><td><b>{e(t)}</b><br><small>{e(a)}</small></td><td>{e(lic)}</td><td><code>{e(arq)}</code></td>'
        f'<td>{e(uso)}</td><td><a href="{e(url)}">{e(url.replace("https://", ""))}</a></td></tr>'
        for t, a, lic, arq, url, uso in FONTES)
    prop = ''.join(f'<li><b>{e(t)}.</b> {e(d)}</li>' for t, d in PROPRIO)
    css = C.CSS + """
table{border-collapse:collapse;width:100%;font-size:.85rem}td,th{border:1px solid var(--ln);padding:.5rem;vertical-align:top;text-align:left}
th{background:rgba(128,128,128,.12)}ul{columns:1}.wrap{overflow-x:auto}small{color:var(--mut)}code{font-size:.78rem;word-break:break-all}
"""
    page = (f'<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>Referências — Bíblia interlinear</title>'
            f'<style>{css}</style><p><a href="index.html">← Índice</a></p>'
            f'<h1>Referências e fontes<small>o que foi usado, de onde veio e como entrou no interlinear</small></h1>'
            f'<h2>Fontes externas</h2><div class="wrap"><table><tr><th>Fonte</th><th>Licença</th><th>Arquivo</th><th>Como foi usada</th><th>Link</th></tr>'
            f'{linhas}</table></div>'
            f'<h2>Trabalho próprio deste projeto</h2><ul>{prop}</ul>'
            f'<h2>Observações</h2><ul><li>Nenhuma tradução bíblica (portuguesa, inglesa ou outra) foi usada como fonte de texto ou de glosa.</li>'
            f'<li>Licenças indicadas conforme os repositórios no momento do download; confirme os termos atuais em cada link antes de redistribuir. '
            f'Licenças CC BY / CC BY-SA exigem atribuição às fontes acima.</li>'
            f'<li>Limites: glosas em forma de lema; sem marcação de sílaba tônica no hebraico; numeração de versículos do AT conforme o WLC.</li></ul>')
    (DADOS / 'saida' / 'referencias.html').write_text(page, encoding='utf-8')
    print('referencias.html gerado')


if __name__ == '__main__':
    main()
