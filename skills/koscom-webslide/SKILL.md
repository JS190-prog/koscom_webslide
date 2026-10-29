---
name: koscom-webslide
description: 코스콤 스타일(KoPub돋움체 · 오렌지·네이비 · 셰브론)의 움직이는 HTML 웹슬라이드를 만든다. 마우스에 반응하는 16:9 덱, Chart.js 차트, 레이어로 움직이는 코쇠 삽화, 부록(사이드 페이지), 편집 모드, 요약 모션 영상, 외부 연결 없이 열리는 단일 HTML 파일(10MB 이하)까지. "웹슬라이드 만들어줘", "HTML 발표자료", "기획서를 웹페이지 슬라이드로", "링크로 공유할 브리핑", "반응형 슬라이드", "단일 HTML로 묶어줘", "요약 영상까지", 공모전·사내 기획서·제안서·교육 자료를 브라우저용 슬라이드로 만들 때 사용한다. .pptx가 필요하면 PPT 스킬, 결재용 .hwp가 필요하면 한글 스킬을 쓴다.
---

# 코스콤 웹슬라이드 (koscom-webslide)

「ㅋㅋ톤 2026」 참가 기획서 「코쇠 문서팩」을 만든 엔진이다. 그 기획서가 `template/` 에 통째로 들어 있고, 새 덱은 이것을 복사해 내용만 바꿔 만든다. 엔진(CSS·JS)은 장이나 부록을 빼도 돌아가게 만들어 두었다.

## 언제 쓰나 / 안 쓰나
- 쓴다: 링크로 공유하는 기획서·제안서·브리핑·교육 자료, 심사·발표용 인터랙티브 덱, 오프라인 단일 파일 제출, 요약 모션 영상
- 안 쓴다: 고쳐 쓸 .pptx가 필요할 때(PPT 스킬), 결재 올릴 .hwp가 필요할 때(한글 스킬), 표만 있는 한 쪽 문서

## 작업 순서

1. **요구 확인** — 분량(장 수), 읽는 사람, 제출 형식(폴더/단일 파일, 용량 제한), 오프라인 여부, 요약 영상 필요 여부. 숫자·출처 자료를 받는다.
2. **원고 설계** — 장마다 메시지 한 줄(제목), 근거(숫자·그림), 출처. 숫자는 **실측 / 외부 조사 / 가정**으로 나누고 가정은 가정이라고 쓴다. 장 구성은 `references/storyline.md`.
3. **새 덱 만들기**
   ```bash
   python scripts/new_deck.py --list                      # 템플릿의 장·부록 목록
   python scripts/new_deck.py ./my-deck --title "제목" --keep 1,2,3,8,19,21 --drop-side gallery,live
   ```
4. **장 쓰기** — `index.html`의 `<section class="slide">`를 고치거나 복제한다. 쓸 수 있는 부품과 규칙은 `references/components.md`. 목차(`.agenda .agrow`)와 각 장의 `data-sec`이 왼쪽 레일을 만든다.
5. **데이터·차트** — 숫자와 표는 맨 아래 `<script id="deck-data">`(JSON)에 둔다. 차트는 `charts.<캔버스 id>`에 `kind`(hbar·vbar·doughnut·line)만 주면 그려지고, 편집 모드의 「차트 데이터 편집」으로 고칠 수 있다. `references/data-and-charts.md`.
6. **삽화** — 코쇠 삽화는 `koscom-kosoe-illustrations` 스킬로 그리고(16:9 흰 배경 webp), `scripts/cut_layers.py`로 레이어(배경·코쇠·화살표/라벨)를 잘라 움직이게 한다. 어두운 장(`.navy`·`.black`)은 자동으로 `-d` 변형을 쓴다. `references/illustrations.md`.
7. **부록(사이드 페이지)** — 수치 근거·출처·예상 질문·실물·요약 영상·추가 자료. 본문은 짧게, 근거는 부록으로. `references/components.md#부록`.
8. **요약 모션(선택)** — `video/summary.html`의 장면을 바꾸면 부록 E에서 그대로 재생된다(동영상 파일 없이). mp4가 따로 필요하면 `scripts/render_video.js`. `references/motion.md`.
9. **단일 파일 · 점검**
   ```bash
   python scripts/build_single.py ./my-deck ./my-deck/제목_단일파일.html      # 9.5MB 넘으면 경고
   node scripts/check_deck.js ./my-deck/제목_단일파일.html --shots ./my-deck/qa
   ```
   점검 결과가 ✅(외부 요청 0 · 스크립트 오류 0 · 용량 이내)일 때만 전달한다. 화면 그림(`--shots`)을 직접 보고 넘침·겹침을 고친다.

## 꼭 지키는 규칙
- **서체**: KoPub돋움체 Medium(본문)·Bold(제목). 다른 서체를 섞지 않는다.
- **줄바꿈**: 단어 단위(`word-break:keep-all`). 단어 중간에서 끊기면 문장을 고치거나 `<br>`로 끊는다.
- **색**: 오렌지 `#ee6d1d`(강조 하나), 네이비 `#00338d`·`#1f4b9b`, 잉크 `#2b2b2e`, 회색 계열. 한 장에 강조색은 오렌지 하나. 제목 강조는 `<em>`.
- **무대**: 1440×810 고정 좌표에 자동 배율. 글자는 본문 15px 이상, 제목 40~52px. 장 하나에 메시지 하나.
- **편집 모드 호환**: 데이터로 그리는 글자는 deck-data에 두고 `data-bind`로 묶는다. 장 안의 글은 편집 모드(E)에서 바로 고칠 수 있다.
- **숫자 표기**: 출처를 부록 B에, 성격(실측/외부 조사/벤더 발표/가정)을 함께. 바뀔 수 있는 개수는 'n종'처럼 고정하지 않는다.
- **가상 데이터**: 사람·고객사·수치는 가명·가상으로. 사내 원본 서식이나 실데이터를 넣지 않는다.
- **용량**: 단일 파일은 mp4를 넣지 않고 모션 원본으로 재생한다. 넘치면 `--referenced-only` → 그림 해상도(1600px)·webp 품질(82) → 부록 그림 수 순으로 줄인다.

## 파일
| 경로 | 내용 |
|---|---|
| `template/index.html` | 예시 덱 겸 엔진(21장 + 부록 A~F). CSS·JS·deck-data 한 파일 |
| `template/video/summary.html` | 요약 모션 원본(111초, 장면별 CSS 애니메이션) |
| `template/assets/` | 서체(ttf), 코쇠 삽화와 레이어(`illust/layers2` + manifest), 코쇠 아바타, 예시 그림 |
| `scripts/new_deck.py` | 템플릿 복사, 장·부록 고르기 |
| `scripts/build_single.py` | 단일 HTML 파일(그림·서체·Chart.js·모션 내장) |
| `scripts/check_deck.js` | 외부 연결을 막고 전 장·부록·모션·편집 모드 점검 |
| `scripts/subset_fonts.py` | 단일 파일용 서체 다시 줄이기(새 글자를 썼을 때) |
| `scripts/cut_layers.py` | 삽화 → 움직이는 레이어 |
| `scripts/render_video.js` | 요약 모션 → mp4(결정적 프레임 녹화 + ffmpeg) |
| `references/` | 부품·데이터·삽화·모션·원고 구성 안내 |

## 필요한 것
Python 3.10+ (Pillow, numpy, fontTools[woff2]), Node 18+ 와 `playwright-core`(점검·녹화, 설치된 Edge/Chrome 사용), ffmpeg(mp4를 만들 때만).
