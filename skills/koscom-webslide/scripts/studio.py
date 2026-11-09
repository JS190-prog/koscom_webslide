#!/usr/bin/env python3
"""웹슬라이드 스튜디오 — 작업 전에 브라우저에서 서식을 고르고, 만든 덱을 고치고, 최종본을 만든다 (표준 라이브러리만).

deck-design-pack(ppt-master)의 확인 페이지 흐름(추천 → 브라우저에서 고름 → 결과 파일을 에이전트가 읽음)을
웹슬라이드에 맞게 줄였다. 서식 = 템플릿에서 고른 장·부록과 덱 정보(제목·상단 바·꼬리표)다.

  python studio.py <프로젝트>           서버를 띄우고 브라우저를 연다(에이전트는 배경으로 실행한다)
  python studio.py <프로젝트> --wait    브라우저에서 「이 서식으로 만들기」를 누를 때까지 기다렸다가 choice.json 을 출력한다
  python studio.py --thumbs             템플릿 장 미리보기 그림(studio/thumbs)을 다시 만든다. 템플릿을 고쳤을 때만

프로젝트 폴더
  deck/                    작업본(폴더판). 덱을 스튜디오에서 열어 편집 모드(E)로 「HTML 저장」하면 여기에 쓴다
  facts/ · voice/          숫자 근거 · 문체 폴더(있으면 최종본 검사에 쓴다)
  studio/choice.json       고른 서식      studio/history/   덮어쓰기 전 백업(덱 폴더 · index.html)
  exports/<제목>_verN.html  최종본(+ .json 검사 기록) — finalize.py

보안: 127.0.0.1 에만 연다. 바꾸는 요청(POST)은 이 서버가 낸 토큰 헤더와 Host 가 맞아야 받는다(다른 사이트가 덱을 덮어쓰지 못하게).
"""
import argparse
import html
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
UI = HERE.parent / "studio"
sys.path.insert(0, str(HERE))
import new_deck  # noqa: E402

MAX_BODY = 40 * 1024 * 1024
PRESETS = [  # 장 번호는 템플릿 기준(1부터). 템플릿을 바꾸면 함께 고친다
    {"name": "보고·브리핑 8장", "keep": [1, 2, 3, 4, 7, 20, 21, 23], "sides": ["basis", "sources"]},
    {"name": "짧은 소개 5장", "keep": [1, 2, 7, 8, 23], "sides": ["sources"]},
    {"name": "제안·공모전 전체", "keep": list(range(1, 24)), "sides": ["basis", "sources", "qa", "gallery", "video", "live"]},
]


def stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def deck_title(index):
    m = re.search(r"<title>([^<]*)</title>", index.read_text(encoding="utf-8", errors="replace"))
    return html.unescape(m.group(1)).strip() if m else ""


def template_info():
    _, _, labels, sides = new_deck.template_parts()
    return {"slides": [{"n": i, "label": l} for i, l in enumerate(labels, 1)],
            "sides": [{"key": k, "label": l} for k, l in sides], "presets": PRESETS}


def state(proj):
    index = proj / "deck" / "index.html"
    choice = proj / "studio" / "choice.json"
    exports = proj / "exports"
    return {"project": str(proj), "deck": index.exists(),
            "title": deck_title(index) if index.exists() else "",
            "slides": len(new_deck.SEC.findall(index.read_text(encoding="utf-8"))) if index.exists() else 0,
            "choice": json.loads(choice.read_text(encoding="utf-8")) if choice.exists() else None,
            "exports": sorted((p.name for p in exports.glob("*.html")), key=lambda n: (len(n), n)) if exports.is_dir() else []}


def _text(v, n):
    return str(v or "").strip()[:n]


def create(proj, req):
    """고른 서식으로 deck/ 을 만든다. 이미 있으면 studio/history/deck-<시각> 으로 옮겨 두고 새로 만든다."""
    info = template_info()
    title = _text(req.get("title"), 80)
    if not title:
        raise ValueError("덱 제목을 적어 주세요")
    try:
        keep = sorted({int(x) for x in req.get("keep") or []})
    except (TypeError, ValueError):
        raise ValueError("장 번호가 숫자가 아닙니다")
    if not keep or keep[0] < 1 or keep[-1] > len(info["slides"]):
        raise ValueError(f"장을 하나 이상 고르세요(1~{len(info['slides'])})")
    all_sides = {s["key"] for s in info["sides"]}
    keep_sides = set(req.get("sides") or [])
    if not keep_sides <= all_sides:
        raise ValueError(f"알 수 없는 부록: {sorted(keep_sides - all_sides)}")
    deck = proj / "deck"
    moved = None
    if deck.exists() and any(deck.iterdir()):
        hist = proj / "studio" / "history"
        hist.mkdir(parents=True, exist_ok=True)
        moved = hist / f"deck-{stamp()}"
        shutil.move(str(deck), str(moved))
    drop = all_sides - keep_sides
    n, dropped = new_deck.make_deck(str(deck), title=title, keep=set(keep), drop=drop, no_motion="video" in drop,
                                    brand=_text(req.get("brand"), 40) or "코스콤", brand_en=_text(req.get("brand_en"), 40),
                                    pill=_text(req.get("pill"), 40) or None)
    choice = {"title": title, "keep": keep, "labels": [info["slides"][k - 1]["label"] for k in keep],
              "sides": sorted(keep_sides), "brand": _text(req.get("brand"), 40) or "코스콤",
              "brand_en": _text(req.get("brand_en"), 40), "pill": _text(req.get("pill"), 40),
              "created_at": datetime.now().astimezone().replace(microsecond=0).isoformat(), "slides": n,
              "previous_deck": str(moved) if moved else None}
    (proj / "studio").mkdir(exist_ok=True)
    (proj / "studio" / "choice.json").write_text(json.dumps(choice, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"ok": True, "choice": choice, "state": state(proj)}


def save(proj, body):
    """편집 모드의 「HTML 저장」: deck/index.html 을 바꾸기 전에 studio/history 에 한 판 남긴다."""
    text = body.decode("utf-8")
    if '<section class="slide' not in text or 'id="deck-data"' not in text:
        raise ValueError("웹슬라이드 덱 HTML이 아닙니다")
    dest = proj / "deck" / "index.html"
    if not dest.exists():
        raise ValueError("먼저 서식을 골라 덱을 만드세요")
    hist = proj / "studio" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    backup = hist / f"index-{stamp()}.html"
    shutil.copy2(dest, backup)
    tmp = dest.with_suffix(".saving")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dest)
    return {"ok": True, "saved": str(dest), "backup": str(backup)}


def finalize(proj):
    r = subprocess.run([sys.executable, str(HERE / "finalize.py"), str(proj)], capture_output=True, timeout=1200)
    lines = r.stdout.decode("utf-8", "replace").strip().splitlines()
    try:
        return json.loads(lines[-1])
    except (IndexError, ValueError):
        return {"ok": False, "stage": "finalize", "error": r.stderr.decode("utf-8", "replace")[-600:]}


class Handler(BaseHTTPRequestHandler):
    proj = None      # serve() 가 채운다
    token = None
    port = None

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _file(self, base, rel):
        base = base.resolve()
        p = (base / rel).resolve()
        if p != base and base not in p.parents:          # ../ 로 밖으로 나가는 경로
            return self._json(404, {"error": "not found"})
        if p.is_dir():
            p = p / "index.html"
        if not p.is_file():
            return self._json(404, {"error": "not found"})
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, p.read_bytes(), ctype)

    def _host_ok(self):
        return self.headers.get("Host") in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "host"})
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self._file(UI, "index.html")
        if path.startswith("/ui/"):
            return self._file(UI, path[4:])
        if path == "/api/token":                          # 같은 출처 페이지만 응답을 읽을 수 있다
            return self._send(200, self.token.encode(), "text/plain; charset=utf-8")
        if path == "/api/state":
            return self._json(200, state(self.proj))
        if path == "/api/template":
            return self._json(200, template_info())
        if path.startswith("/deck/"):
            return self._file(self.proj / "deck", path[len("/deck/"):])
        if path.startswith("/exports/"):
            return self._file(self.proj / "exports", path[len("/exports/"):])
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-Studio-Token") != self.token:
            return self._json(403, {"ok": False, "error": "스튜디오 토큰이 맞지 않습니다. 스튜디오 페이지를 새로 고침하세요"})
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            return self._json(413, {"ok": False, "error": "너무 큽니다"})
        body = self.rfile.read(n)
        path = urlparse(self.path).path
        try:
            if path == "/api/create":
                return self._json(200, create(self.proj, json.loads(body or b"{}")))
            if path == "/api/save":
                return self._json(200, save(self.proj, body))
            if path == "/api/finalize":
                return self._json(200, finalize(self.proj))
        except (ValueError, FileExistsError, UnicodeDecodeError) as e:
            return self._json(400, {"ok": False, "error": str(e)})
        self._json(404, {"ok": False, "error": "not found"})


def serve(proj, port=0, browser=True):
    proj.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    Handler.proj, Handler.token, Handler.port = proj, secrets.token_urlsafe(24), httpd.server_address[1]
    url = f"http://127.0.0.1:{Handler.port}/"
    (proj / "studio").mkdir(exist_ok=True)
    (proj / "studio" / "server.json").write_text(json.dumps({"url": url, "pid": os.getpid()}) + "\n", encoding="utf-8")
    print(json.dumps({"studio": url, "project": str(proj)}, ensure_ascii=False), flush=True)
    if browser:
        webbrowser.open(url)
    return httpd


def wait_choice(proj, timeout):
    """이 명령을 실행한 뒤에 고른 서식(choice.json)이 생길 때까지 기다린다."""
    f = proj / "studio" / "choice.json"
    start, deadline = time.time(), time.time() + timeout
    while time.time() < deadline:
        if f.exists() and f.stat().st_mtime >= start - 1:
            print(f.read_text(encoding="utf-8"))
            return 0
        time.sleep(1)
    print(json.dumps({"waiting": True, "msg": "아직 서식을 고르지 않았습니다. 페이지는 열려 있으니 --wait 를 다시 실행하세요"},
                     ensure_ascii=False))
    return 2


def make_thumbs():
    """템플릿 → 단일 파일 → check_deck --shots → 480px webp (studio/thumbs). node·playwright-core·Pillow 필요."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        single, shots = Path(td) / "tpl.html", Path(td) / "shots"
        subprocess.run([sys.executable, str(HERE / "build_single.py"), str(HERE.parent / "template"), str(single)], check=True)
        subprocess.run(["node", str(HERE / "check_deck.js"), str(single), "--shots", str(shots)], check=True)
        out = UI / "thumbs"
        out.mkdir(parents=True, exist_ok=True)
        for png in sorted(shots.glob("*.png")):
            im = Image.open(png).convert("RGB")
            im.thumbnail((480, 270))
            im.save(out / (png.stem + ".webp"), "WEBP", quality=78)
        print(f"미리보기 {len(list(shots.glob('*.png')))}장 -> {out}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?")
    ap.add_argument("--port", type=int, default=0, help="0 이면 빈 포트")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--wait", action="store_true", help="서식을 고를 때까지 기다린다(서버는 따로 떠 있어야 한다)")
    ap.add_argument("--timeout", type=int, default=540, help="--wait 최대 초(기본 540, 에이전트 도구 한도 아래)")
    ap.add_argument("--thumbs", action="store_true")
    a = ap.parse_args()
    if a.thumbs:
        return make_thumbs()
    if not a.project:
        ap.error("프로젝트 폴더를 주세요")
    proj = Path(a.project).resolve()
    if a.wait:
        return wait_choice(proj, a.timeout)
    httpd = serve(proj, a.port, not a.no_browser)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
