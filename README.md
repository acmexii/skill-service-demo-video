# Service Demo Video

실제 서비스 홈페이지·앱을 Playwright로 탐색하고 녹화해 기업용 기능 소개 영상을 만드는 Codex 스킬입니다. 특정 서비스에 고정되지 않습니다.

## 포함 기능

- 1920×1080 실제 브라우저 녹화, 최종 30fps MP4
- 곡선·가감속 마우스 이동과 `steps: 3`, 클릭 표시
- 글자당 100~200ms 입력과 부드러운 휠 스크롤
- UI 줌인·줌아웃, 주변 암전, 연결선·설명 콜아웃
- 루트 `.env`의 ElevenLabs Key·Voice 설정과 문자 타이밍 기반 자막
- 새 탭 녹화 연결, iframe 커서 중복 방지
- 근거·스토리보드·재현 가능한 코드·검수 지침

## 설치

Codex에 다음과 같이 요청하세요.

```text
$skill-installer https://github.com/acmexii/skill-service-demo-video
```

수동 설치는 개인 스킬 폴더에 복제합니다.

```sh
git clone https://github.com/acmexii/skill-service-demo-video.git ~/.codex/skills/service-demo-video
```

설치 후 다음 메시지부터 `$service-demo-video`로 사용합니다. 기존 설치본이 있다면 로컬 변경을 확인한 후 업데이트하세요.

## 사용 예시

```text
$service-demo-video https://대상서비스주소/ 주요 기능을 소개하는 30초 영상을 만들어 줘.
1080p, 자연스러운 커서와 타이핑, UI 확대, 한국어 내레이션을 적용해 줘.
```

## 실행 환경

Node.js, Playwright와 Chromium, Python, Pillow, FFmpeg가 필요합니다.

```sh
npm install playwright
npx playwright install chromium
python -m pip install Pillow imageio-ffmpeg
```

프로젝트 루트의 `.env`에 아래 변수명을 설정합니다. 실제 값은 이 저장소에 넣지 않습니다.

```dotenv
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_VOICE_ID=your_voice_id
```

Voice는 `VOICE_ID` 변수도 지원합니다. 명시한 프로젝트 루트 `.env`를 우선하며, Key·Voice가 빠지면 임의로 대체하지 않습니다.

```sh
python scripts/tts.py --check --root /path/to/project
node scripts/record.cjs --plan /path/to/plan.json --out /path/to/build
python scripts/render.py --recording /path/to/build/recording.json --out /path/to/final
```

계획 작성·음성 생성·환경변수·검수 방법은 [실행 안내](references/workflow.md)를 참고하세요. 스킬 작성이나 테스트만으로 유료 음성을 생성하지 않습니다. ElevenLabs 합성 실행은 해당 계정의 사용량을 소비할 수 있습니다.

## 검증

```sh
python scripts/test_config.py
node scripts/selftest.cjs --out /path/to/temporary-validation
```

설정 테스트는 API 호출 없이 실행됩니다. 브라우저 테스트는 로컬 데모로 타이핑·클릭·스크롤·새 탭을 확인합니다. 합성 결과는 모든 장면을 재생·청취하고 검수해야 합니다. 자동 검사만으로 영상 품질이나 음성 발음을 보증하지 않습니다.

## 구성

- `SKILL.md`: 제작·검증·전달 지침
- `scripts/`: 녹화·마우스·음성·합성·테스트 코드
- `references/`: 참고 영상 초반 1분 관찰 및 실행 안내
- `agents/openai.yaml`: Codex 표시 정보

참고 영상은 외부 링크와 시각 연출 관찰만 포함합니다. 원본 영상·음원·브랜드 자산은 재배포하지 않습니다. 공개 홈페이지의 제품 이미지를 로그인 앱의 실제 기능 실행으로 표현하지 않습니다. `.env`, 쿠키, 세션, 고객 데이터와 생성 영상은 저장소에 포함하지 않습니다.
