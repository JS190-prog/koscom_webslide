#!/usr/bin/env python3
"""최종본 만들기: 검사(gate) → 단일 파일(build_single) → 점검(check_deck) 을 모두 통과해야
<프로젝트>/exports/<제목>_verN.html 로 남긴다(N 은 1부터 자동으로 올라간다). 실패하면 번호를 쓰지 않는다.

  python finalize.py <프로젝트> [--facts 파일 …] [--voice 폴더] [--mode create|rewrite] [--skip-check]

- 근거: --facts 를 안 주면 <프로젝트>/facts/ 의 파일을 모두 쓴다(없으면 숫자 대조 없이 상투구·문체만 검사)
- 문체: --voice 를 안 주면 <프로젝트>/voice/ 가 있을 때 쓴다
- 점검에는 node 와 playwright-core 가 필요하다(PLAYWRIGHT_CORE 로 경로 지정 가능). 못 돌리는 환경이면 --skip-check,
  그때 검사 기록에 "점검 생략"이 남는다
- 결과: 마지막 줄 JSON 한 줄(studio.py 가 읽는다). 종료 코드 0 = 최종본 생성, 3 = 검사·점검 불합격, 2 = 입력 오류
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def out(obj, code):
    print(json.dumps(obj, ensure_ascii=False))
    return code


def safe_name(title):
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", title).strip(" ._")
    return s[:60] or "deck"


def next_version(exports, name):
    nums = [int(m.group(1)) for p in exports.glob(f"{name}_ver*.html")
            if (m := re.fullmatch(re.escape(name) + r"_ver(\d+)\.html", p.name))]
    return max(nums, default=0) + 1


def json_tail(text):
    """출력에서 마지막 JSON 덩어리(check_deck 은 여러 줄 JSON 뒤에 판정 한 줄을 찍는다)."""
    i, j = text.find("{"), text.rfind("}")
    return json.loads(text[i:j + 1]) if i >= 0 < j else None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--facts", action="append")
    ap.add_argument("--voice")
    ap.add_argument("--mode", choices=["create", "rewrite"], default="create")
    ap.add_argument("--skip-check", action="store_true")
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    deck = proj / "deck"
    index = deck / "index.html"
    if not index.is_file():
        return out({"ok": False, "stage": "input", "error": f"덱이 없습니다: {index}. 먼저 studio.py 로 서식을 고르세요"}, 2)
    facts = a.facts or ([str(p) for p in sorted((proj / "facts").iterdir()) if p.is_file()] if (proj / "facts").is_dir() else [])
    voice = a.voice or (str(proj / "voice") if (proj / "voice" / "fingerprint-slim.json").exists() else None)

    # 1) 문체·숫자 검사
    cmd = [sys.executable, str(HERE / "voice_tool.py"), "gate", "--mode", a.mode, str(index)]
    cmd += ["--voice", voice] if voice else []
    for f in facts:
        cmd += ["--facts", f]
    r = subprocess.run(cmd, capture_output=True, timeout=300)
    try:
        gate = json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        return out({"ok": False, "stage": "gate", "error": r.stderr.decode("utf-8", "replace")[-600:]}, 2)
    gsum = {k: gate.get(k) for k in ("pass", "label", "style_pass", "fidelity_pass", "n_slides")}
    gsum.update({"voice": Path(voice).name if voice else None, "facts": [Path(f).name for f in facts]})
    if r.returncode != 0:
        return out({"ok": False, "stage": "gate", "gate": gsum, "rework": gate.get("rework", []),
                    "msg": "검사 불합격 — rework 항목을 고친 뒤 다시 실행하세요"}, 3)

    # 2) 단일 파일
    m = re.search(r"<title>([^<]*)</title>", index.read_text(encoding="utf-8"))
    title = html.unescape(m.group(1)).strip() if m else ""
    name = safe_name(title)
    exports = proj / "exports"
    exports.mkdir(exist_ok=True)
    work = proj / "studio"
    work.mkdir(exist_ok=True)
    build = work / "build.html"
    b = subprocess.run([sys.executable, str(HERE / "build_single.py"), str(deck), str(build)], capture_output=True, timeout=900)
    if b.returncode != 0 or not build.is_file():
        return out({"ok": False, "stage": "build", "gate": gsum, "error": b.stderr.decode("utf-8", "replace")[-600:]}, 3)

    # 3) 점검
    if a.skip_check:
        check = {"skipped": True, "note": "점검 생략(--skip-check)"}
    else:
        if not shutil.which("node"):
            return out({"ok": False, "stage": "check", "gate": gsum, "error": "node 가 없습니다. 설치하거나 --skip-check"}, 2)
        c = subprocess.run(["node", str(HERE / "check_deck.js"), str(build)], capture_output=True, timeout=900)
        text = c.stdout.decode("utf-8", "replace")
        if c.returncode == 3:
            return out({"ok": False, "stage": "check", "gate": gsum,
                        "error": "playwright-core 를 찾지 못했습니다. PLAYWRIGHT_CORE 로 경로를 지정하거나 --skip-check"}, 2)
        try:
            check = json_tail(text) or {}
        except ValueError:
            check = {"raw": text[-600:]}
        check["pass"] = c.returncode == 0
        if c.returncode != 0:
            return out({"ok": False, "stage": "check", "gate": gsum, "check": check,
                        "msg": "점검 불합격 — 외부 요청·스크립트 오류·용량을 고친 뒤 다시 실행하세요", "build": str(build)}, 3)

    # 4) 번호를 붙여 남긴다
    n = next_version(exports, name)
    final = exports / f"{name}_ver{n}.html"
    os.replace(build, final)
    report = {"version": n, "file": final.name, "title": title,
              "built_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
              "deck_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
              "size_mb": round(final.stat().st_size / 1e6, 2), "gate": gsum, "check": check}
    rep = final.with_suffix(".json")
    rep.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out({"ok": True, "version": n, "file": str(final), "report": str(rep), "gate": gsum,
                "check": "생략" if a.skip_check else "통과"}, 0)


if __name__ == "__main__":
    sys.exit(main())
