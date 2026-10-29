"""삽화를 애니메이션용 부품으로 정밀하게 나눈다.

- 코쇠: 몸통(진회색 면 + 외곽선 + 눈) / 머리 꺾쇠 / 눈 위치(깜빡임용). 팔다리는 배경에 남긴다.
- 색 요소: 오렌지·파랑·빨강을 덩어리(화살표 하나, 라벨 하나)별로 따로 자른다.
- 어두운 배경용(-d): 종이는 투명, 검은 선은 밝은 선, 파랑은 하늘색으로 바꾼다.
사용: python cut2.py <illust 폴더> <출력 폴더> <manifest.json>
"""
import json, os, sys, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC, OUT, MAN = sys.argv[1:4]
LIGHT = np.array([237, 244, 251], float)
SKY = np.array([156, 194, 255], float)
BODY_MOTION = {'01-engine-pack': 'bPress', '02-same-memo': 'bTilt', '03-one-line-all': 'bTilt', '04-pack-maker': 'bRock',
               '05-inherit-layers': 'bNod', '10-cover-backpack': 'bTilt', '11-webslide': 'bPush', '12-blueprint': 'bNod',
               '13-hwp-typeset': 'bNod', 'k2-pain-ruler': 'bTilt', 'k3-vault-llm': 'bBreathe', 'k4-inspector': 'bPeer',
               'k5-closing-relay': 'bBreathe'}


def filt(m, f, k):
    return np.asarray(Image.fromarray((m * 255).astype('uint8')).filter(f(k))) > 0


def dil(m, k): return filt(m, ImageFilter.MaxFilter, k)
def ero(m, k): return filt(m, ImageFilter.MinFilter, k)


def components(mask, min_px=1):
    """연결 요소: PIL floodfill로 값 1~250을 칠해 묶음 단위로 꺼낸다(작은 조각은 버림)."""
    H, W = mask.shape
    img = Image.fromarray(np.where(mask, 255, 0).astype('uint8')).copy()
    px = img.load()
    out, batch = [], []

    def flush():
        a = np.asarray(img)
        for v, (x0, y0) in batch:
            ys, xs = np.where(a == v)
            if ys.size >= min_px:
                m = np.zeros((H, W), bool)
                m[ys, xs] = True
                out.append(m)
        a2 = a.copy()
        a2[(a2 > 0) & (a2 < 255)] = 0
        img.paste(Image.fromarray(a2))
        batch.clear()

    for y, x in np.argwhere(mask):
        if px[int(x), int(y)] == 255:
            v = len(batch) + 1
            ImageDraw.floodfill(img, (int(x), int(y)), v)
            batch.append((v, (x, y)))
            if len(batch) == 250:
                flush()
                px = img.load()
    if batch:
        flush()
    return out


def bbox(m, pad=0, shape=None):
    ys, xs = np.where(m)
    x0, y0, x1, y1 = xs.min() - pad, ys.min() - pad, xs.max() + 1 + pad, ys.max() + 1 + pad
    if shape:
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(shape[1], x1), min(shape[0], y1)
    return int(x0), int(y0), int(x1), int(y1)


def holes_of(m):
    x0, y0, x1, y1 = bbox(m)
    sub = ~m[y0:y1, x0:x1]
    pad = np.pad(sub, 1, constant_values=True)
    img = Image.fromarray(np.where(pad, 255, 0).astype('uint8')).copy()
    ImageDraw.floodfill(img, (0, 0), 100)
    outside = np.asarray(img)[1:-1, 1:-1] == 100
    h = np.zeros_like(m)
    h[y0:y1, x0:x1] = sub & ~outside
    return h


def dark_variant(rgb, alpha, keep=None, blue=None):
    """밝은 종이용 RGBA → 어두운 배경용 RGBA."""
    L = rgb.mean(2)
    sat = rgb.max(2) - rgb.min(2)
    out = np.zeros(rgb.shape[:2] + (4,), float)
    neutral = sat < 45
    a_n = np.clip((242 - L) / 165, 0, 1)
    out[neutral, :3] = LIGHT
    out[neutral, 3] = a_n[neutral] * alpha[neutral]
    col = ~neutral
    out[col, :3] = rgb[col]
    out[col, 3] = alpha[col]
    if blue is not None:
        bm = col & blue
        out[bm, :3] = SKY
    if keep is not None:
        out[keep, :3] = rgb[keep]
        out[keep, 3] = alpha[keep]
    return out


def save(arr_rgba, x0, y0, x1, y1, path):
    a = np.clip(arr_rgba[y0:y1, x0:x1], 0, 255)
    a[..., 3] = np.clip(a[..., 3], 0, 1) * 255
    Image.fromarray(a.astype('uint8'), 'RGBA').save(path, 'WEBP', quality=90, method=6)


os.makedirs(OUT, exist_ok=True)
manifest = {}
for f in sorted(glob.glob(os.path.join(SRC, '*.webp'))):
    name = os.path.basename(f)[:-5]
    im = np.asarray(Image.open(f).convert('RGB')).astype(float)
    H, W = im.shape[:2]
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    L, sat = im.mean(2), im.max(2) - im.min(2)
    od = os.path.join(OUT, name)
    os.makedirs(od, exist_ok=True)
    bg = im.copy()
    erase = np.zeros((H, W), bool)
    one = np.ones((H, W))

    # ── 코쇠 ──
    char = (sat < 30) & (L > 55) & (L < 130)
    char = dil(ero(char, 9), 9) & char          # 8px 이하 선은 버리고 넓은 면(몸통)만
    orange = (r > 170) & (g > 50) & (g < 190) & (b < 135) & (r - b > 90)
    ocomps = components(dil(orange, 3) & orange, 30)
    K, kzone = [], np.zeros((H, W), bool)
    for ci, body in enumerate([c for c in components(char, int(W * H * 0.004))]):
        body = dil(ero(body, 3), 3) & body | body
        small_holes = [hc for hc in components(holes_of(body), 1) if hc.sum() < body.sum() * .08]
        fill = body.copy()
        for hc in small_holes:
            fill |= hc
        bx0, by0, bx1, by1 = bbox(fill)
        bw, bh = bx1 - bx0, by1 - by0
        ring = dil(fill, 11) & ~fill & (L < 236)
        bodym = fill | ring
        eyes = []
        for hc in small_holes:
            if hc.sum() < 20:
                continue
            ex0, ey0, ex1, ey1 = bbox(hc)
            if L[hc].mean() > 200 and hc.sum() < fill.sum() * 0.05:
                eyes.append([(ex0 + ex1) / 2, (ey0 + ey1) / 2, (ex1 - ex0) / 2, (ey1 - ey0) / 2])
        fillc = np.median(im[body], axis=0)
        crest, crest_box = None, None
        for oc in ocomps:
            ox0, oy0, ox1, oy1 = bbox(oc)
            cx = (ox0 + ox1) / 2
            if bx0 - .15 * bw < cx < bx1 + .15 * bw and by0 - 1.0 * bh < oy1 < by0 + .25 * bh and oc.sum() > fill.sum() * .01:
                cm = dil(oc, 5) & (L < 238) & ~bodym
                crest = cm if crest is None else (crest | cm)
        x0, y0, x1, y1 = bbox(bodym, 1, (H, W))
        k = {'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0, 'eyes': [[round(v, 1) for v in e] for e in eyes],
             'fill': '#%02x%02x%02x' % tuple(int(v) for v in fillc), 'm': BODY_MOTION.get(name, 'bBreathe'),
             'pivot': [round((bx0 + bx1) / 2, 1), by1]}
        rgba = np.dstack([im, bodym.astype(float)])
        save(rgba, x0, y0, x1, y1, f'{od}/k{ci}.webp')
        save(dark_variant(im, bodym.astype(float), keep=fill), x0, y0, x1, y1, f'{od}/k{ci}-d.webp')
        erase |= dil(bodym, 3) & (L > 0)
        kzone |= dil(bodym, 9)
        if crest is not None:
            cx0, cy0, cx1, cy1 = bbox(crest, 1, (H, W))
            ys, xs = np.where(crest)
            low = ys.max()
            base_x = xs[ys >= low - 3].mean()
            k['crest'] = {'x': cx0, 'y': cy0, 'w': cx1 - cx0, 'h': cy1 - cy0, 'ox': round(base_x, 1), 'oy': int(low)}
            save(np.dstack([im, crest.astype(float)]), cx0, cy0, cx1, cy1, f'{od}/c{ci}.webp')
            save(dark_variant(im, crest.astype(float)), cx0, cy0, cx1, cy1, f'{od}/c{ci}-d.webp')
            erase |= dil(crest, 3)
            kzone |= dil(crest, 9)
        K.append(k)

    # ── 색 요소: 덩어리별 ──
    blue = (b > 135) & (r < 145) & (b - r > 50)
    red = (r > 170) & (g < 75) & (b < 95) & (r - g > 120)
    masks = {'o': orange & ~red & ~kzone, 'b': blue & ~kzone, 'r': red & ~kzone}
    G = []
    for c, m in masks.items():
        if m.sum() < 60:
            continue
        for gi, grp in enumerate(components(dil(m, 19) & ~kzone, 40)):
            core = grp & m
            if core.sum() < 40:
                continue
            gx0, gy0, gx1, gy1 = bbox(core, 8, (H, W))
            sl = (slice(gy0, gy1), slice(gx0, gx1))
            core_c = core[sl]
            reg = dil(core_c, 5) & ~kzone[sl] & (sat[sl] >= 14)
            C = np.median(im[sl][core_c & (sat[sl] > np.percentile(sat[sl][core_c], 50))], axis=0)
            ch = int(np.argmax(255 - C))
            a_c = np.clip((255 - im[sl][..., ch]) / max(1.0, 255 - C[ch]), 0, 1) * reg
            a_c[core_c] = np.maximum(a_c[core_c], .95)
            a = np.zeros((H, W))
            a[sl] = a_c
            x0, y0, x1, y1 = bbox(a > .02, 1, (H, W))
            rgb = np.zeros(im.shape)
            rgb[y0:y1, x0:x1] = C
            gid = f'{c}{len([x for x in G if x["c"] == c])}'
            save(np.dstack([rgb, a]), x0, y0, x1, y1, f'{od}/{gid}.webp')
            drgb = np.zeros(im.shape)
            drgb[y0:y1, x0:x1] = SKY if c == 'b' else C
            save(np.dstack([drgb, a]), x0, y0, x1, y1, f'{od}/{gid}-d.webp')
            erase |= a > .02
            w, h = x1 - x0, y1 - y0
            fillr = core.sum() / float(w * h)
            if w / h > 2.3 and fillr < .45:
                kind = 'wx'
            elif h / w > 2.3 and fillr < .45:
                kind = 'wy'
            elif w * h > W * H * .03 and fillr < .2:
                kind = 'wx'
            else:
                kind = 'pop'
            G.append({'id': gid, 'c': c, 'x': x0, 'y': y0, 'w': w, 'h': h, 'a': kind})

    # ── 배경 ──
    bg[erase] = 255
    Image.fromarray(bg.astype('uint8')).save(f'{od}/bg.webp', 'WEBP', quality=88, method=6)
    save(dark_variant(bg, one), 0, 0, W, H, f'{od}/bg-d.webp')

    # 순서: 색 요소는 왼쪽에서 오른쪽으로
    G.sort(key=lambda g: (g['c'] != 'o', g['x']))
    manifest[name] = {'w': W, 'h': H, 'K': K, 'G': G}
    print(name, 'kosoe', len(K), 'crest', sum('crest' in k for k in K), 'eyes', [len(k['eyes']) for k in K],
          'groups', {c: sum(g['c'] == c for g in G) for c in 'obr'})

json.dump(manifest, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
