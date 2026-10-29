# koscom_webslide — 코스콤 스타일 웹슬라이드 스킬

말로 원고를 주면 **코스콤 양식(KoPub돋움체 · 오렌지·네이비 · 셰브론)의 움직이는 HTML 웹슬라이드**를 만드는 Claude 스킬입니다.
「ㅋㅋ톤 2026」 참가 기획서 「코쇠오피스」을 만든 엔진을 스킬로 정리했습니다.

- 1440×810 무대 자동 배율, 마우스 반응(기울기·패럴랙스), 단어 단위 줄바꿈
- Chart.js 차트 — 데이터(JSON)만 적으면 그려지고, 편집 모드에서 표로 고친다
- 레이어로 움직이는 코쇠 삽화(배경·몸통·꺾쇠·눈 깜빡임·화살표), 어두운 장 자동 변형
- 부록(사이드 페이지): 수치 근거 · 출처 · 예상 질문 · 실물 · 요약 영상 · 추가 자료
- 편집 모드(E): 글·차트·그림을 브라우저에서 고치고 HTML로 저장
- 요약 모션: 덱 안에서 재생(동영상 파일 없이) + 필요하면 mp4 녹화
- 단일 HTML 파일(그림·서체·차트·모션 내장, 외부 연결 0) — 예시 덱 23장 + 부록 6개 + 111초 모션이 **6.4MB**

## 설치
Claude Code에서:
```
/plugin marketplace add humanist96/koscom_webslide
/plugin install koscom-webslide@koscom-webslide
```
또는 `skills/koscom-webslide` 폴더를 `~/.claude/skills/` (또는 프로젝트의 `.claude/skills/`)에 복사합니다.

## 쓰는 법
"이 원고로 코스콤 웹슬라이드 만들어줘", "기획서를 단일 HTML로 묶어줘(10MB 이하)" 처럼 말하면 스킬이 다음 순서로 만듭니다.

```bash
python skills/koscom-webslide/scripts/new_deck.py ./my-deck --title "제목" --keep 1,2,3,8,19,21
# … index.html의 장·deck-data를 고친다 …
python skills/koscom-webslide/scripts/build_single.py ./my-deck ./my-deck/제목_단일파일.html
node   skills/koscom-webslide/scripts/check_deck.js ./my-deck/제목_단일파일.html --shots ./my-deck/qa
```
자세한 규칙과 부품은 [SKILL.md](skills/koscom-webslide/SKILL.md)와 `references/`.

## 예시
`skills/koscom-webslide/template/index.html` — 「코쇠오피스」 참가 기획서(23장). 브라우저로 바로 열립니다.

## 필요한 것
Python 3.10+ (Pillow · numpy · fontTools[woff2]), Node 18+ + `playwright-core`(점검·녹화, 설치된 Edge/Chrome 사용), ffmpeg(mp4를 만들 때만).

## 알림
조직·사람·고객사·수치 예시는 가상입니다. 서체·삽화·라이브러리의 이용 조건은 [NOTICE.md](NOTICE.md).
