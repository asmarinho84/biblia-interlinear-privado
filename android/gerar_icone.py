"""Gera o ícone (legado + adaptativo) em android/res/mipmap-*. Livro aberto com א (hebraico) e α (grego)."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
R = Path(__file__).resolve().parent / 'res'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'   # tem hebraico e grego
OT, NT = (168, 80, 31), (29, 95, 166)

def gradient(S):
    im = Image.new('RGB', (S, S)); px = im.load()
    for y in range(S):
        for x in range(S):
            t = (x + y) / (2 * S - 2)
            t = min(1, max(0, (t - .42) / .16))        # faixa de mistura estreita: cores nítidas
            px[x, y] = tuple(int(OT[k] + (NT[k] - OT[k]) * t) for k in range(3))
    return im

def livro(S, escala=1.0):
    """camada transparente com o livro aberto centralizado (área segura ~60% do lado)"""
    L = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    w, h = S * 0.62 * escala, S * 0.40 * escala; cx, cy = S / 2, S * 0.5
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    sh = S * 0.012
    # sombra
    d.polygon([(x0, y0 + sh * 3), (cx, y0 + h * .12 + sh * 3), (x1, y0 + sh * 3), (x1, y1 + sh * 3), (cx, y1 - h * .06 + sh * 3), (x0, y1 + sh * 3)], fill=(0, 0, 0, 60))
    # páginas
    d.polygon([(x0, y0), (cx, y0 + h * .12), (cx, y1 - h * .06), (x0, y1)], fill=(255, 250, 240, 255))
    d.polygon([(x1, y0), (cx, y0 + h * .12), (cx, y1 - h * .06), (x1, y1)], fill=(244, 248, 255, 255))
    d.line([(cx, y0 + h * .12), (cx, y1 - h * .06)], fill=(120, 110, 100, 255), width=max(2, int(S * .008)))
    f = ImageFont.truetype(FONT, int(h * .62))
    d.text((cx - w * .245, cy + h * .04), 'א', font=f, fill=OT + (255,), anchor='mm')
    d.text((cx + w * .245, cy + h * .04), 'α', font=f, fill=NT + (255,), anchor='mm')
    return L

def main():
    M = 1024
    # legado: quadrado arredondado
    base = gradient(M).convert('RGBA'); base.alpha_composite(livro(M, 1.18))
    for n, sz in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
        for nome, raio in (('ic_launcher', .22), ('ic_launcher_round', .5)):
            im = base.resize((sz, sz), Image.LANCZOS); m = Image.new('L', (sz, sz), 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, sz - 1, sz - 1], radius=int(sz * raio), fill=255); im.putalpha(m)
            (R / f'mipmap-{n}').mkdir(parents=True, exist_ok=True); im.save(R / f'mipmap-{n}' / f'{nome}.png')
    # adaptativo (108dp -> 432px em xxxhdpi): fundo + primeiro plano separados
    (R / 'mipmap-xxxhdpi').mkdir(exist_ok=True)
    gradient(432).save(R / 'mipmap-xxxhdpi' / 'ic_launcher_background.png')
    fg = livro(432, 1.0); fg.save(R / 'mipmap-xxxhdpi' / 'ic_launcher_foreground.png')
    # monocromático (Android 13+): silhueta branca
    mono = Image.new('RGBA', (432, 432), (0, 0, 0, 0)); a = fg.split()[3]; mono.paste((255, 255, 255, 255), mask=a)
    mono.save(R / 'mipmap-xxxhdpi' / 'ic_launcher_monochrome.png')
    (R / 'mipmap-anydpi-v26').mkdir(exist_ok=True)
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">'
           '<background android:drawable="@mipmap/ic_launcher_background"/><foreground android:drawable="@mipmap/ic_launcher_foreground"/>'
           '<monochrome android:drawable="@mipmap/ic_launcher_monochrome"/></adaptive-icon>')
    (R / 'mipmap-anydpi-v26' / 'ic_launcher.xml').write_text(xml); (R / 'mipmap-anydpi-v26' / 'ic_launcher_round.xml').write_text(xml)
    base.resize((512, 512), Image.LANCZOS).save(R.parent / 'icone_512.png')
if __name__ == '__main__': main()
