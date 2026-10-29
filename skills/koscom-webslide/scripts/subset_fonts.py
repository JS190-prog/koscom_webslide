"""단일 파일용 서체(woff2)를 다시 줄인다 — 지금 든 글자(자주 쓰는 한글 2,350자 등) + 덱·요약 모션에 새로 쓴 글자.

    python subset_fonts.py <덱 폴더> [--vendor scripts/vendor]

원본 서체는 <덱 폴더>/assets/fonts/KoPubDotum-{Medium,Bold}.ttf. 원본에 없는 글자(—, 이모지 등)는 시스템 서체로 대신 보인다.
"""
import argparse
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding='utf-8', errors='replace')
from fontTools import subset  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('deck')
ap.add_argument('--vendor', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor'))
a = ap.parse_args()
text = ''
for f in ('index.html', os.path.join('video', 'summary.html')):
    p = os.path.join(a.deck, f)
    if os.path.exists(p):
        text += open(p, encoding='utf-8').read()
used = {ord(c) for c in re.sub(r'<[^>]+>', ' ', text) if ord(c) > 32}
for w in ('Medium', 'Bold'):
    out = os.path.join(a.vendor, f'KoPubDotum-{w}.woff2')
    keep = set(TTFont(out).getBestCmap()) if os.path.exists(out) else set()
    src = TTFont(os.path.join(a.deck, 'assets', 'fonts', f'KoPubDotum-{w}.ttf'))
    have = set(src.getBestCmap())
    want = (keep | used) & have
    opt = subset.Options()
    opt.flavor = 'woff2'
    opt.layout_features = ['*']
    sub = subset.Subsetter(opt)
    sub.populate(unicodes=sorted(want))
    sub.subset(src)
    src.flavor = 'woff2'
    src.save(out)
    print(w, len(keep), '→', len(want), '자', os.path.getsize(out) // 1024, 'KB', '| 원본 서체에 없는 글자:', ''.join(sorted(chr(u) for u in used - have if u > 0x2000))[:30])
