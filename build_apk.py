#!/usr/bin/env python3
"""build_apk.py — monta o APK da Bíblia Interlinear (WebView + app web embutido em assets/app).
Ferramentas (sem Android SDK completo): aapt2 (npm aaptjs3), android.jar (GitHub Reginer/aosp-android-jar),
montador smali (apktool 2.4.1 via npm apktool-jar) e assinador v1+v2+v3 (npm apk_sign_ts). Veja TOOLS abaixo.
Uso: python3 build_apk.py  -> dados_biblia/Biblia_Interlinear.apk"""
import os, shutil, subprocess, sys, zipfile, struct
from pathlib import Path
R = Path(__file__).resolve().parent
T = Path(os.environ.get('BIBLIA_TOOLS', '/tmp/tools'))
AAPT2 = T / 'aaptjs3-2.0.2/package/bin/x64/linux/aapt2'
ANDROID_JAR = T / 'android34.jar'
APKTOOL = T / 'apktool/package/bin/apktool_2.4.1.jar'
APK_SIGN = T / 'deps/node_modules/apk_sign_ts/dist/index.js'
ASM = Path(os.environ.get('BIBLIA_ASM', '/tmp/drv'))      # Asm.class (montador smali) — fonte em android/Asm.java
W = Path('/tmp/apk_build'); A = R / 'android'
SAIDA = R / 'dados_biblia' / 'Biblia_Interlinear.apk'


def run(*a, **k):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True, **k)
    if r.returncode: sys.exit(f'ERRO: {a[0]}\n{r.stdout}{r.stderr}')
    return r.stdout


def alinhar(src, dst):
    """equivalente ao zipalign 4: entradas sem compressão começam em offset múltiplo de 4"""
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, 'w') as zo:
        for i in zi.infolist():
            data = zi.read(i.filename)
            n = zipfile.ZipInfo(i.filename, i.date_time); n.external_attr = i.external_attr; n.compress_type = i.compress_type
            if i.compress_type == zipfile.ZIP_STORED:
                off = zo.fp.tell() + 30 + len(i.filename.encode())
                pad = (-off) % 4
                if pad: n.extra = struct.pack('<HH', 0xD935, pad - 4) + b'\0' * (pad - 4) if pad >= 4 else b'\0' * pad
            zo.writestr(n, data)


def main():
    shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
    shutil.copytree(R / 'dados_biblia' / 'app', W / 'assets' / 'app')        # app web embutido
    run('java', '-cp', f'{APKTOOL}:{ASM}', 'Asm', A / 'smali', W / 'classes.dex')
    run(AAPT2, 'compile', '--dir', A / 'res', '-o', W / 'res.zip')
    run(AAPT2, 'link', '-o', W / 'base.apk', '-I', ANDROID_JAR, '--manifest', A / 'AndroidManifest.xml',
        '-A', W / 'assets', '--min-sdk-version', '24', '--target-sdk-version', '34',
        '--version-code', '3', '--version-name', '1.2', '--rename-manifest-package', 'com.biblia.interlinear', str(W / 'res.zip'))
    with zipfile.ZipFile(W / 'base.apk', 'a') as z: z.write(W / 'classes.dex', 'classes.dex')
    alinhar(W / 'base.apk', W / 'aligned.apk')
    env = dict(os.environ, APK_SIGN_TS=str(APK_SIGN))
    run('node', A / 'assinar.mjs', W / 'aligned.apk', SAIDA, A / 'keys/key.pem', A / 'keys/cert.pem', env=env)
    print('APK:', SAIDA, round(SAIDA.stat().st_size / 1048576, 1), 'MiB')


if __name__ == '__main__':
    main()
