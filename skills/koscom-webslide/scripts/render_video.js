// 요약 모션(video/summary.html) → mp4. 모든 애니메이션을 프레임마다 멈춰 찍고 ffmpeg로 묶는다(결정적 녹화).
//   1) 덱 폴더를 웹 서버로 연다:  python -m http.server 8765 --directory <덱 폴더>
//   2) node render_video.js qa    [초,초,...]   → <덱>/video/qa/*.jpg (장면 점검용 정지 화면)
//      node render_video.js video [출력.mp4]   → 1920×1080 30fps, 기본 <덱>/assets/video/summary.mp4
// 환경 변수: BASE(기본 http://localhost:8765) · DECK(덱 폴더, qa 저장 위치) · FPS(30) · CRF(24) · BROWSER=chrome
// 필요: playwright-core(npm i playwright-core), ffmpeg(PATH)
const fs = require('fs');
const path = require('path');
const {spawnSync} = require('child_process');
const pw = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const BASE = process.env.BASE || 'http://localhost:8765';
const DECK = path.resolve(process.env.DECK || '.');
const FPS = +(process.env.FPS || 30), CRF = String(process.env.CRF || 24);

async function open(browser) {
  const page = await browser.newPage({viewport: {width: 1920, height: 1080}, deviceScaleFactor: 1});
  page.on('pageerror', e => console.error('PAGE ERROR:', e.message));
  await page.goto(`${BASE}/video/summary.html?capture=1`, {waitUntil: 'load'});
  await page.waitForFunction(() => window.__ready === true, null, {timeout: 60000});
  return page;
}

(async () => {
  const mode = process.argv[2] || 'qa';
  const browser = await pw.chromium.launch({channel: process.env.BROWSER === 'chrome' ? 'chrome' : 'msedge', headless: true});
  try {
    const page = await open(browser);
    const DUR = await page.evaluate(() => window.motion?.dur || 60);
    if (mode === 'qa') {
      const times = (process.argv[3] || Array.from({length: Math.ceil(DUR / 6)}, (_, i) => i * 6 + 3).join(',')).split(',').map(Number);
      const dir = path.join(DECK, 'video', 'qa');
      fs.mkdirSync(dir, {recursive: true});
      for (const t of times) {
        await page.evaluate(v => window.renderAt(v), t);
        await page.screenshot({path: path.join(dir, `t${String(t).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 80});
      }
      console.log('qa →', dir, times.join(' '));
    } else {
      const out = path.resolve(process.argv[3] || path.join(DECK, 'assets', 'video', 'summary.mp4'));
      const frames = path.join(DECK, 'video', 'frames');
      fs.rmSync(frames, {recursive: true, force: true});
      fs.mkdirSync(frames, {recursive: true});
      const total = Math.round(FPS * DUR);
      for (let i = 0; i < total; i++) {
        await page.evaluate(v => window.renderAt(v), i / FPS);
        await page.screenshot({path: path.join(frames, `f${String(i).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 92});
        if (i % 300 === 0) console.log(`frame ${i}/${total}`);
      }
      fs.mkdirSync(path.dirname(out), {recursive: true});
      // 원본 프레임에서 한 번만 압축한다(이미 압축한 mp4를 다시 압축하면 손실이 겹친다)
      const r = spawnSync('ffmpeg', ['-y', '-framerate', String(FPS), '-i', path.join(frames, 'f%05d.jpg'), '-vf', 'scale=in_range=full:out_range=tv,format=yuv420p',
        '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', CRF, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], {stdio: 'inherit'});
      if (r.status !== 0) throw new Error('ffmpeg 실패');
      spawnSync('ffmpeg', ['-y', '-i', path.join(frames, `f${String(FPS * 3).padStart(5, '0')}.jpg`), '-q:v', '3', out.replace(/\.mp4$/, '-poster.jpg')], {stdio: 'ignore'});
      fs.rmSync(frames, {recursive: true, force: true});
      console.log('video →', out, `${(fs.statSync(out).size / 1e6).toFixed(1)}MB`);
    }
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
