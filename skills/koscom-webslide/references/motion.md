# 요약 모션 — 덱 안에서 재생하는 영상

`video/summary.html`은 1920×1080 무대 위에 장면을 CSS 애니메이션으로 짠 모션그래픽이다. 같은 파일이
- **부록 E**에서 그대로 재생되고(동영상 파일 없이 — 단일 파일 용량↓, 화면을 키워도 선명),
- `render_video.js`로 **mp4**도 된다(프레임마다 멈춰 찍는 결정적 녹화).

## 장면 짜기
```html
<!-- S2 문제 6.8–16.8 -->
<div class="sc" data-t="sIn .5 6.8, sOut .4 16.4 forwards">
  <div class="abs" style="left:140px;top:120px" data-t="up .7 7.1"><div class="kick"><i></i>THE PROBLEM</div><div class="hl">제목 <em>강조</em></div></div>
  <div class="abs card" style="left:990px;top:300px;width:800px;height:380px" data-t="fromR .8 8.1">
    <div class="lay" data-ill="k2-pain-ruler" data-at="8.4" style="left:20px;top:20px;width:760px;height:340px"></div>
  </div>
</div>
```
- `data-t="이름 길이 시작 [반복] [이징] [채우기]"` — 모든 시각은 **영상 처음부터의 절대 초**. 쉼표로 여러 개
- 장면 전환: `.sc`에 `sIn`(들어옴)·`sOut`(나감). 장면 사이 셰브론 `.sweep`
- 삽화: `.lay[data-ill][data-at]` — 레이어가 그 시각부터 순서대로 나타난다. 어두운 장면은 `data-dark`
- 자막: `#cap` 안에 장면마다 한 줄(`<b>꼬리표</b>설명`)
- 진행 막대 `#prog`의 길이와 재생기 `motion.dur`(스크립트의 `DUR`)를 전체 길이에 맞춘다
- 실제 화면을 넣을 때는 `.frame`(브라우저 틀) 안에 그림 — 예시의 '화면 시안' 장면

## 재생기
`summary.html`은 `window.motion`(`seek` · `play` · `pause` · `time` · `dur`)을 내놓는다. 기획서 부록 E의 재생기는 이것을 iframe으로 불러 재생·멈춤·막대 이동·장면 바로가기(`#vchap button[data-t]`)·Space·전체 화면을 붙인다. 장면 버튼의 시각을 장면 시작과 맞춘다.

## mp4 만들기
```bash
python -m http.server 8765 --directory ./my-deck        # 다른 창에서
DECK=./my-deck node scripts/render_video.js qa           # 장면 점검 정지 화면 → video/qa/
DECK=./my-deck node scripts/render_video.js video        # → assets/video/summary.mp4 (crf 24)
```
- 원본 프레임에서 한 번만 압축한다(만든 mp4를 다시 압축하면 손실이 겹친다)
- 녹화 중에는 같은 PC에서 무거운 일을 하지 않는다

## 주의
- 무대는 왼쪽 위 기준 절대 위치로 줄인다(`fit()`). 가운데 정렬 레이아웃에 맡기면 1920이 아닌 창에서 밀려 보인다
- 재생기의 `play()`는 이미 끝난 애니메이션을 다시 재생하지 않는다(다시 감기는 것을 막음)
