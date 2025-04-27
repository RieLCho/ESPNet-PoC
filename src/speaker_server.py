import os
import time
import uuid
import logging
import pickle
import base64
import tempfile
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Request, status, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
import uvicorn

from pydantic import BaseModel, Field

# 화자 인식 모듈 import
from speaker_recognition import SpeakerRecognition

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("speaker_server.log")
    ]
)
logger = logging.getLogger("speaker_server")

# API 키 인증 설정
API_KEY_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# 임베딩 저장 파일 경로
DEFAULT_EMBEDDINGS_FILE = os.environ.get("EMBEDDINGS_FILE", "speaker_embeddings.pkl")

# API 키 목록 (실제로는 보안 스토리지에서 로드해야 함)
API_KEYS = {
    "test_api_key_1234": "test_client",
    os.environ.get("API_KEY", ""): "default_client"
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

# 화자 인식 서버 클래스 (컨텍스트 관리 및 인증 처리)
class SpeakerRecognitionServer:
    def __init__(self, embeddings_file: str = DEFAULT_EMBEDDINGS_FILE):
        """
        화자 인식 서버 초기화
        
        Args:
            embeddings_file (str): 화자 임베딩 저장 경로
        """
        self.embeddings_file = embeddings_file
        self.model = SpeakerRecognition(embeddings_file)
        self.start_time = time.time()
        self.request_count = 0
        
        # 화자별 메타데이터 저장 딕셔너리 (실제 구현에서는 DB에 저장)
        self.speaker_metadata = {}
        
        # 화자-오디오 매핑 (실제 구현에서는 DB에 저장)
        self.speaker_audios = {}
        
        # 화자 만남 카운터 (실제 구현에서는 DB에 저장)
        self.encounter_counts = {}
        
        logger.info(f"화자 인식 서버가 초기화되었습니다. 임베딩 파일: {embeddings_file}")
        logger.info(f"등록된 화자 수: {len(self.model.speaker_embeddings)}")
        
    def verify_api_key(self, api_key: str = Depends(API_KEY_HEADER)) -> str:
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
            detail="유효하지 않은 API 키",
            headers={"WWW-Authenticate": API_KEY_NAME},
        )
    
    def decode_audio(self, audio_data_base64: str) -> str:
        """
        Base64로 인코딩된 오디오 데이터를 디코딩하여 임시 파일로 저장
        
        Args:
            audio_data_base64 (str): Base64로 인코딩된 오디오 데이터
            
        Returns:
            str: 임시 파일 경로
        """
        try:
            audio_data = base64.b64decode(audio_data_base64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            return temp_path
        except Exception as e:
            logger.error(f"오디오 디코딩 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"오디오 디코딩 실패: {str(e)}"
            )
    
    def register_speaker(self, request: SpeakerRegisterRequest) -> Dict[str, Any]:
        """
        화자 등록 처리
        
        Args:
            request (SpeakerRegisterRequest): 화자 등록 요청
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        start_time = time.time()
        self.request_count += 1
        
        speaker_id = request.anonymousId
        temp_audio_path = self.decode_audio(request.audioData)
        
        try:
            # 화자 등록
            self.model.register_speaker(speaker_id, temp_audio_path, save_immediately=True)
            
            # 메타데이터 저장
            if request.metadata:
                if speaker_id not in self.speaker_metadata:
                    self.speaker_metadata[speaker_id] = {}
                self.speaker_metadata[speaker_id].update(request.metadata)
            
            # 오디오 파일 정보 저장
            if speaker_id not in self.speaker_audios:
                self.speaker_audios[speaker_id] = []
            
            audio_info = {
                "timestamp": datetime.now().isoformat(),
                "originalFilename": request.metadata.get("originalFilename", "unknown")
            }
            self.speaker_audios[speaker_id].append(audio_info)
            
            processing_time = time.time() - start_time
            
            return {
                "status": "success",
                "anonymousId": speaker_id,
                "message": "화자가 성공적으로 등록되었습니다",
                "processingTime": processing_time,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"화자 등록 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"화자 등록 실패: {str(e)}"
            )
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
    
    def identify_speaker(self, request: SpeakerIdentifyRequest) -> Dict[str, Any]:
        """
        화자 식별 처리
        
        Args:
            request (SpeakerIdentifyRequest): 화자 식별 요청
            
        Returns:
            Dict[str, Any]: 식별 결과
        """
        start_time = time.time()
        self.request_count += 1
        
        temp_audio_path = self.decode_audio(request.audioData)
        
        try:
            # 화자 식별
            speaker_id, similarity = self.model.identify_speaker(
                temp_audio_path, 
                threshold=request.threshold
            )
            
            # 메타버스 컨텍스트 로깅
            if request.metaverseContext:
                context_str = ", ".join([f"{k}: {v}" for k, v in request.metaverseContext.items()])
                logger.info(f"메타버스 컨텍스트: {context_str}")
            
            # 식별된 화자의 만남 카운트 증가
            if speaker_id:
                if speaker_id not in self.encounter_counts:
                    self.encounter_counts[speaker_id] = 0
                self.encounter_counts[speaker_id] += 1
            
            processing_time = time.time() - start_time
            
            # 응답 구성
            result = {
                "status": "success",
                "anonymousId": speaker_id if speaker_id else None,
                "confidence": float(similarity) if similarity is not None else 0.0,
                "isKnownSpeaker": speaker_id is not None,
                "processingTime": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # 화자 메타데이터 추가 (식별된 경우)
            if speaker_id and speaker_id in self.speaker_metadata:
                result["metadata"] = self.speaker_metadata[speaker_id]
            
            # 만남 횟수 추가
            if speaker_id:
                result["encounters"] = self.encounter_counts[speaker_id]
            
            return result
        
        except Exception as e:
            logger.error(f"화자 식별 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"화자 식별 실패: {str(e)}"
            )
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
    
    def get_speaker_info(self, speaker_id: str) -> Dict[str, Any]:
        """
        화자 정보 조회
        
        Args:
            speaker_id (str): 화자 ID
            
        Returns:
            Dict[str, Any]: 화자 정보
        """
        if speaker_id not in self.model.speaker_embeddings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"화자 ID {speaker_id}를 찾을 수 없습니다"
            )
        
        # 화자 정보 구성
        speaker_info = {
            "anonymousId": speaker_id,
            "registeredAt": datetime.now().isoformat(),  # 실제로는 DB에서 조회
            "audioCount": len(self.speaker_audios.get(speaker_id, [])),
            "encounters": self.encounter_counts.get(speaker_id, 0)
        }
        
        # 메타데이터 추가
        if speaker_id in self.speaker_metadata:
            speaker_info["metadata"] = self.speaker_metadata[speaker_id]
        
        return speaker_info
    
    def list_speakers(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        화자 목록 조회
        
        Args:
            limit (int): 최대 조회 수
            offset (int): 시작 오프셋
            
        Returns:
            Dict[str, Any]: 화자 목록
        """
        all_speakers = list(self.model.speaker_embeddings.keys())
        total_count = len(all_speakers)
        
        # 페이지네이션 적용
        paginated_speakers = all_speakers[offset:offset+limit]
        
        # 화자 목록 구성
        speakers_info = []
        for speaker_id in paginated_speakers:
            speaker_info = {
                "anonymousId": speaker_id,
                "audioCount": len(self.speaker_audios.get(speaker_id, [])),
                "encounters": self.encounter_counts.get(speaker_id, 0)
            }
            
            # 메타데이터 추가
            if speaker_id in self.speaker_metadata:
                speaker_info["metadata"] = self.speaker_metadata[speaker_id]
            
            speakers_info.append(speaker_info)
        
        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "speakers": speakers_info
        }
    
    def delete_speaker(self, speaker_id: str) -> Dict[str, Any]:
        """
        화자 삭제
        
        Args:
            speaker_id (str): 화자 ID
            
        Returns:
            Dict[str, Any]: 삭제 결과
        """
        if speaker_id not in self.model.speaker_embeddings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"화자 ID {speaker_id}를 찾을 수 없습니다"
            )
        
        try:
            # 화자 임베딩 삭제
            del self.model.speaker_embeddings[speaker_id]
            self.model.save_embeddings()
            
            # 메타데이터 및 관련 정보 삭제
            if speaker_id in self.speaker_metadata:
                del self.speaker_metadata[speaker_id]
            
            if speaker_id in self.speaker_audios:
                del self.speaker_audios[speaker_id]
            
            if speaker_id in self.encounter_counts:
                del self.encounter_counts[speaker_id]
            
            return {
                "status": "success",
                "message": f"화자 ID {speaker_id}가 성공적으로 삭제되었습니다",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"화자 삭제 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"화자 삭제 실패: {str(e)}"
            )
    
    def batch_process(self, request: BatchRequest) -> Dict[str, Any]:
        """
        배치 작업 처리
        
        Args:
            request (BatchRequest): 배치 작업 요청
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        start_time = time.time()
        operation = request.operation
        results = []
        
        if operation not in ["register", "identify", "delete"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 작업: {operation}"
            )
        
        for i, item in enumerate(request.items):
            try:
                if operation == "register":
                    # 화자 등록 요청으로 변환
                    register_request = SpeakerRegisterRequest(**item)
                    result = self.register_speaker(register_request)
                
                elif operation == "identify":
                    # 화자 식별 요청으로 변환
                    identify_request = SpeakerIdentifyRequest(**item)
                    result = self.identify_speaker(identify_request)
                
                elif operation == "delete":
                    # 화자 삭제
                    speaker_id = item.get("anonymousId")
                    if not speaker_id:
                        raise ValueError("화자 ID가 필요합니다")
                    result = self.delete_speaker(speaker_id)
                
                results.append({
                    "index": i,
                    "status": "success",
                    "result": result
                })
            
            except Exception as e:
                logger.error(f"배치 작업 오류 (항목 {i}): {e}")
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(e)
                })
        
        processing_time = time.time() - start_time
        
        return {
            "operation": operation,
            "totalItems": len(request.items),
            "successCount": sum(1 for r in results if r["status"] == "success"),
            "errorCount": sum(1 for r in results if r["status"] == "error"),
            "processingTime": processing_time,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

# FastAPI 앱 생성
app = FastAPI(
    title="화자 인식 API",
    description="메타버스 환경에서 익명 화자 인식을 위한 API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 구현에서는 허용된 오리진만 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서버 인스턴스 생성
server = SpeakerRecognitionServer()

# 미들웨어: 모든 요청 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({process_time:.4f}초)")
    
    return response

# API 엔드포인트
@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    uptime = time.time() - server.start_time
    return {
        "status": "ok",
        "uptime": uptime,
        "requestCount": server.request_count,
        "speakerCount": len(server.model.speaker_embeddings),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/speakers/register")
async def register_speaker(
    request: SpeakerRegisterRequest,
    api_key: str = Depends(server.verify_api_key)
):
    """화자 등록"""
    return server.register_speaker(request)

@app.post("/speakers/identify")
async def identify_speaker(
    request: SpeakerIdentifyRequest,
    api_key: str = Depends(server.verify_api_key)
):
    """화자 식별"""
    return server.identify_speaker(request)

@app.get("/speakers/{speaker_id}")
async def get_speaker_info(
    speaker_id: str,
    api_key: str = Depends(server.verify_api_key)
):
    """화자 정보 조회"""
    return server.get_speaker_info(speaker_id)

@app.get("/speakers")
async def list_speakers(
    limit: int = 100,
    offset: int = 0,
    api_key: str = Depends(server.verify_api_key)
):
    """화자 목록 조회"""
    return server.list_speakers(limit, offset)

@app.delete("/speakers/{speaker_id}")
async def delete_speaker(
    speaker_id: str,
    api_key: str = Depends(server.verify_api_key)
):
    """화자 삭제"""
    return server.delete_speaker(speaker_id)

@app.post("/batch")
async def batch_process(
    request: BatchRequest,
    api_key: str = Depends(server.verify_api_key)
):
    """배치 작업 처리"""
    return server.batch_process(request)

# 서버 실행 함수
def run_server(host="0.0.0.0", port=8000, embeddings_file=DEFAULT_EMBEDDINGS_FILE):
    """서버 실행"""
    logger.info(f"화자 인식 서버를 {host}:{port}에서 시작합니다.")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="화자 인식 서버")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="호스트 주소")
    parser.add_argument("--port", type=int, default=8000, help="포트 번호")
    parser.add_argument("--embeddings", type=str, default=DEFAULT_EMBEDDINGS_FILE, help="임베딩 파일 경로")
    
    args = parser.parse_args()
    run_server(args.host, args.port, args.embeddings)