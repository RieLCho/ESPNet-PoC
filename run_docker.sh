#!/bin/bash

# Docker 이미지 빌드
docker build -t espnet-speaker-recognition .

# Docker 컨테이너 실행
# $1: 모델 경로
# $2: 등록할 화자 음성 파일
# $3: 화자 ID
# $4: 테스트할 음성 파일
docker run --rm -v $(pwd)/audio:/app/audio -v $(pwd)/models:/app/models \
    espnet-speaker-recognition \
    --model_path "$1" \
    --register_audio "$2" \
    --speaker_id "$3" \
    --test_audio "$4" 