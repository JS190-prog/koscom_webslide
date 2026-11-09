// 덱 점검 — 외부 연결을 모두 막고 단일 파일(또는 폴더판 index.html)을 연다.
//   node check_deck.js <파일.html> [--max-mb 10] [--shots <폴더>]
// 확인: 장 넘기기 · 차트 · 부록마다 그림 · 요약 모션 재생 · 편집 모드 켜고 끄기 · 대본(N) · 발표자 보기(S) 넘김 동기화 · 외부 요청 0 · 스크립트 오류 0 · 용량
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
  const ext = [], errs = [], ctx = p.context();   // 발표자 창(팝업)과 그 미리보기도 같은 컨텍스트에서 막고 오류를 모은다
  await ctx.route('**/*', r => { const u = r.request().url(); if (/^(file|data|blob|about):/.test(u)) return r.continue(); ext.push(u); r.abort(); });
  const watch = pg => pg.on('pageerror', e => errs.push((e.stack || e.message).split('\n').slice(0, 2).map(x => x.trim()).join(' @ ')));
  watch(p); ctx.on('page', watch);
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

  // 대본(aside.notes)과 N 펼침
  const withNotes = await p.evaluate(() => [...document.querySelectorAll('.slide')].map((s, i) => s.querySelector('aside.notes')?.textContent.trim() ? i : -1).filter(i => i >= 0));
  let notes = `${withNotes.length}/${N}장`, notesBad = false;
  if (withNotes.length) {
    await p.evaluate(k => deck.go(k), withNotes[0]); await p.waitForTimeout(400);
    await p.keyboard.press('n'); await p.waitForTimeout(200);
    notesBad = await p.evaluate(() => getComputedStyle(document.querySelector('.slide.active aside.notes')).display !== 'block');
    await p.keyboard.press('n');
    notes += notesBad ? ' · N 펼침 실패' : ' · N 펼침 확인';
  }
  // 발표자 보기(S): 미리보기 두 개가 뜨고, 발표자 창에서 넘기면 청중 화면과 미리보기가 함께 넘어가야 한다
  await p.keyboard.press('Home'); await p.waitForTimeout(400);
  let presenter = '';
  try {
    const [pop] = await Promise.all([p.waitForEvent('popup', {timeout: 5000}), p.keyboard.press('s')]);
    const frameIdx = async id => { try { return await (await (await pop.$('#' + id)).contentFrame()).evaluate(() => window.deck ? deck.index : -1); } catch (e) { return -1; } };
    const until = async i => {
      const want = [i, i, Math.min(i + 1, N - 1)].join();
      for (let t = 0; t < 60; t++) {
        if ([await p.evaluate(() => deck.index), await frameIdx('cur'), await frameIdx('nxt')].join() === want) return true;
        await p.waitForTimeout(250);
      }
      return false;
    };
    const steps = [await until(0)];
    if (N > 1) { await pop.keyboard.press('PageDown'); steps.push(await until(1)); await pop.keyboard.press('PageUp'); steps.push(await until(0)); }
    if (shots) await pop.screenshot({path: path.join(shots, 'presenter.png')});
    presenter = steps.every(Boolean) ? '열림 · 넘김 동기화 확인' : `동기화 실패(${steps})`;
    await pop.close();
  } catch (e) { presenter = '열리지 않음: ' + e.message.split('\n')[0]; }
  const presenterBad = !presenter.startsWith('열림 · ');

  const mb = fs.statSync(file).size / 1e6;
  const res = {파일: path.basename(file), 용량MB: +mb.toFixed(2), 장: N, 차트: charts, 부록: sides, 대본: notes, 발표자보기: presenter, 외부요청: ext.length, 오류: [...new Set(errs)]};
  console.log(JSON.stringify(res, null, 1));
  await b.close();
  const bad = ext.length || errs.length || mb > maxMb || notesBad || presenterBad;
  if (bad) console.error(`❌ 확인 필요 — ${ext.length ? '외부 요청 ' : ''}${errs.length ? '스크립트 오류 ' : ''}${mb > maxMb ? `용량 ${maxMb}MB 초과 ` : ''}${notesBad ? '대본 펼침 ' : ''}${presenterBad ? '발표자 보기' : ''}`);
  else console.log('✅ 통과');
  process.exit(bad ? 1 : 0);
})();
