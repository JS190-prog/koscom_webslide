# 제3자 구성 요소

| 구성 요소 | 위치 | 출처 · 조건 |
|---|---|---|
| KoPub돋움체 Medium · Bold | `template/assets/fonts/*.ttf`, `scripts/vendor/*.woff2`(일부 글자만 남긴 판) | 한국출판인회의 KoPub 서체. 배포처의 사용 조건을 따른다(서체 자체의 판매 금지) |
| Chart.js 4.4.1 | `scripts/vendor/chart.umd.min.js`, 폴더판은 cdnjs | MIT License, chartjs.org |
| 코쇠 삽화 · 아바타 | `template/assets/illust`, `template/assets/kosoe` | `koscom-kosoe-illustrations` 스킬로 만든 그림. 그 저장소의 조건을 따른다 |
| 코스콤 색·셰브론 모양 | `template/index.html` | 사내 문서 양식을 따라 다시 그린 것. 회사 CI 사용 기준을 따른다 |
| gn-voice 방식 · 장표 규범 | `scripts/voice_tool.py`, `references/voice.md` | [gongnyang/gn-voice](https://github.com/gongnyang/gn-voice) LICENSE Section A(MIT)의 `scripts/verify_style.py`(음슴체 판정·끝맺음 규칙)와 `references/profiles/presentation.md`(제목만 읽기·장당 단어 수·병렬성)를 참고해 다시 썼다. 저자의 코퍼스·지문·장르 팩(Section B)은 쓰지 않는다. 아래 고지를 따른다 |

| 모션 기법 · 덱 모션 원칙 | `templates/motion/` | [gongnyang/awesome-ai-motion](https://github.com/gongnyang/awesome-ai-motion)(MIT, © 2026 gongnyang)의 효과 카드·`routes/덱과사이트.md`의 정의·기본 파라미터를 참고해 바닐라 JS·CSS로 다시 구현했다. 클립·코드는 복사하지 않았다 |
| 스크롤 연속 타임라인 · handoff move | `templates/scrolline/` | [gongnyang/awesome-html-scrolline-deck](https://github.com/gongnyang/awesome-html-scrolline-deck)(MIT, © 2026 gongnyang)의 개념(무대 하나·연속 timeline·link move·컨셉 문법)을 참고해 바닐라 JS로 다시 구현했다. GSAP·Lenis는 쓰지 않는다 |
| 발표자 보기 방식 | 원고 원본마다 「발표자 보기(S)·대본(N)」 블록, `references/presenter.md` | [lewislulu/html-ppt-skill](https://github.com/lewislulu/html-ppt-skill)(MIT)의 발표자 모드 방식(장마다 `aside.notes`, `S`로 새 창, 같은 파일을 `?preview`로 띄운 미리보기를 `postMessage`로 넘김)과 대본 쓰기 원칙을 참고해 새로 구현했다. 코드는 복사하지 않았다 |
| three.js r158 | `templates/three/assets/vendor/three.min.js` | MIT License, © 2010-2023 three.js authors(`three.LICENSE.txt`). 3D 장면은 위 두 저장소의 3D 효과 카드·`launch-orbit-note` 장면을 참고해 새로 만들었다 |

예시 덱의 조직·사람·고객사·수치(가정·가상 표기)는 시연용입니다. 사내 원본 서식이나 실데이터는 들어 있지 않습니다.

## gn-voice (MIT, Section A)

Copyright (c) 2026 gn-voice authors

Permission is hereby granted, free of charge, to any person obtaining a copy of the software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
