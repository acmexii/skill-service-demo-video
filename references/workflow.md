# 실행과 계획 형식

필요 런타임: Node.js + Playwright + Chromium, Python + Pillow, FFmpeg(libx264/AAC). 런타임은 현재 환경에서 찾고 스킬에 특정 PC의 경로를 고정하지 않는다. Playwright 설치와 브라우저 버전이 다르면 설치된 실행파일을 명시하거나 일치하는 브라우저를 설치한다. 사용자 요청 없이 화면에 새 브라우저 창을 띄우지 않는다. 코드의 기본은 headless다.

## 준비

- `PLAYWRIGHT_MODULE`: 일반 require로 찾지 못할 때 Playwright 패키지 절대 경로.
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE`: 기본 Chromium 실행파일이 없을 때 설치된 브라우저 절대 경로.
- `FFMPEG`: FFmpeg 실행파일. 없으면 PATH 또는 imageio_ffmpeg에서 찾는다.
- `DEMO_FONT`: 해당 언어가 있는 글꼴 파일. 없으면 Windows 맑은 고딕 또는 Noto Sans CJK를 찾는다.
- 비밀은 `<프로젝트 루트>/.env`에서만 읽는다. Voice 변수는 `ELEVENLABS_VOICE_ID` 우선, 없으면 `VOICE_ID`. `.env`를 출력하거나 패키징하지 않는다.

## 계획 예시

아래 URL·selector는 사용 전에 실제 대상 DOM으로 교체한다. 시간은 최종 출력 초 단위다. 앱에서 비밀·실데이터를 타이핑하지 않는다. `scene.id`는 안전한 파일명으로 정하고 `duration`은 실제 녹화 조작 시간보다 길게 잡는다.

```json
{
  "url": "https://대상서비스주소/",
  "readySelector": "관찰한_준비완료_요소",
  "locale": "ko-KR",
  "scenes": [{
    "id": "search",
    "claim_ids": ["C01"],
    "duration": 8,
    "narration": "필요한 문서를 검색하고 결과를 확인하세요.",
    "audio_file": "audio/search.mp3",
    "alignment_file": "audio/search.alignment.json",
    "audio_offset": 0.45,
    "actions": [
      {"kind": "type", "selector": "관찰한_검색창", "text": "데모 보고서", "clear": true, "min": 100, "max": 200},
      {"kind": "click", "selector": "관찰한_검색버튼", "waitForSelector": "관찰한_결과"},
      {"kind": "move", "x": 1500, "y": 750, "ms": 700}
    ],
    "readySelector": "관찰한_결과",
    "holdMs": 1800,
    "focusSelector": "관찰한_결과",
    "zoom": 1.25,
    "spotlight": true,
    "callout": "검색 결과를 한눈에 확인"
  }]
}
```

actions: `type`, `click`, `hover`, `scroll`(delta·ms), `move`(x·y·ms), `ready`(selector·timeout), `wait`(ms). 메뉴는 hover 후 나타난 selector를 ready로 기다린다. 새 탭 클릭에는 waitForSelector를 넣어 목적지 로드를 확인한다. focusSelector는 **최종 체류 시점**의 bbox다. 변하는 위치에 마스크를 먼저 얹지 않도록 줌·마스크는 기본적으로 actions가 끝난 뒤 hold 구간부터 시작한다. 전체 장면에 강조하려면 명시적으로 zoomStart=0을 지정하되 대상을 가리지 않는지 검수한다.

줌 좌표는 원본 1920×1080의 정규화 focus 값이다. `zoomStart`, `zoomEnd`로 범위를 조정한다. 마스크·콜아웃·커서는 화면과 함께 확대된다. 콜아웃을 둘 공간이 부족하거나 확대 크롭 밖으로 나가면 오류를 반환한다. 포커스·배율을 줄이거나 배치를 수정하고 글자를 무리하게 축소하지 않는다. 긴 문장의 자막은 장면을 의미 단위로 나누어 문자 타이밍과 함께 구성한다. 음성 없는 초안은 `silentPreview: true`를 명시한다. 대본이 있는데 audio_file이 없는 최종본을 실수로 납품하지 않도록 기본값은 오류다.

## 실행

1. `python scripts/tts.py --check --root <프로젝트 루트>`로 설정 존재만 확인한다.
2. 유료 음성 생성이 요청된 경우에만 장면별 `narration.txt`를 작성하고 `python scripts/tts.py --root <루트> --text-file <장면 대본> --out-prefix <build/audio/search>`를 실행한다. 인증·권한·한도 오류에는 자동 재시도·다른 Voice 대체를 하지 않는다.
3. `node scripts/record.cjs --plan <plan.json> --out <build>`로 녹화한다. 계획의 audio 경로는 recording.json 폴더 기준이며 절대 경로도 가능하다.
4. `python scripts/render.py --recording <build/recording.json> --out <build/final> --duration <요청 초>`로 합성한다. 요청 시간이 미정이면 --duration을 생략한다. 장면 길이 합계가 요청 시간과 다르거나 음성이 장면 밖으로 넘으면 수정 후 다시 합성한다.
5. 출력 final.mp4의 모든 장면을 재생·청취하고 review-N.png를 확인한다. 커서 이동·줌을 정상 속도로 확인한다. `qa.md`는 사람이 실제로 수행한 검사만 적는다. 렌더러의 전체 디코딩 검사로 시청·청취를 대신하지 않는다.

## 로컬 검증

`node scripts/selftest.cjs --out <임시 검증 폴더>`는 외부 사이트나 유료 API 없이 로컬 HTTP 데모를 녹화한다. 검색 입력·버튼·결과·스크롤·새 탭·iframe 커서를 검증하고 3장면 계획을 저장한다. 기기 성능에 맞춰 테스트 장면 길이를 늘리므로 고정 20초 테스트가 아니다. 이어 render.py로 합성해 줌과 포커스·콜아웃·자막 배치를 확인한다. 데모 결과는 서비스 소개 영상의 실제 고객 사례로 사용하지 않는다.

설치본/공유 ZIP에는 스킬과 지원 코드만 포함한다. 테스트 결과·프로젝트 `.env`·API 응답 로그·쿠키는 포함하지 않는다.
