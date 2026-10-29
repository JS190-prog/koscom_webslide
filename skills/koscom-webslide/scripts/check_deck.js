// 덱 점검 — 외부 연결을 모두 막고 단일 파일(또는 폴더판 index.html)을 연다.
//   node check_deck.js <파일.html> [--max-mb 10] [--shots <폴더>]
// 확인: 장 넘기기 · 차트 · 부록마다 그림 · 요약 모션 재생 · 편집 모드 켜고 끄기 · 외부 요청 0 · 스크립트 오류 0 · 용량
// playwright-core가 필요하다: npm i playwright-core (브라우저는 설치된 Edge/Chrome을 쓴다. BROWSER=chrome 으로 바꿈)
const fs = require('fs');
const path = require('path');
let pw;
try { pw = require(process.env.PLAYWRIGHT_CORE || 'playwright-core'); } catch (e) { console.error('playwright-core를 찾지 못했습니다 — npm i playwright-core 또는 PLAYWRIGHT_CORE=<경로>'); process.exit(3); }
const args = process.argv.slice(2);
const file = path.resolve(args[0] || 'index.html');
const opt = k => { const i = args.indexOf(k); return i > 0 ? args[i + 1] : null; };
const maxMb = +(opt('--max-mb') || 10), shots = opt('--shots');

(async () => {
  const b = await pw.chromium.launch({channel: process.env.BROWSER === 'chrome' ? 'chrome' : 'msedge', headless: true});
  const p = await b.newPage({viewport: {width: 1440, height: 810}});
  const ext = [], errs = [];
  await p.route('**/*', r => { const u = r.request().url(); if (/^(file|data|blob|about):/.test(u)) return r.continue(); ext.push(u); r.abort(); });
  p.on('pageerror', e => errs.push((e.stack || e.message).split('\n').slice(0, 2).map(x => x.trim()).join(' @ ')));
  await p.goto('file:///' + file.replace(/\\/g, '/'), {waitUntil: 'load'});
  await p.waitForTimeout(1800);
  const N = +(await p.evaluate(() => document.getElementById('pgTot')?.textContent || 0));
  if (shots) fs.mkdirSync(shots, {recursive: true});
  for (let i = 1; i <= N; i++) {
    if (shots) { await p.waitForTimeout(1600); await p.screenshot({path: path.join(shots, `s${String(i).padStart(2, '0')}.png`)}); }
    if (i < N) { await p.keyboard.press('ArrowRight'); await p.waitForTimeout(shots ? 200 : 350); }
  }
  const charts = await p.evaluate(() => [...document.querySelectorAll('canvas')].filter(c => c.width > 0).length + '/' + document.querySelectorAll('canvas').length);
  await p.keyboard.press('Home'); await p.waitForTimeout(500);
  const sides = {};
  for (const sd of await p.evaluate(() => [...document.querySelectorAll('.side-page')].map(s => s.dataset.side))) {
    await p.evaluate(s => document.querySelector(`.rail-apx button[data-side="${s}"]`)?.click(), sd);
    await p.waitForTimeout(1200);
    sides[sd] = await p.evaluate(async s => {
      const sp = document.getElementById('side-' + s); sp.querySelectorAll('img').forEach(i => i.loading = 'eager');
      await new Promise(r => setTimeout(r, 1500));
      const im = [...sp.querySelectorAll('img')].filter(i => !i.closest('.lb'));
      return `그림 ${im.filter(i => i.naturalWidth > 1).length}/${im.length}`;
    }, sd);
    if (sd === 'video') { await p.waitForTimeout(3500); sides.video += ' · 모션 ' + await p.evaluate(() => document.querySelector('.vtm')?.textContent + (document.getElementById('sumMotion')?.classList.contains('on') ? ' 재생 중' : ' 멈춤')); }
    if (shots) await p.screenshot({path: path.join(shots, `side-${sd}.png`)});
    await p.keyboard.press('Escape'); await p.waitForTimeout(400);
  }
  await p.keyboard.press('e'); await p.waitForTimeout(500); await p.keyboard.press('e'); await p.waitForTimeout(300);
  const mb = fs.statSync(file).size / 1e6;
  const res = {파일: path.basename(file), 용량MB: +mb.toFixed(2), 장: N, 차트: charts, 부록: sides, 외부요청: ext.length, 오류: [...new Set(errs)]};
  console.log(JSON.stringify(res, null, 1));
  await b.close();
  const bad = ext.length || errs.length || mb > maxMb;
  if (bad) console.error(`❌ 확인 필요 — ${ext.length ? '외부 요청 ' : ''}${errs.length ? '스크립트 오류 ' : ''}${mb > maxMb ? `용량 ${maxMb}MB 초과` : ''}`);
  else console.log('✅ 통과');
  process.exit(bad ? 1 : 0);
})();
