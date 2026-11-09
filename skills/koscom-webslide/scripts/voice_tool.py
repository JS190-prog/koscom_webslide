#!/usr/bin/env python3
"""코스콤 웹슬라이드 스킬의 문체 도구 (표준 라이브러리만, 결정론).

gongnyang/gn-voice 의 방식(서식을 걷어낸 본문 -> 문체 지표 -> 밴드 -> 스크립트 검사 -> 고칠 항목)에
presentation 프로필의 장표 자기검증(제목만 읽기 · 장당 단어 수 · 항목 병렬성)을 지표로 더했다.
뼈대는 koscom-hwp-report 스킬의 voice_tool.py 다(대표 문서 2~3건, 5줄 묶음 표본, 한 건 빼고 검증).
gn-voice 저자의 코퍼스·지문·장르 팩 데이터는 쓰지 않는다. 방식과 장표 규범만 가져왔다.

  build  대표 자료 -> 문체 폴더 (style-guide.md · style-profile.json · fingerprint-slim.json · ai-tells.json · manifest.jsonl · corpus/)
  gate   (문체 폴더) + 검사할 덱 + 근거 -> 합격/불합격 JSON, 고칠 항목, 제목 목록

읽는 형식: 웹슬라이드 .html(section 슬라이드, 이 스킬의 덱) · .pptx · .hwpx(한 장으로 봄) · .md · .txt
대표 자료와 검사할 덱은 같은 함수(read_deck -> style_parts -> points)를 거친다. 한쪽만 다른 규칙으로 읽지 않는다.
"""
import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

WINDOW = 5            # 표본 단위: 5줄 묶음 (hwp 스킬과 같은 값)
MIN_LINE = 8          # 이보다 짧은 줄(꼬리표, 라벨, 숫자)은 끝맺음 측정에서 뺀다. 장당 어절 수에는 센다
ALLOW = 2             # 밴드를 벗어난 지표가 이 개수까지는 합격 (gn-voice 와 같은 규칙)
LOO_WIDEN = 1.5       # 한 건 빼고 검증이 실패하면 여유를 한 번 넓힌다
KST = timezone(timedelta(hours=9))

RATIO = ("end_m", "end_da", "end_polite", "end_other")
LINE_KEYS = RATIO + ("line_len", "line_len_cv", "period_per1k", "comma_per1k", "paren_per1k")
TITLE_KEYS = ("title_len", "title_sentence")
SLIDE_KEYS = ("slide_words", "slide_parallel")
KEYS = LINE_KEYS + TITLE_KEYS + SLIDE_KEYS
MIN_SLACK = {**{k: 0.10 for k in RATIO + ("line_len_cv", "title_sentence", "slide_parallel")},
             "line_len": 3.0, "period_per1k": 3.0, "comma_per1k": 3.0, "paren_per1k": 3.0,
             "title_len": 3.0, "slide_words": 5.0}

# 쓰면 안 되는 일반 AI 상투구. hard=즉시 불합격, capped=한 덱에서 이 횟수까지.
# (gn-voice 의 ai-tells.json 은 저자 코퍼스에서 뽑은 데이터라 가져오지 않고, 일반 표현만 직접 적었다.)
AI_TELLS = {
    "hard": ["알아보겠습니다", "살펴보겠습니다", "궁극적으로", "도움이 되셨다면", "놓치지 마세요"],
    "capped": {"결론적으로": 1, "요약하자면": 1, "다음과 같습니다": 2, "시사합니다": 1, "이번 발표에서는": 1},
    "rule": "hard=즉시 불합격 / capped=덱당 상한 초과 시 불합격",
}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2728\u2705]")
KH_RE = re.compile(r"[ㅋㅎ]{2,}")
HANGUL = re.compile(r"[가-힣]")

# 음슴체(~음/~함/~임) 근사: 끝 어절의 마지막 글자가 ㅁ 받침. 명사 오탐은 막는다 (gn-voice verify_style.py)
_STRIP = re.compile(r"[)\"'”….?!\s~;ㄱ-ㅎㅏ-ㅣ→↗]+$")
_TAIL = re.compile(r"[)\"'”….?!\s→↗]+$")
_BLOCK = ("처음", "다음", "마음", "걸음", "얼음", "죽음", "사람", "이름", "아침", "점심",
          "기쁨", "슬픔", "게임", "시스템", "프로그램", "아이템")
# '요'로 끝나는 명사. '~ 필요'를 존댓말로 세지 않는다 (gn-voice 원본에 있던 오분류, hwp 스킬에서 고침)
_YO_NOUN = ("필요", "중요", "개요", "주요", "수요", "소요", "강요", "동요")


def _m_end(word):
    w = _STRIP.sub("", word)
    if not w or any(w.endswith(b) for b in _BLOCK):
        return False
    o = ord(w[-1])
    return 0xAC00 <= o <= 0xD7A3 and (o - 0xAC00) % 28 == 16


def end_type(line):
    """줄 끝맺음 한 가지: 존댓말 > ~함/~임 > ~다 > 명사형·기타 (한 줄은 한 유형에만 센다)."""
    e = _TAIL.sub("", line)
    if re.search(r"(요|죠|니다)$", e) and not e.endswith(_YO_NOUN):
        return "end_polite"
    if _m_end(e):
        return "end_m"
    if re.search(r"(다|까|랴|자|네|지)$", e):
        return "end_da"
    return "end_other"


# ---------------------------------------------------------------- 읽기 -> {"slides": [{title, em, lines}], "extra": [...]}
# extra 는 표·코드·차트 데이터(deck-data)·부록 글이다. 문체 측정에서는 빠지고 숫자 대조에는 들어간다.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "dfn", "em", "font", "i", "kbd", "label", "mark",
          "q", "s", "samp", "small", "span", "strong", "sub", "sup", "time", "u", "var"}
# 편집 모드가 글로 보지 않는 요소(template/index.html 의 SKIP = script,style,svg,canvas,button,[data-gen],.chevs,.lb)에
# 근거 배지(.ev)·장 번호(.no)·영문 꼬리표(.kick)·목차(.agenda)를 더했다. 배지는 문장 끝에 붙어 끝맺음을 흐린다.
SKIP_TAGS = {"script", "style", "svg", "canvas", "button", "noscript", "template", "head", "select", "textarea",
             "video", "audio", "iframe", "object"}
SKIP_CLASS = {"chevs", "lb", "ev", "no", "kick", "agenda"}
EMPH = {"em", "strong", "b", "mark"}


class _Deck(HTMLParser):
    def __init__(self, mode):
        super().__init__(convert_charrefs=True)
        self.mode = mode          # slide: section.slide 만 / section: 모든 section / heading: h1·h2 마다 새 장
        self.slides, self.extra, self.json = [], [], []
        self.stack, self.buf, self.cur, self.n = [], [], None, Counter()
        self.joint = False        # 인라인 요소가 막 닫혔고 그 뒤 글자가 없다 (<span>A</span><span>B</span> -> 'A B')

    def _new(self):
        self.cur = {"title": "", "em": 0, "lines": []}
        self.slides.append(self.cur)

    def _flush(self):
        s = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if not s or self.n["skip"]:
            return
        if self.n["side"]:
            self.extra.append(s)
            return
        if self.cur is None and self.mode == "heading":
            self._new()
        if self.cur is None:
            return
        if self.n["title"] and not self.cur["title"]:
            self.cur["title"] = s
        else:
            self.cur["lines"].append(s)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag == "br":
                self.buf.append(" ")
            return
        a = dict(attrs)
        cls = set((a.get("class") or "").split())
        if tag == "script" and a.get("id") == "deck-data":
            role = "data"
        elif tag in SKIP_TAGS or "data-gen" in a or cls & SKIP_CLASS:
            role = "skip"
        elif tag == "section" and (self.mode == "section" or (self.mode == "slide" and "slide" in cls)):
            role = "slide"
        elif "side-page" in cls or tag in ("table", "pre"):    # 부록·표·코드는 숫자 대조에만
            role = "side"
        elif tag in ("h1", "h2") and not self.n["side"]:
            role = "title"
        else:
            role = None
        if tag not in INLINE:
            self._flush()
        elif self.joint:
            self.buf.append(" ")
        self.joint = False
        if role == "slide" or (role == "title" and self.mode == "heading" and not self.n["skip"]):
            self._new()
        if tag in EMPH and self.n["title"] and not self.n["skip"] and self.cur is not None:
            self.cur["em"] += 1
        self.n[role] += 1
        self.stack.append((tag, role))

    def handle_endtag(self, tag):
        if all(t != tag for t, _ in self.stack):
            return
        while self.stack:                     # 닫지 않은 <p>·<li> 가 있어도 짝이 맞는 곳까지 닫는다
            t, role = self.stack.pop()
            if t not in INLINE:
                self._flush()                 # 역할(제목·부록 등)을 내리기 전에 그 안의 글을 보낸다
            self.n[role] -= 1
            if role == "data":
                self._data()
            if role == "slide":
                self.cur = None
            if t == tag:
                break
        self.joint = tag in INLINE

    def handle_data(self, d):
        if self.n["data"]:
            self.json.append(d)
        elif not self.n["skip"]:
            self.buf.append(d)
            self.joint = self.joint and not d.strip()

    def _data(self):
        try:
            d = json.loads("".join(self.json))
        except ValueError:
            d = None
        self.json = []

        def walk(x):
            if isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
            elif isinstance(x, (str, int, float)) and not isinstance(x, bool):
                self.extra.append(str(x))
        walk(d)


def read_html(text):
    classes = re.findall(r"<section\b[^>]*\bclass\s*=\s*[\"']([^\"']*)", text)
    mode = ("slide" if any("slide" in c.split() for c in classes)
            else "section" if re.search(r"<section\b", text) else "heading")
    d = _Deck(mode)
    d.feed(text)
    d.close()
    d._flush()
    return {"slides": d.slides, "extra": d.extra}


P_NS = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _ptext(e):
    """a:p 하나의 글자. 줄바꿈(a:br)은 띄어쓰기로 둔다."""
    return "".join((x.text or "") if x.tag == A_NS + "t" else " " for x in e.iter() if x.tag in (A_NS + "t", A_NS + "br"))


def read_pptx(p):
    # ponytail: 장 순서는 slideN 번호순이다(presentation.xml 의 실제 순서가 아님). 문체 지표에는 순서가 영향이 없다.
    slides, extra = [], []
    with zipfile.ZipFile(p) as z:
        names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                       key=lambda n: int(re.findall(r"\d+", n)[-1]))
        for name in names:
            root = ET.fromstring(z.read(name))
            if root.get("show") == "0":          # 숨긴 슬라이드
                continue
            title, shapes = "", []
            for sp in root.iter(P_NS + "sp"):
                ph = sp.find(f"{P_NS}nvSpPr/{P_NS}nvPr/{P_NS}ph")
                kind = None if ph is None else ph.get("type", "body")
                if kind in ("sldNum", "dt", "ftr", "hdr"):
                    continue
                paras = [x for x in (re.sub(r"\s+", " ", _ptext(a)).strip() for a in sp.iter(A_NS + "p")) if x]
                if kind in ("title", "ctrTitle") and not title:
                    title = " ".join(paras)
                elif paras:
                    shapes.append((sp, paras))
            if not title:   # 제목 개체를 안 쓴 장(사내 덱에 흔함): 한글이 든 60자 이하 첫 문단 중 가장 큰 글자, 같으면 가장 위
                cand = [(_sz(sp), -_top(sp), i) for i, (sp, ps) in enumerate(shapes) if HANGUL.search(ps[0]) and len(ps[0]) <= 60]
                if cand:
                    title = shapes[max(cand)[2]][1].pop(0)
            slides.append({"title": title, "em": None, "lines": [x for _, ps in shapes for x in ps]})
            for tr in root.iter(A_NS + "tr"):     # 표는 숫자 대조에만
                extra.append(" | ".join(" ".join(_ptext(a) for a in tc.iter(A_NS + "p")) for tc in tr.iter(A_NS + "tc")))
    return {"slides": slides, "extra": extra}


def _sz(sp):
    s = [int(r.get("sz")) for r in sp.iter(A_NS + "rPr") if (r.get("sz") or "").isdigit()]
    return max(s, default=0)


def _top(sp):
    off = sp.find(f"{P_NS}spPr/{A_NS}xfrm/{A_NS}off")
    return int(off.get("y", 0)) if off is not None else 10 ** 12


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _hp_text(par):
    """한글 문단(hp:p) 하나의 글자. 표 칸·글상자(subList) 안은 따로 모으므로 건너뛴다 (koscom-hwp-report 와 같은 규칙)."""
    out = []

    def walk(e):
        for c in e:
            n = _local(c.tag)
            if n == "subList":
                continue
            if n == "t":
                out.append("".join(c.itertext()))
            else:
                walk(c)
    walk(par)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def read_hwpx(p):
    """한글 문서는 장 구분이 없으므로 한 장으로 본다. 본문 문단은 문체 측정에, 표·글상자 안 글은 숫자 대조에만 쓴다.
    본문이 표·글상자 안에만 있는 문서(견적서 등, 본문 문장 3줄 미만)는 그 안의 글을 본문으로 쓴다."""
    top, nested = [], []
    with zipfile.ZipFile(p) as z:
        secs = sorted((n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)),
                      key=lambda n: int(re.findall(r"\d+", n)[-1]))
        for s in secs:
            for par in ET.fromstring(z.read(s)):
                if _local(par.tag) != "p":
                    continue
                top.append(_hp_text(par))
                for sub in par.iter():
                    if _local(sub.tag) == "subList":
                        nested += [_hp_text(q) for q in sub if _local(q.tag) == "p"]
    top, nested = [x for x in top if x], [x for x in nested if x]
    if sum(len(x) >= MIN_LINE for x in top) < 3:
        top, nested = top + nested, []
    return {"slides": [{"title": "", "em": None, "lines": top}], "extra": nested}


def read_md(text):
    """# · ## 제목마다, 또는 --- 마다 새 장. 표(|…|)는 숫자 대조에만 쓴다."""
    slides, extra, cur = [], [], None
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("!["):
            continue
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", s):
            cur = None
            continue
        if s.startswith("|"):
            if not re.fullmatch(r"[|\s:\-]+", s):
                extra.append(s)
            continue
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", re.sub(r"\*\*|__|`", "", s)).lstrip("> ")
        m = re.match(r"#{1,2}\s+(.*)", s)
        if m or cur is None:
            cur = {"title": m.group(1).strip() if m else "", "em": None, "lines": []}
            slides.append(cur)
            if m:
                continue
        cur["lines"].append(re.sub(r"^#{3,6}\s+", "", s))
    return {"slides": slides, "extra": extra}


def _read(p):
    b = p.read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    sys.exit(f"{p.name}: 글자 인코딩을 읽지 못했습니다(UTF-8 또는 CP949 로 저장해 주세요)")


def read_deck(path):
    p = Path(path)
    if not p.is_file():
        sys.exit(f"파일이 없습니다: {p}")
    ext = p.suffix.lower()
    if ext in (".html", ".htm"):
        return read_html(_read(p))
    if ext == ".pptx":
        try:
            return read_pptx(p)
        except (zipfile.BadZipFile, ET.ParseError, KeyError) as e:
            sys.exit(f"{p.name}: .pptx 를 읽지 못했습니다({e}). 암호가 걸렸거나 손상된 파일일 수 있습니다")
    if ext == ".hwpx":
        try:
            return read_hwpx(p)
        except (zipfile.BadZipFile, ET.ParseError, KeyError) as e:
            sys.exit(f"{p.name}: .hwpx 를 읽지 못했습니다({e}). 배포용·암호 문서이거나 손상된 파일일 수 있습니다")
    if ext in (".md", ".markdown", ".txt"):
        return read_md(_read(p))
    if ext == ".pia":
        sys.exit(f"{p.name}: 사내 보호 도구로 암호화된 파일입니다. 사내 절차대로 해제한 뒤 넣으세요")
    sys.exit(f"{p.name}: 읽을 수 없는 형식입니다(.html·.pptx·.hwpx·.md·.txt). .ppt 는 .pptx 로, .hwp 는 한글에서 .hwpx 로, 워드·PDF 는 본문을 .txt 로 저장해 넣으세요")


# 줄 머리 기호: □ ㅇ - · * ※ ① ▶ ✓, '1.' '가.' 'I.' (뒤에 띄어쓰기가 있을 때만), '[1]', 기호 글꼴 문자(U+E000~F8FF)
_HEAD = re.compile(r"^(?:[□■○◦●ㅇ\-\*※•▪·∙①-⑳▶►▷✓✔\ue000-\uf8ff\s]|\[\d{1,2}\]"
                   r"|(?:\d{1,2}|[가나다라마바사아자차카타파하]|[IVX]{1,4})[.)](?=\s))+")


def clean(line, min_len=MIN_LINE):
    """문체 측정용 줄: 머리 기호를 걷고, 한글이 있고 min_len 이상인 줄만."""
    s = _HEAD.sub("", re.sub(r"\s+", " ", line).strip())
    return s if len(s) >= min_len and HANGUL.search(s) else ""


def style_parts(deck):
    """덱 -> (제목들, 본문 줄들, 장마다 (어절 수, 본문 줄들)). 문체 측정은 모두 여기를 거친다."""
    titles, body, per = [], [], []
    for s in deck["slides"]:
        t = clean(s["title"], 2)
        if t:
            titles.append(t)
        ls = [x for x in map(clean, s["lines"]) if x]
        body += ls
        per.append((sum(len(x.split()) for x in s["lines"]), ls))
    return titles, body, per


_NUMBERING = re.compile(r"^\(?\d{1,2}[.)]?$|^\d{1,2} · ")   # 번호 칸('1', '03')·차트 제목의 장 번호('03 · ')


def all_text(deck):
    """숫자 대조용 전체 글: 제목·본문·표·차트 데이터·부록."""
    out = [x for s in deck["slides"] for x in [s["title"], *s["lines"]]] + deck["extra"]
    return "\n".join(x for x in (_NUMBERING.sub("", l.strip()).strip() for l in out) if x)


def windows(lines, w=WINDOW):
    ws = [lines[i:i + w] for i in range(0, len(lines), w)]
    return [x for x in ws if len(x) >= max(3, w // 2)]


# ---------------------------------------------------------------- 지표 (밴드·검사)
def metrics(lines):
    text = "\n".join(lines)
    n, chars = max(len(lines), 1), max(len(text), 1)
    c = Counter(end_type(l) for l in lines)
    lens = [len(l) for l in lines]
    return {
        **{k: c[k] / n for k in RATIO},
        "line_len": sum(lens) / n,
        "line_len_cv": statistics.pstdev(lens) / statistics.mean(lens) if len(lens) > 2 else 0.0,
        "period_per1k": text.count(".") / chars * 1000,
        "comma_per1k": text.count(",") / chars * 1000,
        "paren_per1k": text.count("(") / chars * 1000,
    }


def title_metrics(ts):
    return {"title_len": sum(len(t) for t in ts) / len(ts),
            "title_sentence": sum(end_type(t) != "end_other" for t in ts) / len(ts)}


def _parallel(ls):
    """한 장 안 항목 중 가장 많은 끝맺음 유형의 비율 (gn-voice presentation: 불릿 병렬성)."""
    return Counter(map(end_type, ls)).most_common(1)[0][1] / len(ls)


def points(deck, check=False):
    """덱 하나 -> 표본 점들(본문 5줄 묶음 · 제목 5개 묶음 · 장). check=True 면 묶음이 모자라도 전체를 한 점으로 잰다."""
    titles, body, per = style_parts(deck)

    def ws(x):
        return windows(x) or ([x] if check and x else [])
    pts = [metrics(w) for w in ws(body)] + [title_metrics(w) for w in ws(titles)]
    if len(per) >= 2:                          # 장 구분이 없는 글(.txt 한 덩어리)은 장 지표를 만들지 않는다
        pts += [{"slide_words": w} for w, _ in per if w]
        pts += [{"slide_parallel": _parallel(ls)} for _, ls in per if len(ls) >= 2]
    return pts


def pct(vals, p):
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def make_band(pts, mult=1.0):
    """지표마다: 점 5개 미만이면 최솟값~최댓값, 이상이면 5~95% 분위수. 여유(slack)를 덧붙인다."""
    band = {}
    for k in KEYS:
        v = [p[k] for p in pts if k in p]
        if not v:
            continue
        lo, hi = (min(v), max(v)) if len(v) < 5 else (pct(v, 5), pct(v, 95))
        slack = max((hi - lo) * 0.15, MIN_SLACK[k]) * mult
        band[k] = {"lo": round(max(lo - slack, 0.0), 4), "hi": round(hi + slack, 4), "raw_lo": round(lo, 4), "raw_hi": round(hi, 4)}
    return band


def deck_metrics(deck):
    """검사할 덱: 지표마다 점들의 중앙값(밴드를 만든 방식과 같은 단위)."""
    pts = points(deck, check=True)
    return {k: statistics.median(p[k] for p in pts if k in p) for k in KEYS if any(k in p for p in pts)}


def tier(n_docs):
    return "trial" if n_docs <= 1 else ("small" if n_docs <= 3 else "normal")


# ---------------------------------------------------------------- 문체 분석 (style-guide.md)
END_NAME = {"end_other": "명사형(~ 추진, ~ 필요, ~으로 등)", "end_m": "~함·~임·~음",
            "end_da": "~다", "end_polite": "~습니다·~요(존댓말)"}
_TOK = re.compile(r"^[\"'“‘(\[<:]+|[\"'”’)\]>,.·:;!?]+$")
DATES = [("2026. 4. 23", r"\d{4}\. \d{1,2}\. \d{1,2}"), ("2026.4.23", r"\d{4}\.\d{1,2}\.\d{1,2}"),
         ("2026-04-23", r"\d{4}-\d{1,2}-\d{1,2}"), ("2026년 4월 23일", r"\d{4}년 ?\d{1,2}월 ?\d{1,2}일"),
         ("2026.4", r"\d{4}\.\d{1,2}(?![\d.])"), ("'26. 4.", r"['’]\d{2}\.\s?\d{1,2}"), ("’26년", r"['’]\d{2}년")]
_MONEY = re.compile(r"\d[\d,.]*(\s?)(조|억|천만|백만|만|천)?(\s?)원")
SIGNS = [("%p", r"%p"), ("%", r"%(?!p)"), ("↑", "↑"), ("↓", "↓"), ("△", "△"), ("전년 대비", r"전년\s?대비")]
SYMBOLS = ("·", "→", "/", "~", "|")


def _words(line):
    return [w for w in (_TOK.sub("", x) for x in _TAIL.sub("", line).split()) if w]


def _ending(line, k):
    ws = _words(line)
    if len(ws) < k or re.search(r"\d", " ".join(ws[-k:])):
        return ""
    return " ".join(ws[-k:])


def _spread(vals):
    vals = vals or [0]
    return {"mean": round(statistics.mean(vals), 1), "p25": round(pct(vals, 25)), "p75": round(pct(vals, 75)),
            "min": min(vals), "max": max(vals)}


def _pick(groups, ok, k=6):
    """문서마다 고르게, 조건(ok)에 맞는 줄을 원문 그대로 뽑는다."""
    per, out = -(-k // max(len(groups), 1)), []
    for g in groups:
        pool = [x for x in g if ok(x)]
        out += pool[::max(len(pool) // per, 1)][:per]
    return out[:k]


def analyze(docs):
    """docs: [(id, 파일명, deck)] -> 문체 분석값 (모두 대표 자료에서 잰 숫자와 원문 그대로의 예)."""
    parts = [style_parts(d[2]) for d in docs]
    titles = [t for p in parts for t in p[0]]
    lines = [l for p in parts for l in p[1]]
    per = [x for p in parts if len(p[2]) >= 2 for x in p[2]]
    raw = "\n".join(all_text(d[2]) for d in docs)
    n, nt, nd = max(len(lines), 1), max(len(titles), 1), len(docs)
    ends = Counter(end_type(l) for l in lines)
    endings = {k: round(ends[k] / n, 3) for k in RATIO}
    tends = Counter(end_type(t) for t in titles)
    tail2 = Counter(_TAIL.sub("", l)[-2:] for l in lines)          # gn-voice smoothness 의 끝맺음 엔트로피
    entropy = -sum(v / n * math.log2(v / n) for v in tail2.values()) if lines else 0.0
    lens, tlens = [len(l) for l in lines], [len(t) for t in titles]
    words = [w for w, _ in per if w]
    par = [_parallel(ls) for _, ls in per if len(ls) >= 2]
    ems = [s["em"] for d in docs for s in d[2]["slides"] if s["title"] and s["em"] is not None]
    df, tf = Counter(), Counter()                                   # 두 어절 표현: 문서 수와 횟수
    for p in parts:
        seen = set()
        for l in p[0] + p[1]:
            ws = _words(l)
            for a, b in zip(ws, ws[1:]):
                bg = f"{a} {b}"
                if len(a) == 1 and len(b) == 1:
                    continue
                if re.search(r"[가-힣]", bg) and not re.search(r"\d", bg):
                    tf[bg] += 1
                    seen.add(bg)
        df.update(seen)
    money = Counter((m.group(2) or "") + (" " if m.group(3) else "") + "원" for m in _MONEY.finditer(raw))
    tdom = max(RATIO, key=lambda k: tends[k]) if titles else "end_other"
    a = {
        "n_docs": nd, "n_slides": sum(len(d[2]["slides"]) for d in docs), "n_titles": len(titles), "n_lines": len(lines),
        "titles": {
            "len": _spread(tlens), "sentence": round(1 - tends["end_other"] / nt, 3) if titles else 0.0,
            "endings": {k: round(tends[k] / nt, 3) for k in RATIO}, "dominant": tdom,
            "top_endings": [(w, c) for w, c in Counter(filter(None, (_ending(t, 1) for t in titles))).most_common(8) if c >= 2],
            "comma": round(sum("," in t for t in titles) / nt, 3), "number": round(sum(bool(re.search(r"\d", t)) for t in titles) / nt, 3),
            "em": round(statistics.mean(ems), 2) if ems else None,
        },
        "slides": {"words": _spread(words), "words_p50": round(statistics.median(words)) if words else 0,
                   "parallel": round(statistics.median(par), 2) if par else None},
        "endings": endings,
        "top_endings": [(w, c) for w, c in Counter(filter(None, (_ending(l, 1) for l in lines))).most_common(12) if c >= 2],
        "top_endings2": [(w, c) for w, c in Counter(filter(None, (_ending(l, 2) for l in lines))).most_common(8) if c >= 2],
        "ending_entropy": round(entropy, 2), "ending_kinds": len(tail2),
        "line_len": _spread(lens),
        "period_end_ratio": round(sum(1 for l in lines if l.rstrip().endswith(".")) / n, 3),
        "comma_per_line": round(sum(l.count(",") for l in lines) / n, 2),
        "paren_per_line": round(sum(l.count("(") for l in lines) / n, 2),
        "symbols": [(s, round(sum(l.count(s) for l in titles + lines) / max(len(titles + lines), 1), 2))
                    for s in SYMBOLS if any(s in l for l in titles + lines)],
        "dates": [(k, c) for k, c in ((k, len(re.findall(p, raw))) for k, p in DATES) if c],
        "money": money.most_common(6),
        "signs": [(k, c) for k, c in ((k, len(re.findall(p, raw))) for k, p in SIGNS) if c],
        "phrases": [(bg, c) for bg, c in tf.most_common() if c >= 2 and df[bg] >= min(2, nd)][:12],
    }
    a["dominant"] = max(RATIO, key=lambda k: endings[k])
    lo, hi = (pct(lens, 25), pct(lens, 75)) if lens else (0, 0)
    a["examples"] = _pick([p[1] for p in parts], lambda l: end_type(l) == a["dominant"] and lo <= len(l) <= hi)
    tlo, thi = (pct(tlens, 25), pct(tlens, 75)) if tlens else (0, 0)
    a["title_examples"] = _pick([p[0] for p in parts], lambda t: end_type(t) == tdom and tlo <= len(t) <= thi)
    return a


def _pc(x):
    return f"{round(x * 100)}%"


def rules_of(a):
    """분석값 -> 작성 규칙(문장). 숫자가 기준을 넘을 때만 규칙을 만든다."""
    t, sl, e, r = a["titles"], a["slides"], a["endings"], []
    if a["n_titles"]:
        s = t["sentence"]
        if s >= 0.6:
            r.append(f"제목은 서술어로 끝나는 결론 문장으로 쓴다({_pc(s)}). 주된 끝맺음: {END_NAME[t['dominant']]}")
        elif s <= 0.3:
            r.append(f"제목은 명사형으로 끝낸다({_pc(1 - s)}). 대신 제목 아래 .lead 에 결론 한 문장을 둔다(리딩덱 규칙)")
        else:
            r.append(f"제목은 서술어로 끝나는 문장({_pc(s)})과 명사·조사로 끊는 말({_pc(1 - s)})을 섞어 쓴다")
        if t["top_endings"]:
            r.append("자주 쓴 제목 끝말: " + ", ".join(w for w, _ in t["top_endings"][:6]))
        r.append(f"제목은 평균 {t['len']['mean']}자, 보통 {t['len']['p25']}~{t['len']['p75']}자로 쓴다")
        if t["comma"] >= 0.25:
            r.append(f"제목 {_pc(t['comma'])}는 쉼표로 앞뒤를 나눈다(예: '앞말, 뒷말')")
        if t["number"] >= 0.2:
            r.append(f"제목 {_pc(t['number'])}에 숫자를 넣는다(근거 숫자가 있는 장)")
        if t["em"] is not None:
            r.append(f"제목 강조(<em>)는 평균 {t['em']}개" + (" — 강조 낱말 하나만" if t["em"] <= 1.2 else ""))
    if sl["words_p50"]:
        r.append(f"한 장 본문은 보통 {sl['words']['p25']}~{sl['words']['p75']}어절(중앙값 {sl['words_p50']})로 쓴다"
                 + (". 75어절을 넘는 읽는 덱이므로 상세는 부록으로 보낼지 함께 검토한다" if sl["words_p50"] > 75 else ""))
    if sl["parallel"] is not None and sl["parallel"] >= 0.75:
        r.append(f"한 장 안 항목은 끝맺음을 맞춘다(같은 유형 {_pc(sl['parallel'])})")
    order = sorted(RATIO, key=lambda k: e[k], reverse=True)
    r.append(f"본문 줄 끝은 주로 {END_NAME[order[0]]}으로 끝낸다({_pc(e[order[0]])})"
             + (f". {END_NAME[order[1]]}도 섞는다({_pc(e[order[1]])})" if e[order[1]] >= 0.15 else ""))
    if a["top_endings"]:
        r.append("자주 쓴 본문 끝말을 우선 쓴다: " + ", ".join(w for w, _ in a["top_endings"][:8]))
    p = a["period_end_ratio"]
    r.append("본문 줄 끝에 마침표를 찍지 않는다" if p < 0.1 else
             f"본문 줄 끝에 마침표를 찍는다({_pc(p)})" if p > 0.6 else f"본문 줄 끝 마침표는 섞어 쓴다({_pc(p)})")
    ll = a["line_len"]
    r.append(f"본문 한 줄은 평균 {ll['mean']}자, 보통 {ll['p25']}~{ll['p75']}자로 쓴다")
    sy = [f"'{s}'" for s, v in a["symbols"] if v >= 0.15]
    if sy:
        r.append("나열·흐름 기호는 " + ", ".join(sy) + "를 쓴다")
    if a["dates"]:
        r.append(f"날짜는 '{max(a['dates'], key=lambda x: x[1])[0]}' 꼴로 쓴다")
    if a["money"]:
        r.append("금액 단위는 " + ", ".join(f"'{u}'" for u, _ in a["money"][:3]) + " 꼴을 쓴다. 근거 금액을 다른 단위로 환산하지는 않는다")
    signs = [k for k, _ in a["signs"] if k != "%"]
    if signs:
        r.append("증감 표기는 " + ", ".join(f"'{s}'" for s in signs) + "를 쓴다")
    if a["phrases"]:
        r.append("자주 쓴 표현을 살려 쓴다: " + ", ".join(bg for bg, _ in a["phrases"][:8]))
    return r


def _fmt(pairs):
    return " · ".join(f"{w}({c})" for w, c in pairs) or "(없음)"


HINT = {"end_m": "~함/~임으로 끝나는 본문 줄", "end_da": "~다로 끝나는 본문 줄", "end_polite": "~요/~니다로 끝나는 본문 줄",
        "end_other": "명사 등으로 끝나는 본문 줄", "line_len": "본문 줄 평균 길이", "line_len_cv": "본문 줄 길이의 들쭉날쭉함",
        "period_per1k": "마침표 밀도", "comma_per1k": "쉼표 밀도", "paren_per1k": "괄호 밀도",
        "title_len": "제목 길이", "title_sentence": "서술어로 끝나는 제목 비율", "slide_words": "장당 본문 어절 수",
        "slide_parallel": "장 안 항목 끝맺음 일치도"}


def guide_md(doc_type, meta, rows, a, rules, band):
    loo = meta["leave_one_out"]
    loo_s = ", ".join(f"{x['held_out']} {'통과' if x['pass'] else '불합격'}" for x in loo) or "1건이라 하지 않음"
    t, sl, e = a["titles"], a["slides"], a["endings"]
    L = [f"# 문체 가이드 — {doc_type} ({meta['label']})", "",
         f"- 근거: 대표 자료 {a['n_docs']}건, 장 {a['n_slides']}개(제목 {a['n_titles']}개), 본문 문장 줄 {a['n_lines']}개, 표본 점 {meta['n_points']}개",
         *[f"  - {r['id']} {r['source_file']} (장 {r['slides']}개, 본문 {r['lines']}줄)" for r in rows],
         f"- 한 건 빼고 검증: {loo_s}" + (" (여유를 한 번 넓힘)" if meta["widened_after_loo"] else ""),
         f"- 만든 때: {meta['built']} · `scripts/voice_tool.py build`", "",
         "> 웹슬라이드 규칙(서체·색·한 장 한 메시지·근거 배지·가상 데이터·원문에 없는 숫자 금지)은 그대로 지키고,",
         "> 그 안에서 제목·끝맺음·분량·표기·표현은 이 가이드를 따른다. 숫자는 모두 대표 자료에서 잰 값이다.", "",
         "## 1. 이렇게 쓴다", "", *[f"- {r}" for r in rules],
         "- 이모지·ㅋㅋ·AI 상투구(살펴보겠습니다, 결론적으로 등)는 쓰지 않는다",
         "- 제목만 위에서 아래로 읽어도 이야기가 이어지게 쓴다(gate 결과의 titles 로 확인)", "",
         "## 2. 제목", "",
         f"- 길이: 평균 {t['len']['mean']}자, 25~75% {t['len']['p25']}~{t['len']['p75']}자, 최소 {t['len']['min']} · 최대 {t['len']['max']}자",
         f"- 서술어로 끝나는 제목: {_pc(t['sentence'])} · 쉼표로 나눈 제목: {_pc(t['comma'])} · 숫자 든 제목: {_pc(t['number'])}"
         + (f" · 강조 평균 {t['em']}개" if t["em"] is not None else ""),
         "- 끝맺음: " + " · ".join(f"{END_NAME[k]} {_pc(t['endings'][k])}" for k in RATIO),
         f"- 자주 쓴 제목 끝말: {_fmt(t['top_endings'])}",
         "- 제목 예 (대표 자료에서 그대로):", *[f"  - {x}" for x in a["title_examples"]], "",
         "## 3. 장 분량", "",
         f"- 장당 본문 어절: 중앙값 {sl['words_p50']}, 25~75% {sl['words']['p25']}~{sl['words']['p75']}, 최대 {sl['words']['max']}"
         " (gn-voice 장표 규범: 발표용 30어절 · 상한 75어절)",
         "- 장 안 항목 끝맺음 일치도: " + (_pc(sl["parallel"]) if sl["parallel"] is not None else "(항목이 2줄 이상인 장 없음)"), "",
         "## 4. 본문 끝맺음", "", "| 유형 | 비율 | 허용 범위(5줄 묶음) |", "|---|---|---|",
         *[f"| {END_NAME[k]} | {_pc(e[k])} | " + (f"{_pc(band[k]['lo'])} ~ {_pc(band[k]['hi'])}" if k in band else "-") + " |" for k in RATIO], "",
         f"- 자주 쓴 끝말: {_fmt(a['top_endings'])}", f"- 자주 쓴 끝 두 어절: {_fmt(a['top_endings2'])}",
         f"- 끝맺음 다양도: 끝 두 글자 {a['ending_kinds']}가지, 엔트로피 {a['ending_entropy']}비트"
         " (gn-voice 의 과매끈 지표. 참고값이며 검사에는 쓰지 않는다)", "",
         "## 5. 길이와 기호", "",
         f"- 본문 줄 길이: 평균 {a['line_len']['mean']}자, 25~75% {a['line_len']['p25']}~{a['line_len']['p75']}자,"
         f" 최소 {a['line_len']['min']} · 최대 {a['line_len']['max']}자",
         f"- 줄 끝 마침표: {_pc(a['period_end_ratio'])} · 줄당 쉼표 {a['comma_per_line']}개 · 줄당 괄호 {a['paren_per_line']}개",
         f"- 줄당 기호(제목 포함): {_fmt(a['symbols'])}", "",
         "## 6. 숫자·날짜 표기", "",
         f"- 날짜: {_fmt(a['dates'])}", f"- 금액 단위: {_fmt(a['money'])}", f"- 비율·증감: {_fmt(a['signs'])}", "",
         "## 7. 자주 쓴 표현 (두 어절, 여러 자료에 나온 것)", "", f"- {_fmt(a['phrases'])}", "",
         "## 8. 본문 예문 (대표 자료에서 그대로)", "", *[f"- {x}" for x in a["examples"]], "",
         "## 9. 검사 기준 (`gate`)", "",
         f"- 아래 지표 중 허용 범위를 벗어난 것이 {ALLOW}개 이하이면 문체 합격. 이모지·ㅋㅋ·금지 상투구는 즉시 불합격.",
         "- 숫자·영문 이름은 근거 파일(`--facts`)과 대조한다. 근거에 없는 값이 생기면 불합격.", "",
         "| 지표 | 대표 자료 범위 | 허용 범위 |", "|---|---|---|",
         *[f"| {HINT[k]} | {b['raw_lo']} ~ {b['raw_hi']} | {b['lo']} ~ {b['hi']} |" for k, b in band.items()], "",
         "이 파일과 corpus/ 에는 대표 자료의 문장이 그대로 들어 있다. 개인정보가 없는지 확인한 뒤 공유한다.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- 검사
def violations_of(deck, band, tells):
    text = "\n".join(x for s in deck["slides"] for x in [s["title"], *s["lines"]])
    v = []
    if EMOJI_RE.search(text):
        v.append({"type": "must_zero", "msg": "이모지 발견"})
    if KH_RE.search(text):
        v.append({"type": "must_zero", "msg": "ㅋㅋ/ㅎㅎ 발견"})
    for p in tells.get("hard", []):
        if p in text:
            v.append({"type": "forbidden_phrase", "msg": p})
    for p, cap in tells.get("capped", {}).items():
        c = text.count(p)
        if c > cap:
            v.append({"type": "tell_cap", "msg": f"{p}x{c}(상한 {cap})"})
    m = deck_metrics(deck)
    oob = [{"metric": k, "value": round(m[k], 3), "expected": [b["lo"], b["hi"]]}
           for k, b in band.items() if k in m and not (b["lo"] <= m[k] <= b["hi"])]
    return v, oob, m


def judge(deck, band, tells, allow=ALLOW):
    v, oob, m = violations_of(deck, band, tells)
    nw = len(windows(style_parts(deck)[1]))
    return {"pass": not v and len(oob) <= allow, "hard": v, "out_of_band": oob, "n_windows": nw,
            "metrics": {k: round(x, 3) for k, x in m.items()}}


def where(deck, o):
    """밴드를 벗어난 장 단위 지표가 어느 장 때문인지 (많이 벗어난 순 3개)."""
    lo, hi = o["expected"]
    high = o["value"] > hi
    rows = []
    for i, s in enumerate(deck["slides"], 1):
        t = clean(s["title"], 2)
        if o["metric"] == "slide_words":
            w = sum(len(x.split()) for x in s["lines"])
            if (w > hi) if high else (0 < w < lo):
                rows.append((abs(w - (hi if high else lo)), f"{i}장 「{t}」 {w}어절"))
        elif o["metric"] == "title_len" and t and ((len(t) > hi) if high else (len(t) < lo)):
            rows.append((abs(len(t) - (hi if high else lo)), f"{i}장 「{t}」 {len(t)}자"))
        elif o["metric"] == "title_sentence" and t and (end_type(t) != "end_other") == high:
            rows.append((0, f"{i}장 「{t}」"))
    return [x for _, x in sorted(rows, key=lambda r: -r[0])[:3]]


# ---------------------------------------------------------------- build
def build(args):
    if not args.human:
        sys.exit("사람이 직접 쓴 자료만 쓸 수 있습니다(--human). AI 도움을 받은 글은 기준을 오염시킵니다")
    docs, rows = [], []
    for i, f in enumerate(map(Path, args.files), 1):
        deck = read_deck(f)
        titles, body, per = style_parts(deck)
        if not windows(body) and not windows(titles):
            sys.exit(f"{f.name}: 문장 줄이 너무 적어 표본을 만들 수 없습니다(본문 {len(body)}줄 · 제목 {len(titles)}개, 둘 중 하나는 3 이상)")
        did = f"D-{i:03d}"
        docs.append((did, f.name, deck))
        rows.append({"id": did, "source_file": f.name, "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                     "doc_type": args.type, "slides": len(deck["slides"]), "titles": len(titles), "lines": len(body),
                     "human_written": True, "included": True, "split": "train",
                     "note": "서식 제거 본문(corpus/)만 보관. 개인정보 점검 후 사용"})
    out = Path(args.out)
    (out / "corpus").mkdir(parents=True, exist_ok=True)
    for did, _, deck in docs:
        md = [f"## {s['title']}\n" + "\n".join(f"- {x}" for x in s["lines"]) for s in deck["slides"]]
        (out / "corpus" / f"{did}.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    (out / "manifest.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    n = len(docs)
    pts = [p for d in docs for p in points(d[2])]

    def run_loo(mu):
        res = []
        for i in range(n if n >= 2 else 0):
            b = make_band([p for j, d in enumerate(docs) if j != i for p in points(d[2])], mu)
            j = judge(docs[i][2], b, AI_TELLS)
            res.append({"held_out": docs[i][0], "pass": j["pass"], "out_of_band": [x["metric"] for x in j["out_of_band"]]})
        return res

    mult, widened = 1.0, False
    loo = run_loo(mult)
    if loo and not all(r["pass"] for r in loo):   # 한 건 빼고 검증이 실패하면 여유를 한 번 넓힌다
        mult, widened = LOO_WIDEN, True
        loo = run_loo(mult)
    status = "trial" if n < 2 else ("verified" if all(r["pass"] for r in loo) else "unverified")
    label = "문체 미검증" if status == "unverified" else {"trial": "문체 시험용(1건)", "small": "문체 소표본", "normal": "문체 표본"}[tier(n)]
    band = make_band(pts, mult)
    meta = {"generator": "scripts/voice_tool.py", "built": datetime.now(KST).replace(microsecond=0).isoformat(),
            "n_docs": n, "n_points": len(pts), "unit": f"본문 {WINDOW}줄 · 제목 {WINDOW}개 묶음, 장", "tier": tier(n),
            "status": status, "label": label, "slack_mult": mult, "widened_after_loo": widened, "allow_out_of_band": ALLOW,
            "leave_one_out": loo,
            "note": "점 5개 미만이면 min~max, 이상이면 5~95% 분위수 + 여유. 자료가 늘면 build 를 다시 돌린다."}
    (out / "fingerprint-slim.json").write_text(json.dumps({"meta": meta, "doc_type": args.type, "band": band},
                                                          ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "ai-tells.json").write_text(json.dumps(AI_TELLS, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    a = analyze(docs)
    rules = rules_of(a)
    prof = {"doc_type": args.type, "status": status, "label": label, "evidence": [r["id"] for r in rows],
            "rules": rules, "analysis": a,
            "band_rules": [f"{k}: {b['raw_lo']} ~ {b['raw_hi']} (허용 {b['lo']} ~ {b['hi']})" for k, b in band.items()],
            "always": ["웹슬라이드 규칙 우선(서체·색·한 장 한 메시지·근거 배지)", "이모지·ㅋㅋ 금지",
                       "AI 상투구 금지(ai-tells.json)", "숫자·영문 이름은 근거 그대로(gate --facts)"]}
    (out / "style-profile.json").write_text(json.dumps(prof, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "style-guide.md").write_text(guide_md(args.type, meta, rows, a, rules, band), encoding="utf-8")
    print(json.dumps({"out": str(out), "guide": str(out / "style-guide.md"), "n_docs": n, "n_points": len(pts),
                      "tier": tier(n), "status": status, "label": label, "widened": widened, "leave_one_out": loo,
                      "rules": rules}, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- 숫자 대조 · gate
NUM_RE = re.compile(r"\d[\d,.]*\s?[%가-힣a-zA-Z]{0,3}")
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{1,}")
_LIST_NO = re.compile(r"(?m)^[ \t□■○◦●ㅇ\-\*※•▪·∙]*\d{1,2}\.(?=\s)")
_YMD = re.compile(r"\b((?:19|20)\d{2})\.\s?(\d{1,2})(?:\.\s?(\d{1,2}))?(?!\d)")
_YY = re.compile(r"['’‘](\d{2})(?=\s?년|\.)")


def assets(text):
    """숫자와 영문 이름 모음 (koscom-hwp-report 와 같은 규칙: 줄 머리 번호 제외, 날짜는 연·월·일로, '26 = 2026)."""
    text = _YY.sub(r"20\1", _LIST_NO.sub("", text))
    text = _YMD.sub(lambda m: " ".join(g for g in m.groups() if g), text)
    nums = {re.sub(r"[^\d.]", "", m.group()).strip(".") for m in NUM_RE.finditer(text)}
    nums = {x.lstrip("0") if re.fullmatch(r"0\d+", x) else x for x in nums}
    return {x for x in nums if x}, {m.group().lower() for m in LATIN_RE.finditer(text)}


def fidelity_of(src, out):
    sn, sl = assets(src)
    on, ol = assets(out)
    return {"missing": sorted(sn - on) + sorted(sl - ol), "invented": sorted(on - sn) + sorted(ol - sl)}


def _load(voice):
    v = Path(voice)
    try:
        return (json.loads((v / "fingerprint-slim.json").read_text(encoding="utf-8")),
                json.loads((v / "ai-tells.json").read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        sys.exit(f"문체 폴더를 읽지 못했습니다({v}): {e}. 먼저 build 를 돌리세요")


def gate(args):
    """덱 하나에 문체 검사와 숫자 대조를 함께 하고, 고칠 항목과 제목 목록을 낸다.
    mode=create: 새로 쓴 덱. 근거(facts)에 없는 숫자·영문 이름이 생기면 불합격, 안 쓴 근거는 참고만.
    mode=rewrite: 기존 자료를 고쳐 쓴 덱. 사라진 것도 불합격."""
    if args.voice:
        slim, tells = _load(args.voice)
        band, label, ref_only = slim["band"], slim["meta"]["label"], slim["meta"]["tier"] == "trial"
    else:
        band, tells, label, ref_only = {}, AI_TELLS, "문체 기준 없음(상투구·숫자만 검사)", False
    deck = read_deck(args.file)
    if not deck["slides"]:
        sys.exit("검사할 장을 찾지 못했습니다(.html 은 <section class=\"slide\">, .md 는 # 제목 또는 --- 로 장을 나눕니다)")
    style = judge(deck, band, tells)
    fid = fidelity_of("\n".join(all_text(read_deck(f)) for f in args.facts), all_text(deck)) if args.facts else None
    fid_pass = fid is None or (not fid["invented"] and (args.mode == "create" or not fid["missing"]))
    todo = [f"[금지] {h['msg']}: 이 표현을 빼고 다시 쓰세요" for h in style["hard"]]
    for o in style["out_of_band"]:
        lo, hi = o["expected"]
        way = "높습니다 -> 줄이세요" if o["value"] > hi else "낮습니다 -> 늘리세요"
        at = where(deck, o)
        todo.append(f"[문체] {HINT[o['metric']]}: {o['value']} (허용 {lo}~{hi}) {way}" + (f" — {', '.join(at)}" if at else ""))
    if fid is not None:
        todo += [f"[숫자] 근거에 없는 값 '{x}': 근거대로 고치거나 [확인 필요]로 표시하세요" for x in fid["invented"]]
        if args.mode == "rewrite":
            todo += [f"[숫자] 원문에 있던 '{x}'가 사라졌습니다: 되살리세요" for x in fid["missing"]]
    ok = style["pass"] and fid_pass
    res = {"pass": ok, "style_pass": style["pass"], "fidelity_pass": fid_pass if fid is not None else None,
           "label": label, "reference_only": ref_only, "rework": todo,
           "unused_facts": (fid or {}).get("missing", []) if args.mode == "create" else [],
           "out_of_band": style["out_of_band"], "n_slides": len(deck["slides"]), "n_windows": style["n_windows"],
           "titles": [f"{i}. {s['title']}" for i, s in enumerate(deck["slides"], 1)]}
    print(json.dumps(res, ensure_ascii=False))
    return 0 if ok else 3


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build", help="대표 자료 -> 문체 폴더")
    b.add_argument("files", nargs="+")
    b.add_argument("--out", required=True)
    b.add_argument("--type", default="발표자료")
    b.add_argument("--human", action="store_true", help="사람이 직접 쓴 자료임을 확인")
    b.set_defaults(fn=build)
    g = sp.add_parser("gate", help="덱 검사: 문체(--voice 가 있을 때) + 상투구 + 숫자 대조(--facts)")
    g.add_argument("--voice", help="build 로 만든 문체 폴더(없으면 상투구·숫자만 검사)")
    g.add_argument("--facts", action="append", default=[], help="근거 파일(여러 개면 --facts 를 반복)")
    g.add_argument("--mode", choices=["create", "rewrite"], default="create")
    g.add_argument("file")
    g.set_defaults(fn=gate)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
