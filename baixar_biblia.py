#!/usr/bin/env python3
"""
baixar_biblia.py — Baixa, de forma organizada, os textos nas línguas originais
dos 66 livros da Bíblia cristã, com morfologia e léxicos (dicionários).

FONTES (todas abertas, sem tradução bíblica em português/inglês no meio):
  AT (hebraico + aramaico de Esdras/Daniel/Jeremias 10:11/Gênesis 31:47):
      OSHB — Open Scriptures Hebrew Bible (Westminster Leningrad Codex + morfologia
      + lemas com numeração Strong/BDB)  -> github.com/openscriptures/morphhb
  NT (grego koiné, texto crítico SBLGNT + morfologia + lema):
      MorphGNT/SBLGNT                    -> github.com/morphgnt/sblgnt
  DICIONÁRIOS (para glosa; NÃO são bíblias):
      Hebraico: openscriptures/HebrewLexicon (BDB/Strong)
      Grego:    openscriptures/strongs (Strong grego)

ESTRUTURA GERADA (pasta ./dados_biblia):
  AT_hebraico_WLC/01_Gn.xml ... 39_Ml.xml
  NT_grego_SBLGNT/40_Mt.txt ... 66_Ap.txt
  dicionarios/...
  manifesto.json   (URL, tamanho, SHA-256 de cada arquivo)

USO:
  python3 baixar_biblia.py              # baixa tudo (retoma o que faltar)
  python3 baixar_biblia.py --verificar  # só confere o que já existe
  python3 baixar_biblia.py --saida OUTRA_PASTA
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAW = "https://raw.githubusercontent.com"

# (ordem, nome do arquivo OSHB, sigla PT-BR, nome PT-BR)
AT = [
    ("Gen", "Gn", "Gênesis"), ("Exod", "Êx", "Êxodo"), ("Lev", "Lv", "Levítico"),
    ("Num", "Nm", "Números"), ("Deut", "Dt", "Deuteronômio"), ("Josh", "Js", "Josué"),
    ("Judg", "Jz", "Juízes"), ("Ruth", "Rt", "Rute"), ("1Sam", "1Sm", "1 Samuel"),
    ("2Sam", "2Sm", "2 Samuel"), ("1Kgs", "1Rs", "1 Reis"), ("2Kgs", "2Rs", "2 Reis"),
    ("1Chr", "1Cr", "1 Crônicas"), ("2Chr", "2Cr", "2 Crônicas"), ("Ezra", "Ed", "Esdras"),
    ("Neh", "Ne", "Neemias"), ("Esth", "Et", "Ester"), ("Job", "Jó", "Jó"),
    ("Ps", "Sl", "Salmos"), ("Prov", "Pv", "Provérbios"), ("Eccl", "Ec", "Eclesiastes"),
    ("Song", "Ct", "Cantares"), ("Isa", "Is", "Isaías"), ("Jer", "Jr", "Jeremias"),
    ("Lam", "Lm", "Lamentações"), ("Ezek", "Ez", "Ezequiel"), ("Dan", "Dn", "Daniel"),
    ("Hos", "Os", "Oseias"), ("Joel", "Jl", "Joel"), ("Amos", "Am", "Amós"),
    ("Obad", "Ob", "Obadias"), ("Jonah", "Jn", "Jonas"), ("Mic", "Mq", "Miqueias"),
    ("Nah", "Na", "Naum"), ("Hab", "Hc", "Habacuque"), ("Zeph", "Sf", "Sofonias"),
    ("Hag", "Ag", "Ageu"), ("Zech", "Zc", "Zacarias"), ("Mal", "Ml", "Malaquias"),
]

# (prefixo MorphGNT, sigla PT-BR, nome PT-BR)
NT = [
    ("61-Mt", "Mt", "Mateus"), ("62-Mk", "Mc", "Marcos"), ("63-Lk", "Lc", "Lucas"),
    ("64-Jn", "Jo", "João"), ("65-Ac", "At", "Atos"), ("66-Ro", "Rm", "Romanos"),
    ("67-1Co", "1Co", "1 Coríntios"), ("68-2Co", "2Co", "2 Coríntios"),
    ("69-Ga", "Gl", "Gálatas"), ("70-Eph", "Ef", "Efésios"), ("71-Php", "Fp", "Filipenses"),
    ("72-Col", "Cl", "Colossenses"), ("73-1Th", "1Ts", "1 Tessalonicenses"),
    ("74-2Th", "2Ts", "2 Tessalonicenses"), ("75-1Ti", "1Tm", "1 Timóteo"),
    ("76-2Ti", "2Tm", "2 Timóteo"), ("77-Tit", "Tt", "Tito"), ("78-Phm", "Fm", "Filemom"),
    ("79-Heb", "Hb", "Hebreus"), ("80-Jas", "Tg", "Tiago"), ("81-1Pe", "1Pe", "1 Pedro"),
    ("82-2Pe", "2Pe", "2 Pedro"), ("83-1Jn", "1Jo", "1 João"), ("84-2Jn", "2Jo", "2 João"),
    ("85-3Jn", "3Jo", "3 João"), ("86-Jud", "Jd", "Judas"), ("87-Re", "Ap", "Apocalipse"),
]


def montar_lista(raiz: Path):
    """Retorna lista de (url, caminho_destino)."""
    itens = []
    for i, (osis, sigla, _nome) in enumerate(AT, start=1):
        itens.append((f"{RAW}/openscriptures/morphhb/master/wlc/{osis}.xml",
                      raiz / "AT_hebraico_WLC" / f"{i:02d}_{sigla}.xml"))
    itens.append((f"{RAW}/openscriptures/morphhb/master/wlc/VerseMap.xml",
                  raiz / "AT_hebraico_WLC" / "VerseMap.xml"))
    for i, (pref, sigla, _nome) in enumerate(NT, start=40):
        itens.append((f"{RAW}/morphgnt/sblgnt/master/{pref}-morphgnt.txt",
                      raiz / "NT_grego_SBLGNT" / f"{i:02d}_{sigla}.txt"))
    # Dicionários
    itens += [
        (f"{RAW}/openscriptures/HebrewLexicon/master/HebrewStrong.xml",
         raiz / "dicionarios" / "hebraico_HebrewStrong.xml"),
        (f"{RAW}/openscriptures/HebrewLexicon/master/LexicalIndex.xml",
         raiz / "dicionarios" / "hebraico_LexicalIndex.xml"),
        (f"{RAW}/openscriptures/HebrewLexicon/master/BrownDriverBriggs.xml",
         raiz / "dicionarios" / "hebraico_BDB.xml"),
        (f"{RAW}/openscriptures/strongs/master/greek/strongs-greek-dictionary.js",
         raiz / "dicionarios" / "grego_strongs.js"),
        (f"{RAW}/openscriptures/strongs/master/hebrew/strongs-hebrew-dictionary.js",
         raiz / "dicionarios" / "hebraico_strongs.js"),
        # léxico grego por lema (glosa curta por lexema; MorphGNT, CC-BY-SA)
        (f"{RAW}/morphgnt/morphological-lexicon/master/lexemes.yaml",
         raiz / "dicionarios" / "grego_lexemes.yaml"),
        # (a ARC 1911 vem de converter_arc1911.py, que baixa o canon do Gutenberg #62383 via GitHub) + tabela de versificação (equivalência de versículos)
        (f"{RAW}/STEPBible/STEPBible-Data/master/Versification/TVTMS%20-%20Translators%20Versification%20Traditions%20with%20Methodology%20for%20Standardisation%20for%20Eng%2BHeb%2BLat%2BGrk%2BOthers%20-%20STEPBible.org%20CC%20BY.txt",
         raiz / "arc" / "TVTMS_STEPBible.txt"),
    ]
    return itens


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(url: str, destino: Path, tentativas: int = 4):
    if destino.exists() and destino.stat().st_size > 0:
        return url, destino, "ja_existia", None
    destino.parent.mkdir(parents=True, exist_ok=True)
    ultimo_erro = None
    for t in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "baixar-biblia/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                dados = r.read()
            if not dados:
                raise ValueError("resposta vazia")
            tmp = destino.with_suffix(destino.suffix + ".part")
            tmp.write_bytes(dados)
            tmp.replace(destino)
            return url, destino, "baixado", None
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            ultimo_erro = str(e)
            time.sleep(2 * t)
    return url, destino, "falhou", ultimo_erro


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", default=str(Path(__file__).resolve().parent / "dados_biblia"))
    ap.add_argument("--verificar", action="store_true", help="não baixa; só confere")
    ap.add_argument("--threads", type=int, default=6)
    args = ap.parse_args()

    raiz = Path(args.saida)
    itens = montar_lista(raiz)
    manifesto, falhas = {}, []

    if not args.verificar:
        with ThreadPoolExecutor(max_workers=args.threads) as ex:
            futuros = [ex.submit(baixar, u, d) for u, d in itens]
            for n, fut in enumerate(as_completed(futuros), 1):
                url, dest, status, erro = fut.result()
                print(f"[{n:3d}/{len(itens)}] {status:10s} {dest.relative_to(raiz)}"
                      + (f"  ERRO: {erro}" if erro else ""))
                if status == "falhou":
                    falhas.append((url, erro))

    faltando = []
    for url, dest in itens:
        if dest.exists() and dest.stat().st_size > 0:
            manifesto[str(dest.relative_to(raiz))] = {
                "url": url, "bytes": dest.stat().st_size, "sha256": sha256(dest)}
        else:
            faltando.append(str(dest.relative_to(raiz)))

    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")

    n_at = sum(1 for k in manifesto if k.startswith("AT_") and not k.endswith("VerseMap.xml"))
    n_nt = sum(1 for k in manifesto if k.startswith("NT_"))
    print(f"\nAT: {n_at}/39 livros | NT: {n_nt}/27 livros | total: {n_at + n_nt}/66")
    if faltando:
        print("Faltando:", *faltando, sep="\n  ")
        sys.exit(1)
    print(f"Tudo certo. Manifesto em {raiz / 'manifesto.json'}")


if __name__ == "__main__":
    main()
