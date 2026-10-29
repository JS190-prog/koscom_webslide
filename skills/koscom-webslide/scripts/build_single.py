"""덱 폴더(index.html + assets/ + video/summary.html) → 그림·서체·Chart.js·요약 모션까지 넣은 단일 HTML 파일.

    python build_single.py <덱 폴더> <출력.html> [--max-mb 9.5] [--referenced-only]

- 서체: scripts/vendor/KoPubDotum-*.woff2 (자주 쓰는 한글 2,350자 + 덱 글자. 새 글자가 생기면 subset_fonts.py)
- 그림: index.html·summary.html에 적힌 경로와 삽화 레이어를 #asset-map에 넣고, 화면에서는 data-asset으로 바꿔 읽는다
- 요약 영상: mp4를 넣지 않는다. video/summary.html(모션 원본)을 #motion-src로 넣어 부록 E에서 그대로 재생 — 용량↓ 선명도↑
- --referenced-only: 쓰지 않는 삽화 레이어는 뺀다(편집 모드에서 다른 삽화로 바꿀 일이 없을 때)
"""
import argparse
import base64
import glob
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding='utf-8', errors='replace')
ap = argparse.ArgumentParser()
ap.add_argument('deck')
ap.add_argument('out')
ap.add_argument('--vendor', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor'))
ap.add_argument('--max-mb', type=float, default=9.5)
ap.add_argument('--referenced-only', action='store_true')
a = ap.parse_args()
ROOT = a.deck
s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
MIME = {'.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.gif': 'image/gif'}
PIX = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='


def b64(path):
    return f'data:{MIME[os.path.splitext(path)[1].lower()]};base64,' + base64.b64encode(open(path, 'rb').read()).decode()


# 1) 서체
for w in ('Medium', 'Bold'):
    old = f"url(assets/fonts/KoPubDotum-{w}.ttf) format('truetype')"
    if old in s:
        s = s.replace(old, f"url(data:font/woff2;base64,{base64.b64encode(open(os.path.join(a.vendor, f'KoPubDotum-{w}.woff2'), 'rb').read()).decode()}) format('woff2')")

# 2) Chart.js
cdn = re.search(r'<script src="https://cdnjs[^"]+chart\.umd\.min\.js"></script>\n<script>window\.Chart \|\|[^\n]*</script>\n', s)
if cdn:
    chart = open(os.path.join(a.vendor, 'chart.umd.min.js'), encoding='utf-8').read().replace('</script', '<\\/script')
    s = s[:cdn.start()] + '<script>/*! Chart.js v4.4.1 | MIT License | chartjs.org */\n' + chart + '\n</script>\n' + s[cdn.end():]

# 3) 쓰는 그림 모으기
mo_path = os.path.join(ROOT, 'video', 'summary.html')
mo = open(mo_path, encoding='utf-8').read() if os.path.exists(mo_path) and 'id="sumMotion"' in s else ''
refs = set(re.findall(r'(?:src|poster)="(assets/[^"]+)"', s)) | {p[3:] for p in re.findall(r'src="(\.\./assets/[^"]+)"', mo)}
illu_all = {os.path.basename(f)[:-5] for f in glob.glob(f'{ROOT}/assets/illust/*.webp')}
if a.referenced_only:
    text = s + mo
    illu = {n for n in illu_all if n in text}
else:
    illu = illu_all            # 편집 모드에서 그림을 바꿔 넣을 수 있게 전부
files = {r for r in refs if not r.endswith('.mp4')}
for n in illu:
    files.add(f'assets/illust/{n}.webp')
    files |= {os.path.relpath(f, ROOT).replace('\\', '/') for f in glob.glob(f'{ROOT}/assets/illust/layers2/{n}/*.webp')}
missing = [f for f in files if not os.path.exists(os.path.join(ROOT, f))]
assert not missing, ('없는 그림', missing[:10])
amap = {f: b64(os.path.join(ROOT, f)) for f in sorted(files)}

# 4) 화면의 경로 → 자리표시 + data-asset (첫 로딩 때 없는 파일을 요청하지 않도록)
s = re.sub(r'<img([^>]*?) src="(assets/[^"]+)"', lambda m: f'<img{m.group(1)} src="{PIX}" data-asset="{m.group(2)}"', s)
s = re.sub(r'<video([^>]*?) src="(assets/[^"]+)" poster="(assets/[^"]+)"', lambda m: f'<video{m.group(1)} data-asset="{m.group(2)}" data-poster="{m.group(3)}"', s)
assert not re.search(r'\s(src|poster)="assets/', s), '바꾸지 못한 경로'
block = '<script type="application/json" id="asset-map">' + json.dumps(amap, separators=(',', ':')) + '</script>\n'

# 5) 요약 모션 원본
if mo:
    mo = re.sub(r"@font-face\{[^}]*\}\n?", '', mo)
    mo = re.sub(r'<img([^>]*?) src="(\.\./assets/[^"]+)"', lambda m: f'<img{m.group(1)} src="{PIX}" data-masset="{m.group(2)}"', mo)
    block += '<script type="text/plain" id="motion-src">' + mo.replace('</script', '<\\/script') + '</script>\n'

anchor = '<script type="application/json" id="deck-data">'
assert anchor in s, 'deck-data 블록이 없음'
s = s.replace(anchor, block + anchor, 1)
open(a.out, 'w', encoding='utf-8').write(s)
mb = os.path.getsize(a.out) / 1e6
print(f'그림 {len(amap)}개 · 삽화 {len(illu)}종 · 모션 {"포함" if mo else "없음"} · {mb:.2f}MB ({mb * 1e6 / 2 ** 20:.2f}MiB)')
if mb > a.max_mb:
    print(f'⚠ {a.max_mb}MB를 넘었습니다 — --referenced-only, 그림 해상도(1600px)·품질(82) 낮추기, 부록 그림 줄이기 순으로 줄이세요')
    sys.exit(2)
