# 장(슬라이드) 부품

무대는 1440×810. 장 하나 = `<section class="slide">` 하나. 안쪽 여백(위 96 · 오른쪽 72 · 아래 84 · 왼쪽 128)은 상단 바·왼쪽 레일·하단 바 자리다.

## 새 덱에서 먼저 바꿀 것
- `<title>`·`<meta name="description">` — 덱 이름과 한 줄 설명
- 상단 바 `.topbar .brand`(왼쪽 위 이름·영문 꼬리)와 `.pill`(오른쪽 위 꼬리표, 예시는 "ㅋㅋ톤 2026 · 참가 기획서")
- 표지 장(`.slide.cover`)의 제목·한 줄 정의·꼬리표·버튼(`data-side`가 가리키는 부록이 남아 있는지)
- 목차 `.agenda .agrow`와 각 장의 `data-sec`, 맺음 장

## 장의 뼈대
```html
<!-- 07 SOLUTION -->
<section class="slide" data-sec="2" data-label="해법 · 한 줄 정의" data-hook="c7">
  <div class="side-links"><button class="side-link" data-side="basis">근거 보기 ↗</button></div>   <!-- 선택: 부록 바로가기 -->
  <div class="kick a"><span class="no">07</span>SOLUTION</div>
  <h2 class="t a">엔진은 회사가 <em>하나</em>, 팩은 부서마다</h2>
  <p class="lead a">한 문장 설명. <b>핵심 낱말</b>은 굵게.</p>
  <div style="display:grid;grid-template-columns:1fr 420px;gap:44px;margin-top:20px"> … </div>
</section>
```
| 속성 | 뜻 |
|---|---|
| `data-sec` | 왼쪽 레일의 묶음 번호. 목차의 `.agrow` 순서(1부터)와 맞춘다. 0이면 레일에 점을 찍지 않는다(표지·목차·맺음) |
| `data-label` | 하단 바에 보이는 장 이름 — "묶음 · 장 이름" |
| `data-hook` | 장에 들어올 때 실행할 동작 이름(차트는 캔버스만 있으면 자동이라 보통 필요 없음) |
| 클래스 `navy` · `black` | 어두운 장. 삽화가 자동으로 어두운 변형(-d)을 쓴다 |
| 클래스 `cover` | 표지(셰브론 + 코쇠 아바타) |

## 등장 · 움직임
- `.a` — 장에 들어올 때 차례로 올라온다(순서 = 문서 순서). `.a.r` 오른쪽에서, `.a.rv` 서서히 드러남
- `.tilt` + `data-tilt` — 마우스를 따라 살짝 기운다(삽화·카드)
- `.px` + `style="--d:-16"` — 마우스 반대로 움직이는 패럴랙스
- `<span data-count="24000">0</span>` — 숫자가 차오른다(`data-dec="1"` 소수 한 자리). 마우스를 다시 대면 다시 찬다

## 글 부품
| 부품 | 쓰임 | 예 |
|---|---|---|
| `.kick` | 장 번호 + 영문 꼬리표 | `<div class="kick a"><span class="no">03</span>THE PROBLEM</div>` |
| `h2.t` | 제목. 강조는 `<em>` 하나 | |
| `.lead` | 제목 아래 한두 문장 | |
| `.note` | 작은 회색 주석·출처 | `<span class="note">(단위 %)</span>` |
| `.tag` · `.tag.solid` · `.tag.or` | 꼬리표 | `<div class="chip-row"><span class="tag solid">엔진 3종</span></div>` |
| `.kpi` (`.navy`·`.grey`) | 큰 숫자 + 설명 | `<div class="kpi a"><div class="v"><span data-count="251">0</span><small>억 시간</small></div><div class="d">설명 (출처)</div></div>` |
| `.fact` | 이름-설명 줄 목록 | `<div class="fact" style="grid-template-columns:130px 1fr"><b>규칙 반영</b><span>공지·교육 → 팩 수정 1회</span></div>` |
| `.card` | 테두리 상자 | |
| `.rule` | 아이콘 점 + 제목 + 설명(구조도 옆 설명) | `<div class="rule" data-e="ppt"><i></i><div><h4>PPT</h4><p>…</p></div></div>` |
| `.ready` + `.meter` | 준비 상태 막대 | `<div class="ready"><b>PPT 엔진</b><div class="meter"><i style="--v:.9"></i></div><span class="st ok">보유</span></div>` |
| `.pipe .st` | 셰브론 단계 흐름 | |
| `.code` | 코드·설계도 보기 | |
| `.live-strip` + `.badge-live` | 검은 띠 강조 | |

## 그림
```html
<div class="illu tilt" data-tilt style="height:380px;padding:16px">
  <img src="assets/illust/01-engine-pack.webp" alt="그림 설명(무엇을 하는 코쇠인지)">
</div>
```
`assets/illust/<이름>.webp`에 레이어(`layers2/<이름>/`)가 있으면 자동으로 부품별로 움직인다. 없으면 그림 한 장으로 보인다. → `illustrations.md`

## 차트
```html
<div class="chart-box" style="height:300px"><canvas id="c3bar"></canvas></div>
```
캔버스 id = deck-data `charts`의 키. → `data-and-charts.md`

## 부록(사이드 페이지)
본문은 짧게, 근거·출처·질문·실물·영상은 부록으로. 장의 `.side-link`나 왼쪽 레일 아래 「부록」 목록에서 연다(Esc로 닫힘).
```html
<aside class="side-page" id="side-basis" data-side="basis" data-key="A" data-short="수치 근거" data-label="부록 A · 수치 근거" aria-hidden="true">
  <header class="sp-head">
    <div class="kick"><span class="bar"></span>APPENDIX A · 수치 근거</div>
    <h2>연 24,000시간은 이렇게 <em>계산했습니다</em></h2>
    <p class="lead">한두 문장.</p>
    <button class="sp-close" aria-label="닫기">✕</button>
  </header>
  <div class="sp-body">
    <h3>소제목</h3>
    <div class="formula"><div class="fb"><b>500명</b><small>설명</small></div><span class="op">×</span><div class="fb res"><b>24,000</b><small>시간 / 년</small></div></div>
    <table class="map ftab"><thead><tr><th>항목</th><th>값</th></tr></thead><tbody><tr><td>…</td><td>…</td></tr></tbody></table>
  </div>
</aside>
```
- `</section>` 들과 `<!-- /deck-content -->` 사이에 둔다. `data-key`(A, B…)와 `data-short`가 레일의 부록 목록이 된다.
- 그림 모음: `<div class="gal"><button class="shot"><img src="…" data-lb data-cap="설명"><span>1</span></button>…</div>` + 부록 끝에 라이트박스 한 벌
  `<div class="lb"><button class="lb-x">✕</button><button class="lb-p">‹</button><img alt=""><button class="lb-n">›</button><div class="lb-cap"></div></div>` — 방향키로 넘긴다
- 예상 질문: `<details class="q"><summary><span class="qn">Q1</span><span class="qt">질문</span><span class="qa-tag">창의성</span><span class="pm">+</span></summary><div class="ans"><ul><li>답</li></ul><button class="sp-go" data-goto="4">관련 장 5장 보기 →</button></div></details>` (`data-goto`는 0부터 센 장 번호)
- 출처 목록은 필터(`.flt`)로 실측·외부 조사·언론·벤더·공식 문서를 나눠 보여 준다(예시 덱 부록 B)

## 목차와 레일
목차 장의 `.agenda .agrow`가 레일 묶음이 된다. `data-go`는 그 묶음의 첫 장(0부터), `.n`·`.h`·`.d`는 번호·이름·설명.
```html
<div class="agrow" role="button" tabindex="0" data-go="2"><span class="n">01</span><span class="h">문제</span><span class="d">한 줄 설명</span><span class="p">03–06</span><span class="ar">→</span></div>
```

## 편집 모드
화면 오른쪽 위 ✎ 또는 E 키. 장 안의 글자를 바로 고치고, 차트는 「차트 데이터 편집」, 그림은 더블클릭으로 바꾼다. 저장하면 고친 HTML을 내려받는다(초안은 브라우저에 자동 보관). 스튜디오(`scripts/studio.py`)에서 연 덱은 프로젝트의 `deck/index.html`에 바로 저장되고 이전 판은 `studio/history/`에 남는다(`references/studio.md`). 그래서 **글자는 HTML에, 숫자·목록은 deck-data에** 둔다.
