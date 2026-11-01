// assinar.mjs <entrada.apk> <saida.apk> <key.pem> <cert.pem>  — assina com v1+v2+v3 (pacote npm apk_sign_ts)
import { readFileSync, writeFileSync } from 'node:fs';
const { ApkSigner, SigningKey } = await import(process.env.APK_SIGN_TS);
const [, , entrada, saida, chave, cert] = process.argv;
const signer = new ApkSigner({ signingKey: SigningKey.fromPEM(readFileSync(chave, 'utf8'), readFileSync(cert, 'utf8')) });
const { signedApk } = await signer.sign(new Uint8Array(readFileSync(entrada)));
writeFileSync(saida, signedApk);
console.log('assinado:', saida);
