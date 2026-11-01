# Bíblia interlinear (66 livros) — original + transliteração + glosa em português (dicionário)

Ordem de execução (Python 3, `pip install pyyaml`):

**Pasta raiz:** a pasta que contém estes `.py` e `dados_biblia/`. Todos os scripts usam a própria pasta como raiz (funciona de qualquer diretório, em qualquer PC). Os links do HTML são relativos: mantenha `index.html`, `referencias.html`, `auditoria_sentidos.html` e `html/` juntos; para ler, abra `dados_biblia/saida/index.html`.

1. `python3 baixar_biblia.py`            baixa textos originais e dicionários (OSHB/WLC, MorphGNT/SBLGNT, HebrewLexicon, lexemes.yaml)
2. `python3 converter_biblia.py`         organiza + transliteração (hebraico/aramaico RTL, grego LTR) → saida/jsonl e saida/html
3. `python3 montar_lexico.py`            dicionário lema → glosa (inglês curta, dos léxicos) → lexico/*_en.json
4. `python3 preparar_traducao.py`        lista congelada lexico/entradas.tsv (14.665 entradas)
   (traduções PT feitas à mão a partir das glosas do dicionário: lexico/pt_por_id.txt — já incluso)
5. `python3 aplicar_traducoes.py`        junta tudo → lexico/hebraico_pt.json, grego_pt.json (confere 100%)
6. `python3 glosar_biblia.py`            acrescenta glosa PT + morfologia por palavra, regenera o HTML
7. `python3 validar_biblia.py`           validação independente
   (glosar_biblia.py também gera saida/referencias.html, linkada no índice)

Ajustes curados de exibição (glosa curta quando o 1º sentido do dicionário engana): lexico/ajustes_exibicao.tsv

Fontes/licenças: OSHB (CC BY 4.0), MorphGNT SBLGNT (CC BY-SA 3.0), OpenScriptures HebrewLexicon (CC BY 4.0 / domínio público),
MorphGNT morphological-lexicon (CC BY-SA 4.0).

Limites conhecidos: glosas em forma de lema (verbos no infinitivo; número/gênero/pessoa na linha morfológica);
sem marcação de sílaba tônica no hebraico; numeração de versículos segue o WLC (difere de Bíblias em português
em Salmos com título, Joel, Malaquias etc.); texto grego é o SBLGNT (crítico), não o Textus Receptus.



## Passo 8 — sentido por contexto (só entre sentidos do dicionário)
- `dados_biblia/lexico/contexto.tsv` — regras auditáveis: `lang  chave  condições  glosa  classe  motivo` (formato no cabeçalho de `contexto.py`).
- `contexto.py` — motor de regras; `glosar_biblia.py` aplica durante a glosa; `gerar_auditoria.py` gera `saida/auditoria_sentidos.html`.
- Classes: A = forma gramatical decide; B = escolha pelo contexto (julgamento de leitura de Claude, revisar por amostragem); C = locução.
- Cobertura atual: ~41 mil de 443 mil palavras (A 28.155 · B 12.047 · C 1.047). Para ampliar, acrescente linhas ao TSV e rode `python3 glosar_biblia.py`.
- Também: "-de" em construtos hebraicos, particípio passivo em português, pronomes gregos por caso.
- Mapas foram removidos do projeto a pedido.

## Passo 9 — linha ARC (Almeida Revista e Corrigida)
- Cada versículo mostra, abaixo da interlinear, a linha **ARC** (`dados_biblia/arc/pt_arc.json`, baixado por `baixar_biblia.py`).
- `mapa_versos.py` converte a numeração do original (WLC/SBLGNT) para a da ARC usando a tabela STEPBible TVTMS (`arc/TVTMS_STEPBible.txt`) + alinhamento por posição + correções manuais (1Reis 5, Neemias 7, 1Crônicas 12). Sem correspondência segura aparece “—” (ex.: títulos de Salmos; Mt 17:21 ausente no SBLGNT).
- A ARC não entra nas glosas: a interlinear continua vindo só dos dicionários.
- **Aviso legal:** o arquivo ARC é uma edição **moderna** (não a de 1898), com direitos autorais; uso pessoal, **não publicar**. Veja `AVISO_LEGAL.md`.

## Passo 10 — app web (leitura configurável)
- `python3 exportar_app.py` gera `dados_biblia/app/` (index.html + style.css + app.js + data/NN.js, um arquivo por livro). Interface-fonte em `app_src/`.
- Abra `dados_biblia/app/index.html` (funciona offline, inclusive direto do arquivo) ou publique a pasta `app/` em qualquer hospedagem estática.
- Configurações: texto original, transliteração, interlinear, morfologia e ARC, ligados/desligados de forma independente; tamanho do texto; tema; sublinhado de sentidos por contexto.
- Cores: Antigo Testamento em terracota, Novo Testamento em azul. Capítulos lidos ficam salvos no navegador (localStorage), com exportar/importar arquivo para trocar de aparelho.

## Passo 11 — app Android (APK)
- `python3 build_apk.py` gera `dados_biblia/Biblia_Interlinear.apk` (WebView + app web embutido em assets/app; sem permissões, 100% offline).
- Projeto em `android/` (manifesto, recursos, `MainActivity.smali`, `Asm.java` = montador smali, `assinar.mjs`, `keys/` = chave de assinatura).
- Ferramentas usadas (sem Android SDK): aapt2 (npm aaptjs3), android.jar API 34 (GitHub Reginer/aosp-android-jar), apktool 2.4.1 (npm apktool-jar, só as classes smali), apk_sign_ts (npm, assinatura v1+v2+v3). Ajuste `BIBLIA_TOOLS` se instalar em outra pasta.
- GUARDE `android/keys/`: atualizações do app só instalam por cima se forem assinadas com a mesma chave.
- Antes: `python3 exportar_app.py` (gera `dados_biblia/app`); o `build_apk.py` embute essa pasta automaticamente.
- Ícone: `python3 android/gerar_icone.py` (adaptativo + monocromático). Versão/autor: `exportar_app.py` (meta.js) e `--version-name` em `build_apk.py`.
- Tela sempre ligada: `FLAG_KEEP_SCREEN_ON` em `MainActivity.smali`.


## ARC 1911 (versão 1.2)
A linha ARC usa a edição de 1911 (domínio público, Gutenberg #62383). Gere o JSON com `python3 converter_arc1911.py` (baixa o canon fixado por commit) e depois `exportar_app.py` e `build_apk.py`. Ver `AVISO_LEGAL.md`.
