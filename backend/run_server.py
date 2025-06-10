#!/usr/bin/env python3
"""
ESPNet 화자 인식 서버 실행 스크립트
"""

import uvicorn
import os
import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """서버 실행"""
    # 환경 변수 설정
    os.environ.setdefault("API_KEY", "metaverse_demo_key")
    os.environ.setdefault("EMBEDDINGS_FILE", "speaker_embeddings.pkl")
    
    print("🎤 ESPNet 화자 인식 서버를 시작합니다...")
    print("📍 API 문서: http://localhost:8000/docs")
    print("🔍 헬스 체크: http://localhost:8000/health")
    print("🔑 API 키: metaverse_demo_key")
    print("-" * 50)
    
    # 서버 실행
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
