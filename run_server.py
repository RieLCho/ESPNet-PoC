#!/usr/bin/env python3
"""
화자 인식 서버 실행 스크립트
메타버스 익명 화자 인식을 위한 API 서버를 실행합니다.
"""

import os
import argparse
from src.speaker_server import run_server

if __name__ == "__main__":
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description="화자 인식 서버")
    parser.add_argument("--host", type=str, default="0.0.0.0", 
                      help="호스트 주소 (기본값: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, 
                      help="포트 번호 (기본값: 8000)")
    parser.add_argument("--embeddings", type=str, default="speaker_embeddings.pkl", 
                      help="화자 임베딩 파일 경로 (기본값: speaker_embeddings.pkl)")
    parser.add_argument("--api-key", type=str, 
                      help="API 키 설정 (설정하지 않으면 환경 변수 또는 기본값 사용)")
    
    args = parser.parse_args()
    
    # API 키 설정
    if args.api_key:
        os.environ["API_KEY"] = args.api_key
    
    # 서버 실행
    print(f"화자 인식 서버를 {args.host}:{args.port}에서 시작합니다...")
    print(f"임베딩 파일: {args.embeddings}")
    
    run_server(
        host=args.host,
        port=args.port,
        embeddings_file=args.embeddings
    )