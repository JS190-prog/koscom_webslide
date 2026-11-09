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
- **스튜디오**([deck-design-pack](https://github.com/JS190-prog/deck-design-pack) 방식): 작업 전에 브라우저에서 장 미리보기를 보고 서식(장·부록·제목·상단 바)을 고르고, 만든 덱을 브라우저에서 고치면 프로젝트에 바로 저장되며(이전 판 백업), 검사·점검을 통과한 판만 `exports/<제목>_verN.html` 최종본으로 남긴다
- **문체 맞추기**([gn-voice](https://github.com/gongnyang/gn-voice) 방식): 예전 발표자료·보고서(.pptx·웹슬라이드·.hwpx·.md) 2~3건에서 제목 꼴·끝맺음·장당 분량·표기·자주 쓴 표현을 재서 `style-guide.md`로 정리하고, 그 문체로 쓴 덱을 스크립트가 검사한다(문체 밴드 · AI 상투구 · 근거에 없는 숫자 · 제목만 읽기)

## 설치
Claude Code에서:
```
/plugin marketplace add JS190-prog/koscom_webslide
/plugin install koscom-webslide@koscom-webslide
```
또는 `skills/koscom-webslide` 폴더를 `~/.claude/skills/` (또는 프로젝트의 `.claude/skills/`)에 복사합니다.
원 저장소 [humanist96/koscom_webslide](https://github.com/humanist96/koscom_webslide)에는 문체 맞추기 기능이 없습니다.

## 쓰는 법
"이 원고로 코스콤 웹슬라이드 만들어줘", "기획서를 단일 HTML로 묶어줘(10MB 이하)" 처럼 말하면 스킬이 다음 순서로 만듭니다.

```bash
python skills/koscom-webslide/scripts/studio.py ./my-deck     # 브라우저에서 서식을 고른다 → my-deck/deck/
# … 에이전트가 deck/index.html의 장·deck-data를 쓴다. 스튜디오의 「덱 열고 고치기」로 직접 고쳐 저장할 수 있다 …
python skills/koscom-webslide/scripts/finalize.py ./my-deck   # 검사 → 단일 파일 → 점검 통과 시 my-deck/exports/제목_ver1.html
```
브라우저 없이 만들 때는 `new_deck.py ./my-deck/deck --title "제목" --keep 1,2,3,8,19,21`. 스튜디오·최종본은 [references/studio.md](skills/koscom-webslide/references/studio.md), 자세한 규칙과 부품은 [SKILL.md](skills/koscom-webslide/SKILL.md)와 `references/`.

### 문체를 맞출 때
"이 발표자료들 문체로 웹슬라이드 만들어줘", "우리 팀 장표 문체 분석해줘"처럼 대표 자료와 함께 말하면 먼저 문체를 분석하고, 다 쓴 덱을 검사합니다.

```bash
python skills/koscom-webslide/scripts/voice_tool.py build 예전발표1.pptx 예전발표2.html --out ./my-deck/voice --human
# … voice/style-guide.md 대로 장을 쓴다 …
python skills/koscom-webslide/scripts/voice_tool.py gate --voice ./my-deck/voice --facts ./my-deck/facts/facts.txt ./my-deck/deck/index.html
```
`my-deck/voice`·`my-deck/facts`가 있으면 `finalize.py`가 최종본을 만들 때 같은 검사를 알아서 돌립니다.
`gate`가 불합격이면 고칠 항목(어느 장의 제목·분량·끝맺음·숫자인지)을 한 줄씩 돌려줍니다. 자세한 절차는 [references/voice.md](skills/koscom-webslide/references/voice.md).

## 예시
`skills/koscom-webslide/template/index.html` — 「코쇠오피스」 참가 기획서(23장). 브라우저로 바로 열립니다.

## 필요한 것
Python 3.10+ (Pillow · numpy · fontTools[woff2]), Node 18+ + `playwright-core`(점검·녹화, 설치된 Edge/Chrome 사용), ffmpeg(mp4를 만들 때만). 문체 도구는 Python 표준 라이브러리만 씁니다.

## 알림
조직·사람·고객사·수치 예시는 가상입니다. 서체·삽화·라이브러리의 이용 조건은 [NOTICE.md](NOTICE.md).
