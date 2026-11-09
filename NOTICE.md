# 제3자 구성 요소

| 구성 요소 | 위치 | 출처 · 조건 |
|---|---|---|
| KoPub돋움체 Medium · Bold | `template/assets/fonts/*.ttf`, `scripts/vendor/*.woff2`(일부 글자만 남긴 판) | 한국출판인회의 KoPub 서체. 배포처의 사용 조건을 따른다(서체 자체의 판매 금지) |
| Chart.js 4.4.1 | `scripts/vendor/chart.umd.min.js`, 폴더판은 cdnjs | MIT License, chartjs.org |
| 코쇠 삽화 · 아바타 | `template/assets/illust`, `template/assets/kosoe` | `koscom-kosoe-illustrations` 스킬로 만든 그림. 그 저장소의 조건을 따른다 |
| 코스콤 색·셰브론 모양 | `template/index.html` | 사내 문서 양식을 따라 다시 그린 것. 회사 CI 사용 기준을 따른다 |
| gn-voice 방식 · 장표 규범 | `scripts/voice_tool.py`, `references/voice.md` | [gongnyang/gn-voice](https://github.com/gongnyang/gn-voice) LICENSE Section A(MIT)의 `scripts/verify_style.py`(음슴체 판정·끝맺음 규칙)와 `references/profiles/presentation.md`(제목만 읽기·장당 단어 수·병렬성)를 참고해 다시 썼다. 저자의 코퍼스·지문·장르 팩(Section B)은 쓰지 않는다. 아래 고지를 따른다 |

예시 덱의 조직·사람·고객사·수치(가정·가상 표기)는 시연용입니다. 사내 원본 서식이나 실데이터는 들어 있지 않습니다.

## gn-voice (MIT, Section A)

Copyright (c) 2026 gn-voice authors

Permission is hereby granted, free of charge, to any person obtaining a copy of the software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
