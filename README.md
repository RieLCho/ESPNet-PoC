# ESPnet 기반 화자 인식 시스템 PoC

이 프로젝트는 ESPnet을 사용하여 구현된 간단한 화자 인식 시스템의 Proof of Concept입니다.

## 설치 방법

0. python 3.11 준비

```
pyenv install 3.11
```

1. 필요한 패키지 설치:

```bash
uv add -r requirements.tsx
```

or

```
source .venv/bin/activate && uv pip install --index-strategy unsafe-best-match -r requirements.txt
```

2. ESPnet ASR 모델 다운로드:
   ESPnet 모델은 다음 링크에서 다운로드할 수 있습니다:
   https://github.com/espnet/espnet_model_zoo

## 사용 방법

### 화자 등록

```bash
python src/demo.py --model_path /path/to/asr_model \
                  --register_audio /path/to/speaker_audio.wav \
                  --speaker_id "speaker1"
```

### 화자 식별

```bash
python src/demo.py --model_path /path/to/asr_model \
                  --test_audio /path/to/test_audio.wav
```

## 디렉토리 구조

```
.
├── data/
│   ├── speaker_embeddings/    # 저장된 화자 임베딩
│   └── audio_samples/         # 테스트용 오디오 샘플
├── src/
│   ├── speaker_recognition.py # 화자 인식 핵심 로직
│   └── demo.py               # 데모 스크립트
└── requirements.txt          # 필요한 패키지 목록
```

## 참고사항

- 입력 오디오는 WAV 형식을 권장합니다.
- 샘플링 레이트는 자동으로 16kHz로 변환됩니다. 
```
for f in ./data/mika/*.wav; do ffmpeg -i "$f" -ar 16000 -ac 1 "${f%.*}_converted.wav" -y; done
```
- 화자 식별 시 기본 유사도 임계값은 0.7입니다.
