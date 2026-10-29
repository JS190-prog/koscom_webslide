# 삽화 — 코쇠 그림을 레이어로 움직이기

## 1. 그리기
`koscom-kosoe-illustrations` 스킬로 그린다. 16:9 흰 배경, 코스콤 오렌지·진회색 절제, 코쇠가 핵심 동작을 맡는 개념 삽화. 장의 메시지를 한 장면으로(예: "공통 엔진에 부서 팩 카트리지를 끼우는 코쇠"). 프롬프트는 `template/assets/illust/prompts/` 참고.

webp(가로 1600px 안팎, 품질 82)로 `assets/illust/<이름>.webp`에 둔다. 이름은 영문 소문자·숫자·하이픈.

## 2. 레이어로 자르기
```bash
python scripts/cut_layers.py <덱>/assets/illust <덱>/assets/illust/layers2 <덱>/assets/illust/layers2/manifest.json
```
- 배경(선·종이) / 코쇠 몸통(진회색 면 + 외곽선 + 눈) / 머리 꺾쇠 / 눈꺼풀(깜빡임) / 오렌지·파랑·빨강 덩어리(화살표 하나, 라벨 하나)를 따로 자른다
- 어두운 장용 `-d` 변형도 함께 만든다(종이는 투명, 검은 선은 밝은 선, 파랑은 하늘색)
- 코쇠 몸 동작은 스크립트의 `BODY_MOTION`(bTilt·bNod·bPress·bRock·bPush·bPeer·bBreathe)으로 정한다. 없으면 bBreathe
- 만든 manifest를 `index.html`의 `<script type="application/json" id="illu-layers">`에도 그대로 넣는다(단일 파일·요약 모션이 이 지도를 쓴다)

## 3. 넣기
```html
<div class="illu tilt" data-tilt style="height:380px;padding:16px"><img src="assets/illust/<이름>.webp" alt="…"></div>
```
레이어가 있으면 장에 들어올 때 배경 → 코쇠 → 화살표·라벨 순으로 나타나고 코쇠가 숨 쉬듯 움직인다. `.navy`·`.black` 장에서는 `-d` 변형이 자동으로 쓰인다.

## 주의
- Pillow `Image.fromarray(...)`로 만든 이미지는 읽기 전용이라 `ImageDraw.floodfill`이 조용히 실패한다 → `.copy()` 후 칠한다(스크립트에 반영됨)
- 사각형으로 대충 자르면 어색하다. 색 덩어리·외곽선 기준으로 정밀하게 자른 결과를 화면에서 직접 확인한다
