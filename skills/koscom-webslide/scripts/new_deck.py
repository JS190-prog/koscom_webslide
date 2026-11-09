"""템플릿(예시 덱 「코쇠오피스」 기획서)을 복사해 새 덱 폴더를 만든다.

    python new_deck.py <새 폴더> [--title "제목"] [--keep 1,2,8,19,21] [--drop-side qa,gallery,live] [--no-motion] [--list]
                       [--brand 코스콤 --brand-en "KOSCOM" --pill "사업 브리핑"]

- --list       : 템플릿의 장 번호·이름과 부록 목록만 보여 준다
- --keep       : 남길 장 번호(1부터, 표지=1). 생략하면 전부 남긴다. 나머지 장은 지운다(엔진은 장이 빠져도 돈다)
- --drop-side  : 지울 부록(basis·sources·qa·gallery·video·live)
- --no-motion  : 요약 모션(부록 E와 video/)을 뺀다
- --brand · --brand-en · --pill : 상단 바 왼쪽 이름·영문 꼬리, 오른쪽 위 꼬리표
studio.py(브라우저에서 서식 고르기)도 template_parts()·make_deck() 을 그대로 쓴다.
"""
import argparse
import html
import os
import re
import shutil
import sys

TPL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'template')
SEC = re.compile(r'\n(?:  <!-- [^\n]*-->\n)?  <section class="slide[\s"].*?</section>\n', re.S)   # slide · slide cover · slide navy …


def template_parts():
    """템플릿 -> (원문, 장 match 목록, 장 이름 목록, 부록 [(키, 이름)])"""
    src = open(os.path.join(TPL, 'index.html'), encoding='utf-8').read()
    secs = list(SEC.finditer(src))
    labels = [re.search(r'data-label="([^"]*)"', m.group(0)).group(1) for m in secs]
    sides = re.findall(r'<aside class="side-page" id="side-([\w-]+)"[^>]*data-label="([^"]*)"', src)
    return src, secs, labels, sides


def make_deck(dest, title=None, keep=None, drop=(), no_motion=False, brand=None, brand_en=None, pill=None):
    """새 덱 폴더를 만든다. keep: 남길 장 번호(1부터) 집합, None 이면 전부. drop: 지울 부록 키. 반환 (장 수, 지운 부록)."""
    if os.path.exists(dest) and os.listdir(dest):
        raise FileExistsError(f'{dest} 가 비어 있지 않습니다')
    src, secs, _, _ = template_parts()
    shutil.copytree(TPL, dest, dirs_exist_ok=True)
    s = src
    if keep:
        for i, m in reversed(list(enumerate(secs, 1))):
            if i not in keep:
                s = s[:m.start()] + '\n' + s[m.end():]
    drop = set(drop) | ({'video'} if no_motion else set())
    for k in drop:
        s = re.sub(rf'\n  <aside class="side-page" id="side-{k}".*?</aside>', '', s, flags=re.S)
        s = re.sub(rf'<button class="(?:cta ghost|side-link)" data-side="{k}">.*?</button>', '', s)
    if 'video' in drop:
        shutil.rmtree(os.path.join(dest, 'video'), ignore_errors=True)
    esc = html.escape
    if title:
        s = re.sub(r'<title>[^<]*</title>', lambda m: f'<title>{esc(title)}</title>', s, count=1)
    if brand or brand_en:
        s = re.sub(r'(<div class="brand">\s*<svg.*?</svg>\s*).*?(\s*</div>)',
                   lambda m: f'{m.group(1)}{esc(brand or "")}<span class="div"></span><small>{esc(brand_en or "")}</small>{m.group(2)}',
                   s, count=1, flags=re.S)
    if pill:
        s = re.sub(r'<span class="pill">.*?</span>', lambda m: f'<span class="pill"><i>{esc(pill[:1])}</i>{esc(pill)}</span>', s, count=1)
    open(os.path.join(dest, 'index.html'), 'w', encoding='utf-8').write(s)
    return len(SEC.findall(s)), sorted(drop)


def main():
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('dest', nargs='?')
    ap.add_argument('--title')
    ap.add_argument('--keep')
    ap.add_argument('--drop-side', default='')
    ap.add_argument('--no-motion', action='store_true')
    ap.add_argument('--brand')
    ap.add_argument('--brand-en')
    ap.add_argument('--pill')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    if a.list or not a.dest:
        _, _, labels, sides = template_parts()
        for i, l in enumerate(labels, 1):
            print(f'{i:2d}  {l}')
        print('부록:', ', '.join(f'{k}({l})' for k, l in sides))
        return
    keep = {int(x) for x in a.keep.split(',') if x.strip()} if a.keep else None
    drop = {x.strip() for x in a.drop_side.split(',') if x.strip()}
    try:
        n, dropped = make_deck(a.dest, a.title, keep, drop, a.no_motion, a.brand, a.brand_en, a.pill)
    except FileExistsError as e:
        sys.exit(str(e))
    print(f'새 덱: {a.dest} — 장 {n}개, 지운 부록 {dropped or "없음"}')
    print('다음: index.html의 <section class="slide"> 내용과 맨 아래 deck-data(JSON)를 고치고, 브라우저로 열어 확인')


if __name__ == '__main__':
    main()
