#!/usr/bin/env python3
"""voice_tool 자체검사 (표준 라이브러리만). 실행: python scripts/voice_selftest.py
  1. 끝맺음 분류: '~ 필요'는 명사형, '~씁니다'는 존댓말
  2. 웹슬라이드 읽기: 근거 배지·장 번호·꼬리표·버튼·data-gen·상단 바는 빠지고, 표·부록·deck-data 는 숫자 대조에만
  3. .pptx 읽기: 제목 개체, 줄바꿈, 쪽 번호 제외, 숨긴 장 제외, 표, 제목 개체가 없을 때 가장 큰 글자
  4. .md 읽기: # 제목·--- 로 장 나누기, 표는 숫자 대조에만
  4b. .hwpx 읽기: 본문 문단은 측정, 표 칸 글은 숫자 대조에만, 본문이 표 안에만 있으면 표 안을 본문으로
  5. 대표 자료 3건 build -> 문체 소표본·한 건 빼고 검증 통과·style-guide.md
  6. 같은 문체의 새 덱은 합격, AI투 합쇼체 덱은 불합격(제목 비율·끝맺음), 금지 상투구·이모지는 즉시 불합격
  7. 예시 덱(template)으로 만든 기준에 예시 덱 자신은 합격 (대표 자료와 검사 대상이 같은 규칙으로 읽힘)
  8. 숫자를 바꾸면 gate 가 잡는다 (본문 숫자와 차트 데이터 모두)
  9. --human 없이는 거부하고 아무것도 쓰지 않는다
"""
import contextlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import voice_tool as vt  # noqa: E402

TEMPLATE = HERE.parent / "template" / "index.html"


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = vt.main(list(argv))
    return code, json.loads(out.getvalue())


TOPICS = ["교육", "점검", "보수", "구매", "운영", "보안", "예산"]


def noun_deck(seed):
    """명사형 제목·명사형 항목의 보고 덱(같은 작성자 문체)."""
    out = []
    for i in range(7):
        t = TOPICS[(i + seed) % 7]
        out += [f"## {t} 추진 현황 및 {['계획', '결과', '과제'][(i + seed) % 3]}",
                f"- {t} 대상 범위 확정 및 일정 수립 {i + seed + 2}건",
                f"- 부서별 {t} 담당자 지정 완료",
                f"- 차주 {t} 결과 점검 예정" + (" (월 1회)" if i % 2 else "")]
    return "\n".join(out)


def ai_deck(extra=""):
    out = []
    for t in TOPICS:
        out += [f"## {t} 프로그램은 조직의 경쟁력을 높이는 핵심 요소입니다",
                f"- 현재 {t} 프로그램은 다양한 부서에서 활발하게 운영되고 있으며 긍정적인 반응을 얻고 있습니다.",
                "- 이러한 흐름 속에서 체계적인 관리 방안을 마련하는 것이 무엇보다 중요하다고 판단됩니다.",
                "- 따라서 앞으로도 지속적인 개선 노력을 통해 더 나은 성과를 만들어 갈 수 있을 것입니다." + extra]
    return "\n".join(out)


MINI = """<div class="topbar">상단 바 2026</div>
<section class="slide"><div class="kick a"><span class="no">03</span>THE PROBLEM</div>
<h2 class="t">업무시간의 <em>35%</em>, 보고서에 씁니다</h2>
<p class="lead">사람인 조사입니다.<span class="ev ext">외부 조사</span></p>
<div class="chip-row"><span class="tag">PPT</span><span class="tag">한글 문서</span></div>
<div class="side-links"><button class="side-link">출처 보기 ↗</button></div>
<div data-gen>자동 생성 글</div>
<table><tr><td>표 칸 120만원</td></tr></table>
<p>첫째 줄<br>이어지는 줄
<div class="pain"><span class="n">1</span><h4>형식마다 재작성</h4></div>
<aside class="notes"><p>대본에서 <strong>77만원</strong>을 말합니다.</p></aside>
</section>
<aside class="side-page"><p>부록 근거 500명</p></aside>
<script type="application/json" id="deck-data">{"charts":{"c":{"kind":"vbar","types":["t","n"],"rows":[["항목",440],["둘째",3.30]]}}}</script>"""

P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def sp(text_paras, ph=None, sz=None, y=None):
    php = f'<p:nvPr><p:ph type="{ph}"/></p:nvPr>' if ph else "<p:nvPr/>"
    xfrm = f'<p:spPr><a:xfrm><a:off x="0" y="{y}"/></a:xfrm></p:spPr>' if y is not None else "<p:spPr/>"
    rpr = f'<a:rPr sz="{sz}"/>' if sz else ""
    paras = "".join(f"<a:p>{''.join(f'<a:r>{rpr}<a:t>{t}</a:t></a:r>' if t != '<br>' else '<a:br/>' for t in p)}</a:p>" for p in text_paras)
    return f"<p:sp><p:nvSpPr>{php}</p:nvSpPr>{xfrm}<p:txBody>{paras}</p:txBody></p:sp>"


def slide(body, show=None):
    s = f' show="{show}"' if show else ""
    return f'<p:sld {P}{s}><p:cSld><p:spTree>{body}</p:spTree></p:cSld></p:sld>'


def make_pptx(path):
    tbl = ('<p:graphicFrame><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>예산</a:t></a:r></a:p></a:txBody></a:tc>'
           '<a:tc><a:txBody><a:p><a:r><a:t>480만원</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("ppt/slides/slide1.xml", slide(sp([["대표 제목입니다"]], "title") + sp([["첫 항목 내용 정리"], ["둘째", "<br>", "항목 이어짐"]], "body")
                                               + sp([["7"]], "sldNum") + tbl))
        z.writestr("ppt/slides/slide2.xml", slide(sp([["숨긴 장 제목"]], "title"), show="0"))
        z.writestr("ppt/slides/slide10.xml", slide(sp([["머리글 작은 글"]], sz=1200, y=0) + sp([["가장 큰 제목 글자"]], sz=2800, y=500)))


def main():
    # 1
    for line, want in [("보수 예산 반영 필요", "end_other"), ("검토하였습니다", "end_polite"), ("보고서에 씁니다", "end_polite"),
                       ("점검 완료함", "end_m"), ("다음 달에 반영한다", "end_da"), ("다음", "end_other")]:
        assert vt.end_type(line) == want, (line, vt.end_type(line), want)

    # 2
    d = vt.read_html(MINI)
    assert len(d["slides"]) == 1, d
    s = d["slides"][0]
    assert s["title"] == "업무시간의 35%, 보고서에 씁니다" and s["em"] == 1, s
    assert s["lines"] == ["사람인 조사입니다.", "PPT 한글 문서", "첫째 줄 이어지는 줄", "1", "형식마다 재작성"], s["lines"]
    assert vt.end_type(s["lines"][0]) == "end_polite"
    assert {"표 칸 120만원", "부록 근거 500명", "440", "대본에서 77만원을 말합니다."} <= set(d["extra"]), d["extra"]   # 대본은 문체 측정에서 빠지고 숫자 대조에 든다
    whole = json.dumps(d, ensure_ascii=False)
    for gone in ("상단 바", "THE PROBLEM", "출처 보기", "자동 생성 글", "외부 조사"):
        assert gone not in whole, gone
    assert "vbar" not in d["extra"] and "t" not in d["extra"], "차트 설정값(kind·types)은 숫자 대조에 넣지 않는다"
    f = vt.fidelity_of("합계 3.30억원 · 100.00% · 26.04", vt.all_text(d) + "\n100% 26.04")   # JSON 3.30 은 3.3 으로 읽힌다
    assert "3.3" not in f["invented"] and "100" not in f["invented"] and not f["missing"], f
    assert vt.fidelity_of("예산 26.04억원", "예산 26.40억원")["invented"] == ["26.4"], "끝자리 0이 아닌 차이는 잡는다"
    assert "\n1\n" not in "\n" + vt.all_text(d) + "\n", "번호 칸은 숫자 대조에서 빠진다"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # 3
        make_pptx(tmp / "a.pptx")
        d = vt.read_deck(tmp / "a.pptx")
        assert [x["title"] for x in d["slides"]] == ["대표 제목입니다", "가장 큰 제목 글자"], d
        assert d["slides"][0]["lines"] == ["첫 항목 내용 정리", "둘째 항목 이어짐"], d["slides"][0]
        assert d["slides"][1]["lines"] == ["머리글 작은 글"], d["slides"][1]
        assert d["extra"] == ["예산 | 480만원"], d["extra"]

        # 4
        (tmp / "m.md").write_text("# 표지\n본문 줄입니다\n---\n두 번째 장 본문\n## 세 번째\n| 표 | 100 |\n|---|---|\n![그림](x.png)\n", encoding="utf-8")
        d = vt.read_deck(tmp / "m.md")
        assert [(x["title"], x["lines"]) for x in d["slides"]] == [("표지", ["본문 줄입니다"]), ("", ["두 번째 장 본문"]), ("세 번째", [])], d
        assert d["extra"] == ["| 표 | 100 |"], d

        # 4b
        def hwpx(path, body):
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("Contents/section0.xml", '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
                           f'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">{body}</hs:sec>')

        def par(*runs):
            return "<hp:p>" + "".join(f"<hp:run>{r}</hp:run>" for r in runs) + "</hp:p>"
        cell = "<hp:tbl><hp:tr><hp:tc><hp:subList>" + par("<hp:t>합계 : 26.04억원</hp:t>") + "</hp:subList></hp:tc></hp:tr></hp:tbl>"
        hwpx(tmp / "r.hwpx", par("<hp:t>□ 개 요 : 본사 승강기 제어반 교체 필요</hp:t>")
             + par("<hp:t>○ 운행 중 정지 신고 지속 </hp:t>", "<hp:t>발생</hp:t>")
             + par("<hp:t>○ 부분 수리로는 근본적 해결이 불가함</hp:t>", cell))
        d = vt.read_deck(tmp / "r.hwpx")
        assert d["slides"][0]["lines"] == ["□ 개 요 : 본사 승강기 제어반 교체 필요", "○ 운행 중 정지 신고 지속 발생",
                                            "○ 부분 수리로는 근본적 해결이 불가함"] and d["extra"] == ["합계 : 26.04억원"], d
        assert "26.04" in vt.all_text(d) and vt.style_parts(d)[1][2] == "부분 수리로는 근본적 해결이 불가함"
        hwpx(tmp / "q.hwpx", par("<hp:t>견적서</hp:t>", cell))
        d = vt.read_deck(tmp / "q.hwpx")
        assert d["slides"][0]["lines"] == ["견적서", "합계 : 26.04억원"] and d["extra"] == [], "본문이 표 안에만 있으면 표 안을 읽는다"

        # 5
        refs = []
        for i in range(3):
            refs.append(tmp / f"ref{i}.md")
            refs[-1].write_text(noun_deck(i), encoding="utf-8")
        voice = tmp / "voice"
        code, r = run("build", *map(str, refs), "--out", str(voice), "--human")
        assert code == 0 and r["status"] == "verified" and r["label"] == "문체 소표본", r
        assert all(x["pass"] for x in r["leave_one_out"]), r
        guide = (voice / "style-guide.md").read_text(encoding="utf-8")
        assert "제목은 명사형으로 끝낸다" in guide and "## 9. 검사 기준" in guide, guide[:400]
        assert (voice / "corpus" / "D-001.md").exists() and (voice / "manifest.jsonl").exists()

        # 6
        (tmp / "new.md").write_text(noun_deck(3), encoding="utf-8")
        code, r = run("gate", "--voice", str(voice), str(tmp / "new.md"))
        assert code == 0 and r["pass"], r
        (tmp / "ai.md").write_text(ai_deck(), encoding="utf-8")
        code, r = run("gate", "--voice", str(voice), str(tmp / "ai.md"))
        bad = {o["metric"] for o in r["out_of_band"]}
        assert code == 3 and not r["style_pass"] and {"title_sentence", "end_polite"} <= bad, r
        assert any(x.startswith("[문체] 서술어로 끝나는 제목 비율") and "1장 「" in x for x in r["rework"]), r["rework"]
        (tmp / "tell.md").write_text(noun_deck(3) + "\n- 이번 장에서는 예산을 살펴보겠습니다\n- 🔥 점검 완료", encoding="utf-8")
        code, r = run("gate", "--voice", str(voice), str(tmp / "tell.md"))
        assert code == 3 and {"[금지] 살펴보겠습니다: 이 표현을 빼고 다시 쓰세요", "[금지] 이모지 발견: 이 표현을 빼고 다시 쓰세요"} <= set(r["rework"]), r

        # 7
        if TEMPLATE.exists():
            code, r = run("build", str(TEMPLATE), "--out", str(tmp / "tv"), "--human")
            assert code == 0 and r["label"] == "문체 시험용(1건)", r
            code, r = run("gate", "--voice", str(tmp / "tv"), str(TEMPLATE))
            assert code == 0 and r["pass"] and r["reference_only"], r
            assert all(t.split(". ", 1)[1] for t in r["titles"]), "예시 덱의 모든 장에 제목이 읽혀야 한다"

            # 8
            d = vt.read_deck(TEMPLATE)
            (tmp / "facts.txt").write_text(vt.all_text(d), encoding="utf-8")
            h = TEMPLATE.read_text(encoding="utf-8")
            m = h.replace('data-count="65.4" data-dec="1">65.4<', 'data-count="66.4" data-dec="1">66.4<', 1).replace('["수작업 (가정)",440,', '["수작업 (가정)",480,', 1)
            assert m != h
            (tmp / "m.html").write_text(m, encoding="utf-8")
            code, r = run("gate", "--facts", str(tmp / "facts.txt"), str(TEMPLATE))
            assert code == 0 and r["fidelity_pass"], r
            code, r = run("gate", "--facts", str(tmp / "facts.txt"), str(tmp / "m.html"))
            assert code == 3 and not r["fidelity_pass"] and {"[숫자] 근거에 없는 값 '66.4': 근거대로 고치거나 [확인 필요]로 표시하세요",
                                                              "[숫자] 근거에 없는 값 '480': 근거대로 고치거나 [확인 필요]로 표시하세요"} <= set(r["rework"]), r
        else:
            print("SKIP 7·8: template/index.html 없음")

        # 9
        try:
            run("build", str(refs[0]), "--out", str(tmp / "nohuman"))
            raise AssertionError("--human 없이 build 가 통과했다")
        except SystemExit:
            pass
        assert not (tmp / "nohuman").exists()
    print("voice_selftest OK")


if __name__ == "__main__":
    main()
