"""템플릿(예시 덱 「코쇠오피스」 기획서)을 복사해 새 덱 폴더를 만든다.

    python new_deck.py <새 폴더> [--title "제목"] [--keep 1,2,8,19,21] [--drop-side qa,gallery,live] [--no-motion] [--list]

- --list       : 템플릿의 장 번호·이름과 부록 목록만 보여 준다
- --keep       : 남길 장 번호(1부터, 표지=1). 생략하면 전부 남긴다. 나머지 장은 지운다(엔진은 장이 빠져도 돈다)
- --drop-side  : 지울 부록(basis·sources·qa·gallery·video·live)
- --no-motion  : 요약 모션(부록 E와 video/)을 뺀다
"""
import argparse
import os
import re
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding='utf-8', errors='replace')
TPL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'template')
ap = argparse.ArgumentParser()
ap.add_argument('dest', nargs='?')
ap.add_argument('--title')
ap.add_argument('--keep')
ap.add_argument('--drop-side', default='')
ap.add_argument('--no-motion', action='store_true')
ap.add_argument('--list', action='store_true')
a = ap.parse_args()

src = open(os.path.join(TPL, 'index.html'), encoding='utf-8').read()
SEC = re.compile(r'\n(?:  <!-- [^\n]*-->\n)?  <section class="slide[\s"].*?</section>\n', re.S)   # slide · slide cover · slide navy …
secs = list(SEC.finditer(src))
labels = [re.search(r'data-label="([^"]*)"', m.group(0)).group(1) for m in secs]
sides = re.findall(r'<aside class="side-page" id="side-([\w-]+)"[^>]*data-label="([^"]*)"', src)
if a.list or not a.dest:
    for i, l in enumerate(labels, 1):
        print(f'{i:2d}  {l}')
    print('부록:', ', '.join(f'{k}({l})' for k, l in sides))
    sys.exit(0)
if os.path.exists(a.dest) and os.listdir(a.dest):
    sys.exit(f'{a.dest} 가 비어 있지 않습니다')

shutil.copytree(TPL, a.dest, dirs_exist_ok=True)
s = src
if a.keep:
    keep = {int(x) for x in a.keep.split(',') if x.strip()}
    for i, m in reversed(list(enumerate(secs, 1))):
        if i not in keep:
            s = s[:m.start()] + '\n' + s[m.end():]
drop = {x.strip() for x in a.drop_side.split(',') if x.strip()} | ({'video'} if a.no_motion else set())
for k in drop:
    s = re.sub(rf'\n  <aside class="side-page" id="side-{k}".*?</aside>', '', s, flags=re.S)
    s = re.sub(rf'<button class="(?:cta ghost|side-link)" data-side="{k}">.*?</button>', '', s)
if a.no_motion:
    shutil.rmtree(os.path.join(a.dest, 'video'), ignore_errors=True)
if a.title:
    s = re.sub(r'<title>[^<]*</title>', f'<title>{a.title}</title>', s, count=1)
open(os.path.join(a.dest, 'index.html'), 'w', encoding='utf-8').write(s)
n = len(SEC.findall(s))
print(f'새 덱: {a.dest} — 장 {n}개, 지운 부록 {sorted(drop) or "없음"}')
print('다음: index.html의 <section class="slide"> 내용과 맨 아래 deck-data(JSON)를 고치고, 브라우저로 열어 확인')
