#!/usr/bin/env python3
"""studio.py · finalize.py 자체검사. 실행: python scripts/studio_selftest.py   (build_single 이 쓰는 Pillow·fontTools 필요, 30초 안팎)
  1. 템플릿 정보: 장·부록·프리셋 번호가 템플릿 범위 안
  2. 보안: 토큰 없는 POST·다른 Host 는 403, ../ 경로는 404
  3. 서식 고르기: 잘못된 입력은 400, 고른 장·부록·제목(이스케이프)·상단 바로 deck/ 생성, choice.json 기록
  4. 저장: 덱 HTML 이 아니면 400, 저장하면 deck/index.html 이 바뀌고 이전 판이 studio/history 에 남음
  5. 다시 고르기: 기존 덱은 지우지 않고 studio/history/deck-<시각> 으로 옮김
  6. --wait: 실행 뒤에 고른 서식만 인정
  7. 최종본: 검사 합격 -> exports/<제목>_ver1.html·ver2, AI 상투구가 있으면 번호를 쓰지 않고 불합격
"""
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import finalize  # noqa: E402
import studio  # noqa: E402


def req(port, method, path, body=None, token=None, host=None, ctype="application/json"):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    h = {"Host": host or f"127.0.0.1:{port}"}
    if token:
        h["X-Studio-Token"] = token
    if body is not None:
        body = body if isinstance(body, bytes) else json.dumps(body).encode()
        h["Content-Type"] = ctype
    c.request(method, path, body=body, headers=h)
    r = c.getresponse()
    data = r.read()
    c.close()
    try:
        return r.status, json.loads(data)
    except ValueError:
        return r.status, data.decode("utf-8", "replace")


def main():
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "proj"
        httpd = studio.serve(proj, 0, browser=False)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            # 1
            st, t = req(port, "GET", "/api/template")
            assert st == 200 and len(t["slides"]) >= 10 and {s["key"] for s in t["sides"]} >= {"basis", "sources"}, t
            for p in t["presets"]:
                assert all(1 <= k <= len(t["slides"]) for k in p["keep"]), p
                assert set(p["sides"]) <= {s["key"] for s in t["sides"]}, p
            st, token = req(port, "GET", "/api/token")
            assert st == 200 and len(token) > 20

            # 2
            good = {"title": "시험 덱 <b>&", "keep": [1, 2, 23], "sides": ["basis"], "brand": "경영지원부", "pill": "보고"}
            assert req(port, "POST", "/api/create", good)[0] == 403, "토큰 없는 요청은 막는다"
            assert req(port, "POST", "/api/create", good, token="wrong")[0] == 403
            assert req(port, "POST", "/api/create", good, token=token, host="evil.example:80")[0] == 403, "다른 Host 는 막는다"
            assert req(port, "GET", "/api/token", host="evil.example")[0] == 403
            assert req(port, "GET", "/ui/%2e%2e/scripts/studio.py")[0] == 404, "../ 로 스킬 밖 파일을 읽지 못한다"
            assert req(port, "GET", "/deck/..%2f..%2fsecret.txt")[0] == 404

            # 3
            for bad in ({**good, "title": " "}, {**good, "keep": [99]}, {**good, "keep": []}, {**good, "sides": ["zz"]}):
                st, r = req(port, "POST", "/api/create", bad, token=token)
                assert st == 400 and not r["ok"], (bad, r)
            st, r = req(port, "POST", "/api/create", good, token=token)
            assert st == 200 and r["ok"] and r["choice"]["slides"] == 3, r
            index = proj / "deck" / "index.html"
            h = index.read_text(encoding="utf-8")
            assert "<title>시험 덱 &lt;b&gt;&amp;</title>" in h and 'id="side-basis"' in h and 'id="side-qa"' not in h
            assert "경영지원부<span class=\"div\"></span>" in h and '<span class="pill"><i>보</i>보고</span>' in h
            assert json.loads((proj / "studio" / "choice.json").read_text(encoding="utf-8"))["keep"] == [1, 2, 23]
            st, s = req(port, "GET", "/api/state")
            assert s["deck"] and s["slides"] == 3 and s["title"] == "시험 덱 <b>&", s
            st, page = req(port, "GET", "/deck/index.html")
            assert st == 200 and '<section class="slide' in page

            # 4
            assert req(port, "POST", "/api/save", b"<html>no</html>", token=token, ctype="text/html")[0] == 400
            edited = h.replace("<title>시험 덱 &lt;b&gt;&amp;</title>", "<title>고친 제목</title>")
            st, r = req(port, "POST", "/api/save", edited.encode(), token=token, ctype="text/html")
            assert st == 200 and r["ok"] and "<title>고친 제목</title>" in index.read_text(encoding="utf-8"), r
            assert list((proj / "studio" / "history").glob("index-*.html")), "저장 전 판을 남긴다"

            # 5
            st, r = req(port, "POST", "/api/create", {**good, "title": "둘째 서식", "keep": [1, 23]}, token=token)
            assert st == 200 and r["choice"]["slides"] == 2 and r["choice"]["previous_deck"], r
            moved = Path(r["choice"]["previous_deck"])
            assert (moved / "index.html").read_text(encoding="utf-8").count("<title>고친 제목</title>") == 1, "기존 덱을 지우지 않는다"
        finally:
            httpd.shutdown()

        # 6
        choice = proj / "studio" / "choice.json"
        old = time.time() - 600
        os.utime(choice, (old, old))
        assert studio.wait_choice(proj, 1) == 2, "실행 전에 고른 서식은 기다림을 끝내지 않는다"
        os.utime(choice, None)
        assert studio.wait_choice(proj, 1) == 0

        # 7
        assert finalize.safe_name('본사 "소방"/배관: 교체?') == "본사 _소방_배관_ 교체"
        fin = [sys.executable, str(HERE / "finalize.py"), str(proj), "--skip-check"]
        for v in (1, 2):
            r = subprocess.run(fin, capture_output=True, timeout=600)
            res = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
            assert r.returncode == 0 and res["ok"] and res["version"] == v, res
        exports = proj / "exports"
        assert (exports / "둘째 서식_ver2.html").is_file() and json.loads((exports / "둘째 서식_ver2.json").read_text(encoding="utf-8"))["check"]["skipped"]
        index = proj / "deck" / "index.html"
        index.write_text(index.read_text(encoding="utf-8").replace("</h1>", " 살펴보겠습니다</h1>", 1), encoding="utf-8")
        r = subprocess.run(fin, capture_output=True, timeout=600)
        res = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
        assert r.returncode == 3 and res["stage"] == "gate" and any("살펴보겠습니다" in x for x in res["rework"]), res
        assert not (exports / "둘째 서식_ver3.html").exists(), "불합격이면 번호를 쓰지 않는다"
    print("studio_selftest OK")


if __name__ == "__main__":
    main()
