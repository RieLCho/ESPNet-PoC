# FastAPI 기반 화자 인식 서버
import os
import time
import uuid
import logging
import base64
import tempfile
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
import uvicorn

from pydantic import BaseModel, Field

# 화자 인식 모듈 import
from src.speaker_recognition import SpeakerRecognition

# 로그 디렉토리 생성
os.makedirs("logs", exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/speaker_server.log")
    ]
)
logger = logging.getLogger("speaker_server")

# API 키 인증 설정
API_KEY_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# 임베딩 저장 파일 경로
DEFAULT_EMBEDDINGS_FILE = os.environ.get("EMBEDDINGS_FILE", "speaker_embeddings.pkl")

# API 키 목록 (실제로는 환경 변수나 보안 스토리지에서 로드해야 함)
API_KEYS = {
    "test_api_key_1234": "test_client",
    "metaverse_demo_key": "metaverse_client",
    os.environ.get("API_KEY", "default_key"): "default_client"
}

# 데이터 모델 정의
class SpeakerRegisterRequest(BaseModel):
    anonymousId: str = Field(..., description="익명 화자 ID")
    audioData: str = Field(..., description="Base64로 인코딩된 오디오 데이터")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 메타데이터")

class SpeakerIdentifyRequest(BaseModel):
    audioData: str = Field(..., description="Base64로 인코딩된 오디오 데이터")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="유사도 임계값")
    metaverseContext: Optional[Dict[str, Any]] = Field(default_factory=dict, description="메타버스 컨텍스트")

class BatchRequest(BaseModel):
    operation: str = Field(..., description="작업 유형 (register, identify, delete)")
    items: List[Dict[str, Any]] = Field(..., description="작업 항목 목록")

class AudioFile(BaseModel):
    filename: str
    content: str  # base64 encoded

# FastAPI 앱 초기화
app = FastAPI(
    title="ESPNet 화자 인식 API",
    description="메타버스용 실시간 화자 인식 시스템",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정 (프론트엔드 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
speaker_model = None
request_count = 0
start_time = time.time()
speaker_metadata = {}  # 화자별 메타데이터 저장

def verify_api_key(api_key: str = Depends(API_KEY_HEADER)) -> str:
    """API 키 검증"""
    if api_key in API_KEYS:
        return api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API 키가 필요합니다",
            headers={"WWW-Authenticate": API_KEY_NAME},
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="유효하지 않은 API 키입니다"
    )

def decode_audio_data(audio_data: str) -> str:
    """Base64 오디오 데이터를 임시 파일로 저장"""
    try:
        # Base64 디코딩
        audio_bytes = base64.b64decode(audio_data)
        
        # 임시 파일 생성
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.write(audio_bytes)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        logger.error(f"오디오 디코딩 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 오디오 데이터: {str(e)}"
        )

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 화자 인식 모델 로드"""
    global speaker_model
    try:
        logger.info("화자 인식 모델을 로딩 중입니다...")
        speaker_model = SpeakerRecognition(DEFAULT_EMBEDDINGS_FILE)
        logger.info(f"화자 인식 서버가 시작되었습니다. 등록된 화자 수: {len(speaker_model.speaker_embeddings)}")
    except Exception as e:
        logger.error(f"모델 로딩 실패: {e}")
        raise e

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    global request_count
    uptime = time.time() - start_time
    
    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 2),
        "requests_processed": request_count,
        "registered_speakers": len(speaker_model.speaker_embeddings) if speaker_model else 0,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/speakers/register")
async def register_speaker(
    request: SpeakerRegisterRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """화자 등록"""
    global request_count
    request_count += 1
    
    try:
        logger.info(f"화자 등록 요청: {request.anonymousId}")
        
        # 오디오 데이터 디코딩
        temp_audio_path = decode_audio_data(request.audioData)
        
        try:
            # 화자 등록
            speaker_model.register_speaker(request.anonymousId, temp_audio_path, save_immediately=True)
            
            # 메타데이터 저장
            speaker_metadata[request.anonymousId] = {
                "registered_at": datetime.now().isoformat(),
                "metadata": request.metadata,
                "client": API_KEYS.get(api_key, "unknown")
            }
            
            logger.info(f"화자 등록 완료: {request.anonymousId}")
            
            return {
                "status": "success",
                "message": "화자가 성공적으로 등록되었습니다",
                "anonymousId": request.anonymousId,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            # 임시 파일 정리
            background_tasks.add_task(os.unlink, temp_audio_path)
            
    except Exception as e:
        logger.error(f"화자 등록 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"화자 등록 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/speakers/identify")
async def identify_speaker(
    request: SpeakerIdentifyRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """화자 식별"""
    global request_count
    request_count += 1
    
    try:
        logger.info("화자 식별 요청")
        
        # 오디오 데이터 디코딩
        temp_audio_path = decode_audio_data(request.audioData)
        
        try:
            # 화자 식별
            start_time_identify = time.time()
            speaker_id, similarity = speaker_model.identify_speaker(
                temp_audio_path, 
                threshold=request.threshold
            )
            processing_time = time.time() - start_time_identify
            
            is_known = speaker_id is not None
            
            result = {
                "status": "success",
                "anonymousId": speaker_id,
                "confidence": float(similarity),
                "isKnownSpeaker": is_known,
                "threshold": request.threshold,
                "processingTimeSeconds": round(processing_time, 3),
                "timestamp": datetime.now().isoformat()
            }
            
            # 알려진 화자인 경우 메타데이터 포함
            if is_known and speaker_id in speaker_metadata:
                result["speakerInfo"] = speaker_metadata[speaker_id]
            
            logger.info(f"화자 식별 결과: {speaker_id} (유사도: {similarity:.4f})")
            
            return result
            
        finally:
            # 임시 파일 정리
            background_tasks.add_task(os.unlink, temp_audio_path)
            
    except Exception as e:
        logger.error(f"화자 식별 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"화자 식별 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/speakers")
async def list_speakers(api_key: str = Depends(verify_api_key)):
    """등록된 화자 목록 조회"""
    try:
        speakers = []
        for speaker_id, embeddings in speaker_model.speaker_embeddings.items():
            speaker_info = {
                "anonymousId": speaker_id,
                "embeddingCount": len(embeddings),
                "registeredAt": speaker_metadata.get(speaker_id, {}).get("registered_at", "Unknown"),
                "metadata": speaker_metadata.get(speaker_id, {}).get("metadata", {})
            }
            speakers.append(speaker_info)
        
        return {
            "status": "success",
            "speakers": speakers,
            "totalCount": len(speakers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"화자 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"화자 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.delete("/speakers/{speaker_id}")
async def delete_speaker(speaker_id: str, api_key: str = Depends(verify_api_key)):
    """화자 삭제"""
    try:
        if speaker_id not in speaker_model.speaker_embeddings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"화자를 찾을 수 없습니다: {speaker_id}"
            )
        
        # 화자 임베딩 삭제
        del speaker_model.speaker_embeddings[speaker_id]
        
        # 메타데이터 삭제
        if speaker_id in speaker_metadata:
            del speaker_metadata[speaker_id]
        
        # 변경사항 저장
        speaker_model.save_embeddings()
        
        logger.info(f"화자 삭제 완료: {speaker_id}")
        
        return {
            "status": "success",
            "message": f"화자가 성공적으로 삭제되었습니다: {speaker_id}",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"화자 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"화자 삭제 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/stats")
async def get_statistics(api_key: str = Depends(verify_api_key)):
    """서버 통계"""
    uptime = time.time() - start_time
    
    return {
        "status": "success",
        "statistics": {
            "uptime_seconds": round(uptime, 2),
            "uptime_formatted": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
            "total_requests": request_count,
            "registered_speakers": len(speaker_model.speaker_embeddings),
            "requests_per_minute": round(request_count / (uptime / 60), 2) if uptime > 0 else 0,
            "model_loaded": speaker_model is not None,
            "embeddings_file": DEFAULT_EMBEDDINGS_FILE
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
