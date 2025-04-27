#!/usr/bin/env python3
"""
화자 인식 클라이언트 실행 스크립트
메타버스 익명 화자 인식 서버에 연결하는 클라이언트를 실행합니다.
"""

import os
import argparse
from src.realtime_speaker_recognition import RealtimeSpeakerRecognition

if __name__ == "__main__":
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description="화자 인식 클라이언트")
    parser.add_argument("--server", type=str, default="http://localhost:8000",
                      help="서버 URL (기본값: http://localhost:8000)")
    parser.add_argument("--api-key", type=str, default="test_api_key_1234",
                      help="API 키 (기본값: test_api_key_1234)")
    parser.add_argument("--duration", type=int, default=5,
                      help="녹음 시간 (초) (기본값: 5)")
    parser.add_argument("--threshold", type=float, default=0.7,
                      help="유사도 임계값 (기본값: 0.7)")
    parser.add_argument("--local-fallback", action="store_true",
                      help="서버 연결 실패 시 로컬 모델 사용")
    parser.add_argument("--embeddings", type=str, default="speaker_embeddings.pkl",
                      help="로컬 임베딩 파일 경로 (기본값: speaker_embeddings.pkl)")
    
    args = parser.parse_args()
    
    print(f"화자 인식 클라이언트를 시작합니다...")
    print(f"서버: {args.server}")
    print(f"녹음 시간: {args.duration}초")
    
    # 클라이언트 초기화 및 실행
    client = RealtimeSpeakerRecognition(
        server_url=args.server,
        api_key=args.api_key,
        duration=args.duration,
        threshold=args.threshold,
        use_local_fallback=args.local_fallback,
        embeddings_file=args.embeddings
    )
    
    # 대화형 모드 실행
    client.interactive_mode()