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

## 서식 고르기

1. 에이전트가 원고 설계에 맞춰 장 구성을 한 줄로 추천하고 스튜디오를 **배경으로** 띄운다.
   ```bash
   python scripts/studio.py ./my-deck                  # {"studio": "http://127.0.0.1:<port>/", ...} 출력 후 브라우저 열림
   python scripts/studio.py ./my-deck --wait           # 고를 때까지 기다림(기본 540초)
   ```
2. 사용자가 브라우저에서 고른다.
   - **덱 정보**: 제목(필수) · 상단 바 이름(기본 "코스콤") · 상단 바 영문 꼬리 · 오른쪽 위 꼬리표
   - **장**: 템플릿 23장의 미리보기 카드. 프리셋 — 보고·브리핑 8장(1·2·3·4·7·20·21·23 + 부록 근거·출처) / 짧은 소개 5장(1·2·7·8·23 + 출처) / 제안·공모전 전체
   - **부록**: A 수치 근거 · B 출처 · C 예상 질문 · D 실물 · E 요약 영상 · F 추가 자료
   - 「이 서식으로 만들기」 → `deck/` 생성, `choice.json` 기록
3. `--wait`가 `choice.json`을 출력하면(종료 코드 0) 에이전트가 이어서 장을 쓴다. 종료 코드 2는 아직 안 고른 것이니 다시 `--wait`.

`choice.json`: `title` · `keep`(장 번호) · `labels`(장 이름) · `sides`(남긴 부록) · `brand` · `brand_en` · `pill` · `slides`(장 수) · `created_at` · `previous_deck`(다시 고르기 전 덱을 옮긴 곳, 처음이면 `null`).

`--wait`는 **이 명령을 실행한 뒤에** 기록된 선택만 인정한다(예전 선택으로 바로 끝나지 않게). 서식을 다시 고르면 기존 `deck/`은 지우지 않고 `studio/history/deck-<시각>/`으로 옮긴다.

브라우저를 못 여는 환경이면 `new_deck.py --list`로 장 목록을 채팅에 보여 주고 `new_deck.py ./my-deck/deck --title … --keep … --drop-side …`로 만든다. 같은 함수(`make_deck`)를 쓰므로 결과는 같다(`--brand`·`--brand-en`·`--pill`도 있다).

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
