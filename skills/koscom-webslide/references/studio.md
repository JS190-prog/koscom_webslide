# 스튜디오와 최종본

[deck-design-pack](https://github.com/JS190-prog/deck-design-pack)의 확인 페이지 흐름(추천 → 브라우저에서 고름 → 결과 파일을 에이전트가 읽음 → 고친 뒤 `_verN`으로 내보냄)을 웹슬라이드에 맞게 줄였다. Python 표준 라이브러리만 쓴다.

## 프로젝트 폴더

```
my-deck/
  facts/            숫자·이름 근거(txt·md·hwpx 등). 최종본 검사가 모두 읽는다
  voice/            문체 폴더(voice_tool.py build --out). 있으면 최종본 검사에 쓴다
  deck/             작업본(폴더판). 에이전트가 쓰고, 사용자가 스튜디오에서 고쳐 저장한다
  studio/
    choice.json     고른 서식(아래)
    server.json     떠 있는 스튜디오 주소·pid
    history/        덮어쓰기 전 백업 — deck-<시각>/(서식을 다시 골랐을 때), index-<시각>.html(편집 저장마다)
    build.html      최종본 만들기 중간 산출물(점검에 떨어지면 여기 남는다)
  exports/
    <제목>_ver1.html · <제목>_ver1.json   최종본과 검사 기록. 판마다 번호가 올라가고 이전 판은 지우지 않는다
```

## 서식 고르기 — AI가 채우고 사람은 확인

1. 에이전트가 근거 자료로 원고 설계를 하고 `studio/recommendations.json`을 쓴다(아래 형식). 덱 정보와 **원고 후보 2~3개**를 넣는다. 후보는 분량(요약·보고·상세)이나 원고 원본(`references/templates.md` — 코쇠오피스·키네틱 모션·스크롤 타임라인·3D)이 다르게 짠다.
2. 스튜디오를 **배경으로** 띄우고 기다린다.
   ```bash
   python scripts/studio.py ./my-deck                  # {"studio": url, "recommend": "원고 후보 3개, 추천 …"} 출력 후 브라우저 열림
   python scripts/studio.py ./my-deck --wait           # 고를 때까지 기다림(기본 540초). 종료 코드 2면 다시
   ```
   `recommend`가 오류 문장이면 추천 파일을 고친 뒤 다시 띄운다(화면에도 오류가 뜨고 원고 원본에서 직접 고르기로 바뀐다).
3. 사용자가 브라우저에서 확인한다.
   - **덱 정보**: AI가 채운 칸(연한 주황). 고친 칸은 파란 줄로 표시된다
   - **원고 고르기**: 후보 카드(★ 추천, 장 수·부록 수·원고 원본 이름). 고른 원고의 장마다 모양 미리보기 + 제목·메시지 칸(고칠 수 있음) + 넣기 칸(끄면 그 장을 뺌)
   - **부록**: 원고가 고른 부록이 켜져 있다
   - 「이 서식으로 만들기」 → 원고 순서대로 `deck/` 생성, `choice.json` 기록
4. `--wait`가 `choice.json`을 출력하면 에이전트가 `outline`대로 장을 쓰고 `changes`를 따른다.

추천 파일이 없으면 예전처럼 원고 원본 탭(코쇠오피스·키네틱 모션·…)에서 장 미리보기 카드를 직접 고른다(원본마다 묶음 버튼이 있다).

### recommendations.json

```json
{
 "deck": {"title": "덱 제목", "brand": "상단 바 이름", "brand_en": "영문 꼬리", "pill": "꼬리표"},
 "basis": "근거 한 줄(화면 맨 위에 보인다)",
 "recommend": "report8",
 "drafts": [
  {"id": "report8", "name": "결재 보고 8장", "why": "누구에게·왜", "template": "kosoe", "sides": ["basis", "sources"],
   "slides": [{"layout": 1, "title": "장 제목", "msg": "이 장에서 말할 것 한 줄"}, …]}
 ]
}
```
- `template`: 원고 원본 id(생략하면 `kosoe`). `layout`: 그 원본의 장 번호(`new_deck.py --list --template <id>`), 한 원고 안에서 겹치지 않게. 장은 적은 순서대로 만들어진다.
- 각 장은 `layout` 장의 구조(부품·배치·움직임)를 바탕으로 내용만 바꾼다 — 사용자가 그 모양을 보고 골랐다.

`choice.json`: `template` · `title` · `keep`(장 번호, 원고 순서) · `labels`(장 이름) · `sides`(남긴 부록) · `brand` · `brand_en` · `pill` · `slides`(장 수) · `created_at` · `previous_deck`(다시 고르기 전 덱을 옮긴 곳, 처음이면 `null`). 원고로 만들었으면 `draft`(고른 후보 id) · `outline`(확정한 장 `[{layout, title, msg}]`) · `changes`(사람이 추천에서 고친 곳: 덱 정보·원고·장 제목·메시지·뺀 장).

`--wait`는 **이 명령을 실행한 뒤에** 기록된 선택만 인정한다(예전 선택으로 바로 끝나지 않게). 서식을 다시 고르면 기존 `deck/`은 지우지 않고 `studio/history/deck-<시각>/`으로 옮긴다.

브라우저를 못 여는 환경이면 원고 후보를 채팅으로 보여 주고 `new_deck.py ./my-deck/deck --template <id> --title … --keep … --drop-side …`로 만든다. 같은 함수(`make_deck`)를 쓰므로 결과는 같다(`--brand`·`--brand-en`·`--pill`도 있다).

## 고치기

- 스튜디오의 「덱 열고 고치기」는 `http://127.0.0.1:<port>/deck/index.html`로 연다. 편집 모드(E 또는 ✎)에서 글·차트(「차트 데이터 편집」)·그림(더블클릭)을 고치고 「HTML 저장」을 누르면 `deck/index.html`에 바로 쓴다. 쓰기 전 판은 `studio/history/index-<시각>.html`.
- 덱을 파일(`file://`)로 열었거나 스튜디오가 꺼져 있거나 최종본(`/exports/`)을 열었으면 예전처럼 HTML을 내려받는다(저장 위치 선택 또는 다운로드). 작업본에는 쓰지 않는다.
- 에이전트는 사용자가 고쳤다고 하면 `deck/index.html`을 **다시 읽고** 이어서 고친다. 사용자 수정을 덮어썼으면 `studio/history/`에서 되살린다.
- 저장은 덱 HTML(`<section class="slide` 와 `id="deck-data"`가 있는 것)만 받는다.

## 최종본

```bash
python scripts/finalize.py ./my-deck [--facts 파일 …] [--voice 폴더] [--mode create|rewrite] [--skip-check]
```

| 단계 | 하는 일 | 떨어지면 |
|---|---|---|
| 1 검사 | `voice_tool.py gate` — 문체 밴드(문체 폴더가 있을 때) · AI 상투구 · 근거에 없는 숫자·이름 | 종료 3, `rework` 항목 |
| 2 단일 파일 | `build_single.py deck/ → studio/build.html` | 종료 3, 오류 |
| 3 점검 | `check_deck.js` — 외부 요청 0 · 스크립트 오류 0 · 용량 이내 | 종료 3, 점검 결과(`studio/build.html`은 남김) |
| 4 번호 | `exports/<제목>_verN.html` + `.json`(판 번호·만든 시각·덱 sha256·용량·검사 요약·점검 결과) | — |

- 마지막 줄에 JSON 한 줄을 찍는다. 스튜디오의 「최종본 만들기」는 같은 스크립트를 돌리고 결과(합격·rework)를 화면에 보여 준다.
- 떨어지면 번호를 쓰지 않는다. 그래서 `ver` 번호가 붙은 파일은 모두 검사·점검을 통과한 판이다.
- `--skip-check`로 만든 판은 기록에 `"skipped": true`가 남는다. 사용자에게 점검 없이 만들었다고 알린다.
- 용량이 넘치면 `build_single.py --referenced-only` 등을 직접 돌려 원인을 찾는다(SKILL.md 「용량」).

## 보안

- `127.0.0.1`에만 연다. `Host`가 `127.0.0.1:<port>`·`localhost:<port>`가 아니면 403(DNS 리바인딩 차단).
- 바꾸는 요청(`/api/create`·`/api/save`·`/api/finalize`)은 실행마다 새로 만드는 토큰(`X-Studio-Token`)이 맞아야 받는다. 토큰은 같은 출처 페이지만 읽을 수 있어 다른 사이트가 덱을 덮어쓰지 못한다.
- `/ui/`·`/deck/`·`/exports/` 밖의 파일은 주지 않는다(`../` 차단). 요청 본문은 40MB까지.

## 문제 해결

| 증상 | 할 일 |
|---|---|
| 브라우저가 안 열림 | 출력된 `studio` 주소를 직접 연다. 원격 세션이면 채팅으로 고른다 |
| 「최종본 만들기」가 playwright-core를 못 찾음 | 스튜디오를 띄울 때 `PLAYWRIGHT_CORE=<playwright-core 경로>`를 준다 |
| 「HTML 저장」이 작업본 대신 내려받기로 됨 | 스튜디오가 꺼졌거나 다시 띄워 주소(포트)가 바뀌었다. 스튜디오를 띄우고 새 주소에서 덱을 열어 다시 저장한다(내려받은 파일로 `deck/index.html`을 바꿔도 된다) |
| 장 미리보기가 템플릿과 다름 | 템플릿을 고친 뒤 `python scripts/studio.py --thumbs`(node·playwright-core·Pillow) |

스튜디오·최종본을 고쳤으면 `python scripts/studio_selftest.py`를 돌린다.
