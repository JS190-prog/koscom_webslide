# 원고 원본(템플릿) — 여러 개 두기와 새로 만들기

덱은 **원고 원본**(장 모양을 모아 둔 예시 덱)에서 장을 골라 만든다. 스튜디오의 「원고 고르기」와 `new_deck.py --template`이 원본을 고른다.

| id | 위치 | 이름 | 움직임 |
|---|---|---|---|
| `kosoe` | `template/` | 코쇠오피스 기획서 | 정적 장 넘김 + 마우스 반응, 코쇠 삽화 |
| `motion` | `templates/motion/` | 키네틱 모션 브리핑 | 장마다 모션 기법 하나(마스크 리빌·키네틱 타이포·숫자·입자·와이프…) — [awesome-ai-motion](https://github.com/gongnyang/awesome-ai-motion) |
| `scrolline` | `templates/scrolline/` | 스크롤 타임라인 | 휠로 이어지는 연속 타임라인, 앞 장의 요소가 다음 장으로 넘어감 — [awesome-html-scrolline-deck](https://github.com/gongnyang/awesome-html-scrolline-deck) |
| `three` | `templates/three/` | 3D 구조 브리핑 | three.js 3D 무대(턴테이블·분해도·입체 막대·네트워크), 장마다 카메라 이동 |

```bash
python scripts/new_deck.py --list --template three          # 원본 목록과 그 원본의 장·부록
python scripts/new_deck.py ./my-deck/deck --template motion --title "제목" --keep 1,2,5,9
python scripts/studio.py --thumbs --template motion         # 원본을 고친 뒤 스튜디오 미리보기 다시 만들기
```

## 원본 하나의 구성

```
templates/<id>/
  index.html       엔진 + 예시 장(표본 내용) + 부록 + deck-data
  template.json    {"name", "desc", "look", "presets": [{"name", "keep": [장 번호], "sides": [부록 키]}]}
  assets/          그 원본만 쓰는 그림·라이브러리(assets/vendor/*.js). 서체는 넣지 않는다(template/assets/fonts 를 같이 씀)
```

`new_deck.py`가 원본을 복사할 때 `template.json`은 빼고, `assets/fonts`가 없으면 기본 원본에서 복사한다. `build_single.py`는 `<script src="assets/….js"></script>`를 본문으로 넣는다(외부 연결 0).

## 계약 (새 원본을 만들 때)

1. **엔진은 그대로 복사한다.** `template/index.html`을 통째로 복사한 뒤 바꾸는 곳은 다음뿐이다.
   - `<title>`, `<meta name="description">`, 상단 바(`.brand` 이름·영문 꼬리), 꼬리표(`.pill`)
   - 장 영역: 첫 `<section class="slide`(앞의 `  <!-- NN … -->` 주석 줄 포함)부터 `<!-- /deck-content -->` 바로 앞까지(부록 `aside.side-page` 포함)
   - `<script type="application/json" id="deck-data">`(차트 등 데이터), `id="illu-layers"`(코쇠 삽화를 안 쓰면 `{}`)
   - `</head>` 바로 앞에 원본 전용 `<style>` 한 블록, 엔진 `<script>`와 맨 끝 「발표자 보기(S)·대본(N)」 블록 사이에 원본 전용 `<script>` 한 블록(움직임 층)
   - 엔진 CSS·JS와 대본 CSS(엔진 CSS 끝)·발표자 보기 블록(`</body>` 바로 앞)은 고치지 않는다. 필요한 고리가 없으면 `template/index.html`에 일반 고리로 넣고 네 원본에 똑같이 옮긴다(`studio_selftest.py`가 같은지 확인, `references/presenter.md`)
   - 엔진 뒤에는 `<script>`만 둔다. 엔진이 시작할 때 찍는 저장 원본에는 그 뒤가 아직 없어서, 문서를 다 읽은 뒤 엔진 뒤의 `<script>`를 덧붙인다(다른 요소를 두면 편집 저장본에서 빠진다)
2. **장 마크업** — 장마다 2칸 들여쓴 `  <section class="slide …" data-sec="N" data-label="구분 · 이름">` … `  </section>`, 앞에 `  <!-- NN 이름 -->` 주석 한 줄을 둘 수 있다(`new_deck.SEC`가 이 모양으로 장을 자른다). `data-label`은 스튜디오 카드 이름이 된다. 대본은 장 끝(`</section>` 바로 앞)의 `<aside class="notes">`. 장과 장 사이는 **빈 줄 하나**만 둔다(주석 외의 글 없이, 빈 줄이 없으면 장을 못 나눈다). 2장 정도에 목차(`.agenda .agrow`)를 두면 왼쪽 레일이 생긴다.
3. **부록** — `<aside class="side-page" id="side-<키>" data-side="<키>" data-key="A" data-short="짧은 이름" data-label="부록 A · 이름">`. 최소 `basis`(수치 근거 표)·`sources`(출처) 두 개.
4. **움직임 층** — `document.addEventListener('deck:slide', e => …)`로 장 바뀜(`e.detail = {i, el, prev}`)을, `deck:edit`(`e.detail.on`)로 편집 모드 켜고 끔을 받고 `window.deck`(`go(i)`, `index`, `editing`, `side`, `slides`, `N`)을 쓴다. 첫 장 이벤트는 서체를 읽은 뒤 나오므로 엔진 뒤의 스크립트에서 바로 등록하면 받는다. 엔진은 움직임 줄이기에서 글 등장·장 페이드·차트 애니메이션을 끄고, 단추에 초점이 있으면 Enter·Space로 장을 넘기지 않는다. 차트는 `kind`를 적으면 캔버스 id와 관계없이 범용 차트로 그린다.
   - **휠을 직접 쓰는 원본**(스크롤 타임라인)은 `<body data-nav="scroll">`로 엔진의 휠 장 넘김을 끈다. 키(→ ← Home End)·버튼·`deck.go()`는 그대로 정지점 이동이어야 한다.
   - `check_deck.js`는 → 키로 한 장씩 넘기고 1.6초 뒤 화면을 찍는다. **정지점마다 1.5초 안에 최종 상태**가 되어야 한다.
   - `prefers-reduced-motion: reduce`이면 움직임 없이 최종 상태를 바로 보인다(투명도 0으로 남는 요소 없게).
5. **편집 모드(E)와 저장** — 저장은 엔진 시작 때 찍어 둔 원본 HTML(+ 다 읽은 뒤 덧붙인 엔진 뒤 `<script>`)에 고친 글 요소만 덮어쓴다. 그래서
   - 움직임 층은 **글을 가진 요소 안에 DOM을 넣지 않는다**(글자를 span으로 쪼개기 금지). 요소 통째로 transform·clip-path·opacity로 움직이거나, 장식용 복제는 `data-gen` 표시 + `aria-hidden`으로 따로 둔다(`[data-gen]` 안은 편집·저장 대상에서 빠진다).
   - `deck.editing`이 참이면 움직임을 멈추고 글이 제자리에서 눌리고 고쳐지게 둔다(가리는 층에 `pointer-events:none`).
   - 숫자·목록은 deck-data에 두고 차트는 `charts.<캔버스 id>`에 `kind`(hbar·vbar·doughnut·line)·`cols`·`types`·`rows`를 주면 엔진이 그리고 「차트 데이터 편집」이 붙는다.
6. **규칙** — 서체 KoPub돋움체(엔진), 색은 오렌지 `#ee6d1d`(장마다 강조 하나)·네이비 `#00338d`/`#1f4b9b`·잉크 `#2b2b2e`·회색 계열 안에서 원본마다 다른 인상. 단어 단위 줄바꿈, 본문 15px 이상, 제목 40~52px, 장 하나에 메시지 하나. 예시 내용은 모두 가상(「표본」 표기), 실제 회사·사람·수치를 넣지 않는다.
7. **점검** — `python scripts/build_single.py templates/<id> out.html` 후 `node scripts/check_deck.js out.html --shots qa`가 ✅(외부 요청 0 · 스크립트 오류 0 · 발표자 보기 넘김 동기화)여야 하고, 장마다 화면 그림을 직접 보고 넘침·겹침을 고친다. WebGL을 못 쓰는 환경에서는 정지 그림으로 물러나고 오류를 내지 않는다.
8. **미리보기** — 원본을 고쳤으면 `python scripts/studio.py --thumbs --template <id>`.
