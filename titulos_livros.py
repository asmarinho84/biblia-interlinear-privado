"""Títulos tradicionais dos livros no idioma original, com transliteração (mesmas regras do projeto) e tradução em português.
Hebraico: título tradicional (1ª palavra no Pentateuco; nome do livro nos demais). Grego: título tradicional do NT (SBLGNT).
Numerais (1, 2, 3) ficam só na tradução. Nomes próprios mantêm a forma portuguesa."""
import re
import converter_biblia as C

AT_T = [
    ('בְּרֵאשִׁית', 'No princípio'), ('שְׁמוֹת', 'Nomes'), ('וַיִּקְרָא', 'E chamou'), ('בְּמִדְבַּר', 'No deserto de'), ('דְּבָרִים', 'Palavras'),
    ('יְהוֹשֻׁעַ', 'Josué'), ('שׁוֹפְטִים', 'Juízes'), ('רוּת', 'Rute'), ('שְׁמוּאֵל', '1 Samuel'), ('שְׁמוּאֵל', '2 Samuel'),
    ('מְלָכִים', '1 Reis'), ('מְלָכִים', '2 Reis'), ('דִּבְרֵי הַיָּמִים', '1 Palavras dos dias'), ('דִּבְרֵי הַיָּמִים', '2 Palavras dos dias'),
    ('עֶזְרָא', 'Esdras'), ('נְחֶמְיָה', 'Neemias'), ('אֶסְתֵּר', 'Ester'), ('אִיּוֹב', 'Jó'), ('תְּהִלִּים', 'Louvores'),
    ('מִשְׁלֵי', 'Provérbios de'), ('קֹהֶלֶת', 'Coélet'), ('שִׁיר הַשִּׁירִים', 'Cântico dos cânticos'), ('יְשַׁעְיָהוּ', 'Isaías'),
    ('יִרְמְיָהוּ', 'Jeremias'), ('אֵיכָה', 'Como?'), ('יְחֶזְקֵאל', 'Ezequiel'), ('דָּנִיֵּאל', 'Daniel'), ('הוֹשֵׁעַ', 'Oseias'),
    ('יוֹאֵל', 'Joel'), ('עָמוֹס', 'Amós'), ('עֹבַדְיָה', 'Obadias'), ('יוֹנָה', 'Jonas'), ('מִיכָה', 'Miqueias'),
    ('נַחוּם', 'Naum'), ('חֲבַקּוּק', 'Habacuque'), ('צְפַנְיָה', 'Sofonias'), ('חַגַּי', 'Ageu'), ('זְכַרְיָה', 'Zacarias'), ('מַלְאָכִי', 'Malaquias'),
]
NT_T = [
    ('Κατὰ Μαθθαῖον', 'Segundo Mateus'), ('Κατὰ Μᾶρκον', 'Segundo Marcos'), ('Κατὰ Λουκᾶν', 'Segundo Lucas'), ('Κατὰ Ἰωάννην', 'Segundo João'),
    ('Πράξεις Ἀποστόλων', 'Ações de apóstolos'), ('Πρὸς Ῥωμαίους', 'Para romanos'),
    ('Πρὸς Κορινθίους', '1 Para coríntios'), ('Πρὸς Κορινθίους', '2 Para coríntios'), ('Πρὸς Γαλάτας', 'Para gálatas'),
    ('Πρὸς Ἐφεσίους', 'Para efésios'), ('Πρὸς Φιλιππησίους', 'Para filipenses'), ('Πρὸς Κολοσσαεῖς', 'Para colossenses'),
    ('Πρὸς Θεσσαλονικεῖς', '1 Para tessalonicenses'), ('Πρὸς Θεσσαλονικεῖς', '2 Para tessalonicenses'),
    ('Πρὸς Τιμόθεον', '1 Para Timóteo'), ('Πρὸς Τιμόθεον', '2 Para Timóteo'), ('Πρὸς Τίτον', 'Para Tito'), ('Πρὸς Φιλήμονα', 'Para Filemom'),
    ('Πρὸς Ἑβραίους', 'Para hebreus'), ('Ἰακώβου', 'De Tiago'), ('Πέτρου', '1 De Pedro'), ('Πέτρου', '2 De Pedro'),
    ('Ἰωάννου', '1 De João'), ('Ἰωάννου', '2 De João'), ('Ἰωάννου', '3 De João'), ('Ἰούδα', 'De Judas'), ('Ἀποκάλυψις Ἰωάννου', 'Revelação de João'),
]
assert len(AT_T) == 39 and len(NT_T) == 27


def translit_hebr_titulo(txt):
    return ''.join(('-' if p == '־' else p) if p in ('־', ' ') else C.translit_hebr(p)[0]
                   for p in re.split('([ ־])', txt.replace('ׇ', 'ֹ')))


def translit_grego_titulo(txt):
    return ' '.join(C.translit_grc(w) for w in txt.split())


def titulos():
    """lista de 66 tuplas: (lang, original, transliteração, tradução), na ordem dos livros"""
    out = [('he', o, translit_hebr_titulo(o), t) for o, t in AT_T]
    out += [('grc', o, translit_grego_titulo(o), t) for o, t in NT_T]
    return out


if __name__ == '__main__':
    for t in titulos():
        print(t)
