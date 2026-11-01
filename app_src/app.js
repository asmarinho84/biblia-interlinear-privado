'use strict';
/* Bíblia Interlinear — app estático, 100% offline. Dados em data/NN.js (um por livro). */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const EMBUTIDO = /; wv\)|Android.*Version\//.test(navigator.userAgent);   // WebView do app Android: sem download/upload de arquivo
const META = window.APP_META || { versao: '1.2', autor: 'servo de Deus', build: '', livros: 66, capitulos: 1189, versiculos: 0, palavras: 0 };
const L = window.LIVROS, TOTAL_CAPS = L.reduce((a, b) => a + b.caps, 0);

/* ---------- armazenamento (localStorage pode falhar: sempre em try/catch) ---------- */
const store = {
  get(k, d) { try { const v = localStorage.getItem('bi:' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('bi:' + k, JSON.stringify(v)); } catch (e) { } }
};
const DEF = { opc: true, orig: true, tr: true, gl: true, mf: false, arc: true, ctx: true, vnum: true, fs: 1, theme: 'auto', tab: 'AT' };
let cfg = Object.assign({}, DEF, store.get('cfg', {}));
let lidos = store.get('lidos', {});          // { "livro:cap": timestamp }
let ultimo = store.get('ultimo', null);      // { n, c }
const salvarCfg = () => { store.set('cfg', cfg); aplicar(); };
const salvarLidos = () => store.set('lidos', lidos);
const chave = (n, c) => n + ':' + c;
const livroLidos = n => { let k = 0; for (let c = 1; c <= L[n - 1].caps; c++) if (lidos[chave(n, c)]) k++; return k; };

function aplicar() {
  const r = document.documentElement;
  if (cfg.theme === 'auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', cfg.theme);
  r.style.setProperty('--fs', cfg.fs);
  document.body.classList.toggle('nox', !cfg.ctx);
}

/* ---------- carregamento dos dados do livro ---------- */
window.__B = window.__B || {};
const cache = {};
function carregar(n) {
  if (window.__B[n]) return Promise.resolve(window.__B[n]);
  if (cache[n]) return cache[n];
  return cache[n] = new Promise((ok, no) => {
    const s = document.createElement('script');
    s.src = `data/${String(n).padStart(2, '0')}.js`;
    s.onload = () => ok(window.__B[n]);
    s.onerror = () => { delete cache[n]; no(new Error('Falha ao carregar o livro ' + n)); };
    document.head.appendChild(s);
  });
}

/* ---------- navegação (hash) ---------- */
const view = $('#view'), title = $('#title'), back = $('#btnBack');
function ir(h) { if (location.hash === h) rota(); else location.hash = h; }
window.addEventListener('hashchange', rota);
back.onclick = () => { if (history.length > 1 && /^#\/ler\/\d+\/\d+\/\d+/.test(location.hash)) { history.back(); return; } const p = (location.hash.match(/^#\/ler\/(\d+)/) || [])[1]; ir(p ? '#/livro/' + p : '#/'); };
$('#btnSearch').onclick = () => ir('#/buscar');
$('#btnCfg').onclick = () => abrirCfg();

function rota() {
  fechaPop();
  const h = location.hash || '#/';
  let m;
  if ((m = h.match(/^#\/ler\/(\d+)\/(\d+)(?:\/(\d+))?$/))) return telaLeitura(+m[1], +m[2], m[3] ? +m[3] : 0);
  if (h === '#/buscar') return telaBusca();
  if ((m = h.match(/^#\/livro\/(\d+)$/))) return telaLivro(+m[1]);
  telaHome();
}
const tema = n => document.body.dataset.t = n ? L[n - 1].t : 'AT';
const topo = () => window.scrollTo(0, 0);

/* ---------- Home ---------- */
function telaHome() {
  tema(0); back.hidden = true; title.textContent = 'Bíblia Interlinear';
  document.querySelector('meta[name=theme-color]').content = '#7a3b1c';
  const lidoTot = Object.keys(lidos).length, pct = Math.round(100 * lidoTot / TOTAL_CAPS);
  const cont = ultimo && L[ultimo.n - 1]
    ? `<button class="btn alt" id="cont" style="width:100%;justify-content:center;margin:10px 0 0">▶ Continuar: ${esc(L[ultimo.n - 1].nome)} ${ultimo.c}</button>` : '';
  const lista = L.filter(b => b.t === cfg.tab).map(b => {
    const k = livroLidos(b.n);
    return `<button class="book" data-t="${b.t}" data-n="${b.n}"><b>${esc(b.nome)}</b><span class="o" dir="${b.t === 'AT' ? 'rtl' : 'ltr'}">${esc(b.o)}</span><small>${esc(b.tr)} · ${k}/${b.caps}</small><div class="pg"><i style="width:${100 * k / b.caps}%"></i></div></button>`;
  }).join('');
  view.innerHTML = `<div class="hero"><b>${lidoTot} de ${TOTAL_CAPS} capítulos lidos</b><small>${pct}% da Bíblia</small><div class="bar"><i style="width:${pct}%"></i></div></div>${cont}
    <div class="tabs"><button class="tab ${cfg.tab === 'AT' ? 'on' : ''}" data-k="AT">Antigo Testamento</button><button class="tab ${cfg.tab === 'NT' ? 'on' : ''}" data-k="NT">Novo Testamento</button></div>
    <div class="books">${lista}</div>
    <p style="text-align:center;margin-top:26px"><a href="referencias.html" style="color:var(--mut)">📚 Referências e fontes</a></p>
    <p class="vf">Bíblia Interlinear · versão ${esc(META.versao)}<br>por ${esc(META.autor)}</p>`;
  view.querySelectorAll('.tab').forEach(b => b.onclick = () => { cfg.tab = b.dataset.k; store.set('cfg', cfg); telaHome(); });
  view.querySelectorAll('.book').forEach(b => b.onclick = () => ir('#/livro/' + b.dataset.n));
  const c = $('#cont'); if (c) c.onclick = () => ir(`#/ler/${ultimo.n}/${ultimo.c}`);
}

/* ---------- Livro: grade de capítulos ---------- */
function telaLivro(n) {
  const b = L[n - 1]; if (!b) return ir('#/');
  tema(n); back.hidden = false; title.textContent = b.nome;
  const k = livroLidos(n);
  const caps = Array.from({ length: b.caps }, (_, i) => i + 1).map(c =>
    `<button class="cap ${lidos[chave(n, c)] ? 'lido' : ''}" data-c="${c}">${c}</button>`).join('');
  view.innerHTML = `<div class="hd"><span class="o" dir="${b.t === 'AT' ? 'rtl' : 'ltr'}">${esc(b.o)}</span><span class="tr">${esc(b.tr)}</span><span class="lit">${esc(b.lit)}</span>
    <small style="color:var(--mut)">${b.t === 'AT' ? 'Hebraico/aramaico — da direita para a esquerda' : 'Grego koiné — da esquerda para a direita'} · ${k}/${b.caps} lidos</small></div>
    <div class="caps">${caps}</div>
    <div class="foot"><div class="row"><button class="btn ghost" id="todos">Marcar todos como lidos</button><button class="btn ghost" id="nenhum">Limpar</button></div></div>`;
  view.querySelectorAll('.cap').forEach(e => {
    let t, longo = false;
    e.onpointerdown = () => { longo = false; t = setTimeout(() => { longo = true; alternar(n, +e.dataset.c); e.classList.toggle('lido'); navigator.vibrate && navigator.vibrate(15); }, 550); };
    const fim = () => clearTimeout(t);
    e.onpointerup = fim; e.onpointerleave = fim; e.onpointercancel = fim;
    e.onclick = () => { if (!longo) ir(`#/ler/${n}/${e.dataset.c}`); };
  });
  $('#todos').onclick = () => { for (let c = 1; c <= b.caps; c++) lidos[chave(n, c)] = Date.now(); salvarLidos(); telaLivro(n); };
  $('#nenhum').onclick = () => { if (!confirm('Limpar as marcações de leitura deste livro?')) return; for (let c = 1; c <= b.caps; c++) delete lidos[chave(n, c)]; salvarLidos(); telaLivro(n); };
  const hint = document.createElement('p'); hint.style.cssText = 'text-align:center;color:var(--mut);font-size:.85rem'; hint.textContent = 'Toque para ler · segure para marcar/desmarcar como lido';
  view.appendChild(hint);
}
function alternar(n, c) { const k = chave(n, c); if (lidos[k]) delete lidos[k]; else lidos[k] = Date.now(); salvarLidos(); }

/* ---------- Leitura ---------- */
const vizinho = (n, c, d) => {
  c += d;
  if (c < 1) { if (n <= 1) return null; return { n: n - 1, c: L[n - 2].caps }; }
  if (c > L[n - 1].caps) { if (n >= L.length) return null; return { n: n + 1, c: 1 }; }
  return { n, c };
};
let lendo = null;
/* separa a glosa completa do dicionário nas opções de tradução (corta em , ou ; fora de parênteses/colchetes) */
function opcoes(full) {
  const r = []; let n = 0, a = 0;
  for (let i = 0; i <= full.length; i++) {
    const c = full[i];
    if (c === '(' || c === '[') n++; else if (c === ')' || c === ']') n--;
    if (i === full.length || ((c === ',' || c === ';') && n === 0)) { const t = full.slice(a, i).trim(); if (t && !r.includes(t)) r.push(t); a = i + 1; }
  }
  return r;
}
const ic = (w, v, i) => (cfg.opc && w[6]) ? `<i class="op" role="button" aria-label="Ver opções de tradução" data-o="${v}.${i}">▾</i>` : '';

async function telaLeitura(n, c, vAlvo) {
  const b = L[n - 1]; if (!b || c < 1 || c > b.caps) return ir('#/');
  tema(n); back.hidden = false; title.textContent = `${b.nome} ${c}`;
  document.querySelector('meta[name=theme-color]').content = b.t === 'AT' ? '#7a3b1c' : '#12457d';
  ultimo = { n, c }; store.set('ultimo', ultimo); lendo = { n, c };
  view.innerHTML = '<p class="msg">Carregando…</p>'; if (!vAlvo) topo();
  let dados;
  try { dados = await carregar(n); } catch (e) { view.innerHTML = `<p class="msg">${esc(e.message)}. Se abriu o arquivo direto do celular, abra pelo index.html na mesma pasta de <code>data/</code>.</p>`; return; }
  if (!lendo || lendo.n !== n || lendo.c !== c) return;
  const rtl = b.t === 'AT', lang = rtl ? 'he' : 'el';
  const camadas = [['orig', 'o'], ['tr', 't'], ['gl', 'g'], ['mf', 'm']].filter(([k]) => cfg[k]);
  const idx = { o: 0, t: 1, g: 2, m: 3 };
  const vs = (dados[c - 1] || []).map(([ver, words, arc]) => {
    let corpo = '';
    if (camadas.length === 1) {
      const [, cl] = camadas[0];
      corpo = `<div class="run ${cl === 'o' ? lang : cl === 't' ? 'tr' : cl === 'g' ? 'g' : ''}" ${cl === 'o' && rtl ? 'dir="rtl" lang="he"' : cl === 'o' ? 'lang="el"' : ''}>` +
        words.map((w, i) => `<span class="rw ${esc(w[5])}" data-w="${ver}.${i}">${esc(w[idx[cl]])}</span>${cl === 'g' ? ic(w, ver, i) : ''}`).join(' ') + '</div>';
    } else if (camadas.length > 1) {
      corpo = `<div class="ws" dir="${rtl ? 'rtl' : 'ltr'}" lang="${lang}">` + words.map((w, i) =>
        `<div class="w ${esc(w[5])}" data-w="${ver}.${i}">` + camadas.map(([, cl]) => cl === 'g' ? `<span class="g">${esc(w[2])}${ic(w, ver, i)}</span>` : `<span class="${cl}">${esc(w[idx[cl]])}</span>`).join('') + '</div>').join('') + '</div>';
    }
    const a = cfg.arc ? `<div class="arc" lang="pt-BR"><b>ARC</b>${arc ? esc(arc) : '<span style="color:var(--mut)">—</span>'}</div>` : '';
    return `<div class="v" data-v="${ver}">${cfg.vnum ? `<span class="nv">${ver}</span>` : ''}<div class="vb">${corpo}${a}</div></div>`;
  }).join('');
  const prev = vizinho(n, c, -1), next = vizinho(n, c, 1), ok = !!lidos[chave(n, c)];
  const aviso = (!camadas.length && !cfg.arc) ? '<p class="msg">Nenhuma camada ativa. Abra ⚙ e escolha o que ler.</p>' : '';
  view.innerHTML = `<div class="chap-h"><h3>${esc(b.nome)} ${c}</h3><button class="btn ${ok ? 'done' : 'alt'}" id="mk">${ok ? '✓ Lido' : 'Marcar como lido'}</button></div>${aviso}${vs}
    <div class="foot"><button class="btn ${ok ? 'done' : ''}" id="mk2">${ok ? '✓ Capítulo lido (toque para desmarcar)' : '✓ Marcar como lido e seguir'}</button>
    <div class="row"><button class="btn ghost" id="pv" ${prev ? '' : 'disabled'}>‹ Anterior</button><button class="btn ghost" id="nx" ${next ? '' : 'disabled'}>Próximo ›</button></div></div>`;
  if (vAlvo) { const el = view.querySelector(`.v[data-v="${vAlvo}"]`); if (el) { el.scrollIntoView({ block: 'center' }); el.classList.add('flash'); } else topo(); }
  const marcar = seguir => {
    const ja = !!lidos[chave(n, c)];
    if (ja) { alternar(n, c); telaLeitura(n, c); return; }
    alternar(n, c);
    if (seguir && next) ir(`#/ler/${next.n}/${next.c}`); else telaLeitura(n, c);
  };
  $('#mk').onclick = () => marcar(false); $('#mk2').onclick = () => marcar(true);
  if (prev) $('#pv').onclick = () => ir(`#/ler/${prev.n}/${prev.c}`);
  if (next) $('#nx').onclick = () => ir(`#/ler/${next.n}/${next.c}`);
  view.onclick = e => {
    const op = e.target.closest('.op');
    if (op) {
      const [v, i] = op.dataset.o.split('.').map(Number);
      const ver = dados[c - 1].find(x => x[0] === v); if (ver) mostraOpcoes(ver[1][i], rtl, lang);
      return;
    }
    const el = e.target.closest('[data-w]'); if (!el) return;
    const [v, i] = el.dataset.w.split('.').map(Number);
    const ver = dados[c - 1].find(x => x[0] === v); if (!ver) return;
    mostraPop(ver[1][i], rtl, lang);
  };
}

/* ---------- Detalhe da palavra ---------- */
const pop = $('#pop');
function fechaPop() { pop.hidden = true; }
function mostraPop(w, rtl, lang) {
  pop.innerHTML = `<button class="pc x" aria-label="Fechar" style="float:right;border:0;background:none;font-size:1.3rem;color:var(--mut)">✕</button>
    <span class="o" dir="${rtl ? 'rtl' : 'ltr'}" lang="${lang}" style="font-family:${rtl ? '"SBL Hebrew","Ezra SIL","Noto Serif Hebrew",serif' : '"SBL Greek","Gentium Plus",serif'}">${esc(w[0])}</span>
    <span class="t">${esc(w[1])}</span><b>${esc(w[2])}</b><p>${esc(w[3])}</p>${w[4] ? `<p>${esc(w[4])}</p>` : ''}`;
  pop.hidden = false; pop.querySelector('.pc').onclick = fechaPop;
}
function mostraOpcoes(w, rtl, lang) {
  const lista = opcoes(w[6]), gl = w[2].toLowerCase();
  const norm = t => t.toLowerCase().replace(/\(.*?\)/g, '').replace(/[\[\]]/g, '').trim();
  const marca = lista.map(o => { const n = norm(o); return !!n && gl.includes(n); });
  if (!marca.some(Boolean)) marca.fill(false);
  pop.innerHTML = `<button class="pc x" aria-label="Fechar" style="float:right;border:0;background:none;font-size:1.3rem;color:var(--mut)">✕</button>
    <span class="o" dir="${rtl ? 'rtl' : 'ltr'}" lang="${lang}" style="font-family:${rtl ? '"SBL Hebrew","Ezra SIL","Noto Serif Hebrew",serif' : '"SBL Greek","Gentium Plus",serif'}">${esc(w[0])}</span>
    <span class="t">${esc(w[1])}</span><p style="margin:8px 0 4px"><b style="color:var(--ink)">Opções de tradução (dicionário)</b></p>
    <ol class="opl">${lista.map((o, k) => `<li class="${marca[k] ? 'sel' : ''}">${esc(o)}${marca[k] ? ' <small>← usada aqui</small>' : ''}</li>`).join('')}</ol>
    <p>Exibida: <b style="color:var(--ink)">${esc(w[2])}</b></p>${/\[[ABC]\]/.test(w[4]) ? `<p>${esc(w[4])}</p>` : ''}`;
  pop.hidden = false; pop.querySelector('.pc').onclick = fechaPop;
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { fechaPop(); fechaCfg(); fechaSobre(); }
  if (!lendo || !/^#\/ler\//.test(location.hash) || /INPUT|TEXTAREA/.test(document.activeElement.tagName)) return;
  const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
  if (d) { const v = vizinho(lendo.n, lendo.c, d); if (v) ir(`#/ler/${v.n}/${v.c}`); }
});

/* ---------- Configurações ---------- */
const sheet = $('#sheet');
const fechaCfg = () => sheet.hidden = true;
sheet.addEventListener('click', e => { if (e.target.hasAttribute('data-close')) fechaCfg(); });
function sw(k, nome, desc) { return `<div class="opt"><div>${nome}${desc ? `<small>${desc}</small>` : ''}</div><button class="sw" role="switch" data-k="${k}" aria-checked="${!!cfg[k]}" aria-label="${esc(nome)}"></button></div>`; }
function abrirCfg() {
  $('#cfgBody').innerHTML = `
  <h4>O que mostrar em cada palavra</h4>
  ${sw('orig', 'Texto original', 'Hebraico/aramaico (AT) ou grego (NT)')}
  ${sw('tr', 'Transliteração', 'Como se lê, em letras latinas')}
  ${sw('gl', 'Tradução interlinear', 'Glosa palavra por palavra (dicionário)')}
  ${sw('mf', 'Morfologia', 'Classe gramatical, tempo, caso…')}
  <h4>Tradução corrida</h4>
  ${sw('arc', 'Almeida Revista e Corrigida (ARC)', 'Linha abaixo de cada versículo')}
  <h4>Leitura</h4>
  ${sw('vnum', 'Números dos versículos')}
  ${sw('opc', 'Ícone ▾ de opções de tradução', 'Aparece nas palavras com mais de um sentido no dicionário')}
  ${sw('ctx', 'Sublinhar sentidos escolhidos pelo contexto', 'Pontilhado: verde = pela forma · âmbar = pelo contexto · roxo = expressão')}
  <div class="opt"><div>Tamanho do texto<small id="fsv">${Math.round(cfg.fs * 100)}%</small></div></div>
  <input type="range" id="fs" min="0.8" max="1.8" step="0.05" value="${cfg.fs}">
  <div class="opt"><div>Tema</div><div class="seg" id="th">${[['auto', 'Auto'], ['light', 'Claro'], ['dark', 'Escuro']].map(([v, n]) => `<button data-v="${v}" class="${cfg.theme === v ? 'on' : ''}">${n}</button>`).join('')}</div></div>
  <h4>Progresso de leitura (backup)</h4>
  <p style="color:var(--mut);font-size:.9rem;margin:4px 0 10px">As marcações ficam só neste aparelho. Para levar a outro dispositivo, copie o código abaixo e cole no outro (Importar).</p>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px"><button class="btn alt" id="cp">📋 Copiar código</button><button class="btn alt" id="pt">📥 Importar código colado</button>${EMBUTIDO ? '' : '<button class="btn alt" id="exp">⬇ Baixar arquivo</button><label class="btn alt" style="cursor:pointer">⬆ Abrir arquivo<input type="file" id="imp" accept="application/json" hidden></label>'}<button class="btn ghost" id="rst">Restaurar padrões</button></div>
  <textarea id="code" rows="3" placeholder="Cole aqui o código exportado de outro aparelho" style="width:100%;font:.8rem monospace;border:1px solid var(--line);border-radius:10px;padding:8px;background:var(--bg);color:var(--ink)"></textarea>
  <p style="margin-top:18px"><a href="referencias.html" style="color:var(--mut)">📚 Referências e fontes</a></p>`;
  sheet.hidden = false;
  $('#cfgBody').querySelectorAll('.sw').forEach(b => b.onclick = () => {
    const k = b.dataset.k; cfg[k] = !cfg[k]; b.setAttribute('aria-checked', cfg[k]); salvarCfg(); recarrega();
  });
  $('#fs').oninput = e => { cfg.fs = +e.target.value; $('#fsv').textContent = Math.round(cfg.fs * 100) + '%'; salvarCfg(); };
  $('#th').querySelectorAll('button').forEach(b => b.onclick = () => { cfg.theme = b.dataset.v; salvarCfg(); $('#th').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); });
  const dados = () => JSON.stringify({ app: 'biblia-interlinear', v: 1, lidos, ultimo, cfg });
  const aplicarImport = txt => { try { const j = JSON.parse(txt); if (j.app !== 'biblia-interlinear') throw 0;
      lidos = Object.assign({}, lidos, j.lidos || {}); ultimo = j.ultimo || ultimo; if (j.cfg) cfg = Object.assign({}, DEF, j.cfg);
      salvarLidos(); store.set('ultimo', ultimo); salvarCfg(); alert('Progresso importado.'); fechaCfg(); rota(); } catch (x) { alert('Código inválido.'); } };
  $('#cp').onclick = () => { const t = $('#code'); t.value = dados(); t.select(); let ok = false; try { ok = document.execCommand('copy'); } catch (e) { }
    if (!ok && navigator.clipboard) navigator.clipboard.writeText(t.value).then(() => ok = true, () => { }); alert(ok ? 'Código copiado.' : 'Selecione o texto da caixa e copie.'); };
  $('#pt').onclick = () => { const v = $('#code').value.trim(); if (!v) return alert('Cole o código na caixa primeiro.'); aplicarImport(v); };
  if ($('#exp')) {
    $('#exp').onclick = () => {
      const blob = new Blob([dados()], { type: 'application/json' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'biblia-progresso.json'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    };
    $('#imp').onchange = e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => aplicarImport(r.result); r.readAsText(f); };
  }
  $('#rst').onclick = () => { cfg = Object.assign({}, DEF); salvarCfg(); abrirCfg(); recarrega(); };
}
function recarrega() { if (/^#\/ler\//.test(location.hash)) { const [, n, c] = location.hash.match(/#\/ler\/(\d+)\/(\d+)/); const y = scrollY; telaLeitura(+n, +c).then(() => scrollTo(0, y)); } }

/* ---------- Busca na ARC ---------- */
let arcPronto = null;
function carregarArc() {
  if (window.__ARC && window.__ARCN) return Promise.resolve();
  if (arcPronto) return arcPronto;
  return arcPronto = new Promise((ok, no) => {
    const fim = () => {
      if (!window.__ARCN) window.__ARCN = window.__ARC.map(b => b.map(r => ' ' + norm(r[2]) + ' '));
      ok();
    };
    if (window.__ARC) return fim();
    const s = document.createElement('script'); s.src = 'data/arc.js'; s.onload = fim;
    s.onerror = () => { arcPronto = null; no(new Error('Falha ao carregar o índice da ARC')); };
    document.head.appendChild(s);
  });
}
const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, ' ');
const ACENTOS = { a: 'aáàâãä', e: 'eéèêë', i: 'iíìîï', o: 'oóòôõö', u: 'uúùûü', c: 'cç', n: 'nñ' };
const rxTok = t => t.split('').map(ch => { const b = norm(ch); const k = ACENTOS[b]; return k ? '[' + k + k.toUpperCase() + ']' : ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('');
let bs = Object.assign({ q: '', esc: 'todos', modo: 'todas' }, store.get('busca', {}));
const seg = (id, ops, atual) => `<div class="seg" id="${id}">${ops.map(([v, n]) => `<button data-v="${v}" class="${atual === v ? 'on' : ''}">${n}</button>`).join('')}</div>`;

async function telaBusca() {
  tema(0); back.hidden = false; title.textContent = 'Buscar na ARC'; topo();
  view.innerHTML = `<div class="sbox"><div class="sin"><input id="q" type="search" enterkeyhint="search" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Digite palavra ou frase…" value="${esc(bs.q)}" aria-label="Texto a buscar"></div>
    <div class="sopt">${seg('sc', [['todos', 'Bíblia toda'], ['AT', 'Antigo'], ['NT', 'Novo']], bs.esc)}${seg('sm', [['todas', 'Todas as palavras'], ['frase', 'Frase exata']], bs.modo)}</div></div>
    <div id="sres"><p class="msg">Carregando índice…</p></div>`;
  const q = $('#q'), res = $('#sres');
  try { await carregarArc(); } catch (e) { res.innerHTML = `<p class="msg">${esc(e.message)}.</p>`; return; }
  let timer = 0, pag = 100, achados = [], rx = null;
  const faz = () => {
    bs.q = q.value; store.set('busca', bs);
    const termo = norm(q.value.trim());
    if (termo.length < 2) { res.innerHTML = '<p class="msg">Busca no texto da Almeida Revista e Corrigida (ARC). Ignora acentos e maiúsculas.<br>Digite ao menos 2 letras.</p>'; return; }
    const toks = bs.modo === 'frase' ? [termo] : termo.split(' ').filter(Boolean);
    const de = bs.esc === 'NT' ? 40 : 1, ate = bs.esc === 'AT' ? 39 : 66;
    achados = [];
    for (let n = de; n <= ate; n++) {
      const N = window.__ARCN[n - 1], R = window.__ARC[n - 1];
      for (let i = 0; i < N.length; i++) { const t = N[i]; let ok = true; for (const k of toks) if (!t.includes(k.length > 2 || bs.modo === 'frase' ? k : ' ' + k + ' ')) { ok = false; break; } if (ok) achados.push([n, R[i]]); }
    }
    rx = new RegExp('(' + toks.map(t => { const p = t.split(' ').map(rxTok).join('[^\\p{L}\\p{N}]+'); return t.length > 2 || bs.modo === 'frase' ? p : '(?<![\\p{L}\\p{N}])' + p + '(?![\\p{L}\\p{N}])'; }).join('|') + ')', 'giu');
    pag = 100; mostra();
  };
  const mostra = () => {
    if (!achados.length) { res.innerHTML = `<p class="msg">Nenhum versículo encontrado para “${esc(q.value.trim())}”.</p>`; return; }
    const lista = achados.slice(0, pag).map(([n, r]) => {
      const b = L[n - 1], txt = esc(r[2]).replace(rx, '<mark>$1</mark>');
      return `<button class="res" data-t="${b.t}" data-n="${n}" data-c="${r[3] || r[0]}" data-v="${r[3] ? r[4] : r[1]}"><b>${esc(b.nome)} ${r[0]}:${r[1]}</b>${txt}</button>`;
    }).join('');
    res.innerHTML = `<p class="scount">${fmt(achados.length)} versículo${achados.length > 1 ? 's' : ''} encontrado${achados.length > 1 ? 's' : ''}</p>${lista}` +
      (achados.length > pag ? `<button class="btn alt" id="mais" style="width:100%;justify-content:center;margin:8px 0">Mostrar mais (${fmt(achados.length - pag)})</button>` : '');
    res.querySelectorAll('.res').forEach(e => e.onclick = () => { const v = +e.dataset.v; ir(`#/ler/${e.dataset.n}/${e.dataset.c}` + (v ? '/' + v : '')); });
    const m = $('#mais'); if (m) m.onclick = () => { pag += 100; mostra(); };
  };
  q.oninput = () => { clearTimeout(timer); timer = setTimeout(faz, 300); };
  q.onkeydown = e => { if (e.key === 'Enter') { clearTimeout(timer); faz(); q.blur(); } };
  $('#sc').querySelectorAll('button').forEach(b => b.onclick = () => { bs.esc = b.dataset.v; $('#sc').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); faz(); });
  $('#sm').querySelectorAll('button').forEach(b => b.onclick = () => { bs.modo = b.dataset.v; $('#sm').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); faz(); });
  faz(); if (!bs.q) q.focus();
}

/* ---------- Ajuda e sobre ---------- */
const aboutSheet = $('#about');
const fechaSobre = () => aboutSheet.hidden = true;
aboutSheet.addEventListener('click', e => { if (e.target.hasAttribute('data-close')) fechaSobre(); });
$('#btnAbout').onclick = () => abrirSobre();
const fmt = n => Number(n).toLocaleString('pt-BR');
const LOGO = $('.sp-logo').innerHTML.replace('id="g"', 'id="g2"').replace('url(#g)', 'url(#g2)').replace('width="120" height="120"', 'width="64" height="64"');
const kv = rows => `<table class="kv">${rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join('')}</table>`;
function abrirSobre() {
  const sec = (t, corpo, aberto) => `<details class="ab-sec" ${aberto ? 'open' : ''}><summary>${t}</summary><div class="bd">${corpo}</div></details>`;
  $('#aboutBody').innerHTML = `
  <div class="ab-h">${LOGO}<div><b>Bíblia Interlinear</b><small>Versão ${esc(META.versao)} · por ${esc(META.autor)}</small></div></div>
  <p style="margin:0 0 6px;color:var(--mut);font-size:.92rem">A Bíblia de 66 livros no texto original (hebraico/aramaico e grego), com transliteração, tradução interlinear palavra por palavra e a Almeida Revista e Corrigida. Funciona 100% sem internet.</p>
  ${sec('Como usar', `<ol>
    <li><b>Escolha o livro:</b> na tela inicial, use as abas <i>Antigo</i> e <i>Novo Testamento</i> e toque num livro.</li>
    <li><b>Escolha o capítulo:</b> toque no número para ler. <i>Segure</i> o número para marcar ou desmarcar como lido.</li>
    <li><b>Leia:</b> cada versículo mostra o original, a transliteração, a tradução interlinear e, abaixo, a ARC.</li>
    <li><b>Toque numa palavra</b> para ver original, transliteração, tradução e morfologia (classe gramatical, tempo, caso…).</li>
    <li><b>Toque no ícone ▾</b> ao lado da tradução para ver todas as opções de sentido do dicionário e qual foi usada.</li>
    <li><b>Marque o capítulo como lido</b> no botão do topo ou no fim da página (marca e já segue para o próximo).</li>
    <li><b>Continue de onde parou</b> pelo botão da tela inicial.</li>
    <li><b>Busque no texto</b> pela lupa (canto esquerdo): procure palavras ou frases na ARC, na Bíblia toda ou só no Antigo ou no Novo Testamento; toque no resultado para abrir o versículo.</li></ol>`, true)}
  ${sec('Camadas de leitura (⚙)', `<p>Na engrenagem você liga ou desliga, de forma independente:</p><ul>
    <li><b>Texto original</b> — hebraico (lido da direita para a esquerda) ou grego;</li><li><b>Transliteração</b> — como se lê, em letras latinas;</li>
    <li><b>Tradução interlinear</b> — glosa palavra por palavra, em português;</li><li><b>Morfologia</b> — análise gramatical de cada palavra;</li>
    <li><b>ARC</b> — tradução corrida abaixo de cada versículo.</li></ul>
    <p>Com apenas uma camada de palavras o texto corre em linha contínua; com duas ou mais, aparece em colunas, palavra sobre palavra. Também há tamanho do texto, tema claro/escuro/automático e números dos versículos.</p>`)}
  ${sec('Sentidos e sublinhados', `<p>Quando o dicionário tem vários sentidos, o app escolhe o que faz sentido na leitura, sem sair das opções do dicionário. O sublinhado pontilhado indica:</p>
    <p class="leg"><i style="color:#2f9e5b"></i>verde — escolhido pela <b>forma gramatical</b>;<br><i style="color:#d99a1e"></i>âmbar — escolhido pelo <b>contexto</b>;<br><i style="color:#8b5fc7"></i>roxo — <b>expressão</b> de várias palavras.</p>
    <p>Dica: palavras com <b>(pl)</b> estão no plural; <b>-de</b> indica estado construto (“X de”); verbos aparecem no infinitivo, com o tempo e a pessoa na linha de morfologia.</p>`)}
  ${sec('Progresso e backup', `<p>Os capítulos lidos ficam salvos neste aparelho. Em ⚙ → <i>Progresso de leitura</i>, use <b>Copiar código</b> para levar a outro aparelho e <b>Importar código colado</b> para restaurar.</p>`)}
  ${sec('Dados técnicos', kv([
    ['Aplicativo', 'Bíblia Interlinear'], ['Versão', esc(META.versao) + (META.build ? ' (compilação ' + esc(META.build) + ')' : '')],
    ['Autor', esc(META.autor)], ['Pacote', 'com.biblia.interlinear'],
    ['Plataforma', 'Android 7.0 ou superior (API 24+)'], ['Tecnologia', 'HTML, CSS e JavaScript em WebView nativo'],
    ['Conteúdo', fmt(META.livros) + ' livros · ' + fmt(META.capitulos) + ' capítulos · ' + fmt(META.versiculos) + ' versículos · ' + fmt(META.palavras) + ' palavras'],
    ['Texto original', 'AT: Westminster Leningrad Codex (OSHB) · NT: SBLGNT (MorphGNT)'],
    ['Tradução corrida', 'Almeida Revista e Corrigida (ARC), edição de 1911 — domínio público'],
    ['Interlinear', 'Glosas de dicionário (OpenScriptures, MorphGNT) traduzidas para o português'],
    ['Funcionamento', '100% offline · sem anúncios · sem coleta de dados · sem permissões'],
    ['Armazenamento', 'Somente no aparelho (progresso e preferências)'],
    ['Busca', 'Texto da ARC 1911 (31.104 versículos), sem diferenciar acentos nem maiúsculas'],
    ['Tela', 'Permanece ligada enquanto o app está aberto'],
    ['Assinatura', 'APK assinado (esquemas v1, v2 e v3)']]))}
  ${sec('Fontes e créditos', `<ul><li>Texto hebraico: Open Scriptures Hebrew Bible (WLC).</li><li>Texto grego: SBL Greek New Testament e MorphGNT.</li>
    <li>Léxicos: Open Scriptures HebrewLexicon, BDB e Strong; MorphGNT lexemes.</li><li>Equivalência de versículos: STEPBible TVTMS.</li>
    <li>Transliteração e organização: regras próprias do projeto.</li></ul><p><a href="referencias.html" style="color:var(--acc)">Ver a lista completa de referências e licenças →</a></p>`)}
  ${sec('Avisos e limitações', `<div class="aviso">As <b>glosas em português</b> foram traduzidas por inteligência artificial a partir de dicionários, não de outra Bíblia, e podem conter imprecisões. Os <b>sentidos escolhidos pelo contexto</b> são uma seleção entre opções do dicionário, não uma interpretação.</div>
    <ul><li>Verbos aparecem no infinitivo; o tempo e a pessoa ficam na linha de morfologia.</li>
    <li>A numeração dos versículos do original difere da ARC em alguns trechos (ex.: títulos de Salmos); onde não há correspondência segura aparece “—”.</li>
    <li>O SBLGNT é texto crítico e difere do <i>Textus Receptus</i> em alguns versículos.</li>
    <li>O texto da ARC está na <b>grafia de 1911</b> (ex.: “fórma”, “abysmo”, “sancto”), sem modernização.</li></ul>`)}
  ${sec('Declaração de Domínio Público', `<div class="aviso" style="border-color:var(--acc)"><b>Termo de Conformidade Legal.</b> O texto bíblico disponibilizado nesta aplicação corresponde à edição de 1911 da Almeida Revista e Corrigida (ARC). Trata-se de uma obra em <b>Domínio Público</b>, isenta de direitos patrimoniais nos termos do Art. 41 c/c Art. 45, I, da Lei Federal nº 9.610/1998 (Brasil), da Convenção de Berna (Art. 7.8) e das legislações internacionais de propriedade intelectual; nos Estados Unidos, obras publicadas antes de 1º de janeiro de 1929 são de domínio público. O texto é utilizado em sua versão integral e sem alterações de conteúdo.</div><ul><li>Fonte: <i>A Biblia Sagrada</i>, trad. João Ferreira d’Almeida, edição revista e corrigida, Deposito das Escripturas Sagradas, Lisboa, 1911 — transcrição do Project Gutenberg (eBook nº 62383), conferida por checksum.</li><li>Foram removidos apenas as chamadas de notas de rodapé e os realces em itálico; cinco fronteiras de versículos da transcrição foram ajustadas à numeração padrão (Jz 5, 1Sm 20, 1Rs 22, 2Co 13, Ap 12), sem alterar as palavras.</li></ul>`)}
  ${sec('Atalhos (computador)', `<ul><li><b>← →</b> capítulo anterior / próximo</li><li><b>Esc</b> fecha janelas</li></ul>`)}
  <p class="vf">Bíblia Interlinear ${esc(META.versao)} · ${esc(META.autor)}</p>`;
  aboutSheet.hidden = false;
}

/* ---------- abertura (fecha só no botão), tela ligada ---------- */
(function () {
  const sp = $('#splash'), ok = $('#spok');
  $('#spv').textContent = 'versão ' + META.versao + ' · ' + META.autor;
  const ab = META.abertura;
  if (ab && ab.he) $('#spcard').innerHTML = ab.he.map((h, i) => `<p class="he" lang="he" dir="rtl">${esc(h)}</p><p class="pt" lang="pt-BR"><b>${i + 1}</b>${esc(ab.arc[i])}</p>`).join('') + `<figcaption>${esc(ab.ref)}</figcaption>`;
  else $('#spcard').remove();
  const fechar = () => { sp.classList.add('out'); document.removeEventListener('keydown', tecla); setTimeout(() => sp.remove(), 600); };
  const tecla = e => { if (e.key === 'Enter' || e.key === 'Escape') fechar(); };
  ok.onclick = fechar; document.addEventListener('keydown', tecla);
  try { ok.focus({ preventScroll: true }); } catch (e) { }
  /* mantém a tela ligada (navegadores com Wake Lock; no APK o Android já faz isso nativamente) */
  let wl = null;
  const pedir = async () => { try { if ('wakeLock' in navigator && document.visibilityState === 'visible') wl = await navigator.wakeLock.request('screen'); } catch (e) { } };
  document.addEventListener('visibilitychange', pedir); pedir();
})();
aplicar(); rota();
