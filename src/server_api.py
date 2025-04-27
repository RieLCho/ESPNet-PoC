import os
import json
import base64
import requests
from typing import Dict, List, Optional, Any, Tuple, Union, BinaryIO
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SpeakerServerAPI")

class SpeakerServerAPI:
    """화자 인식 서버 API 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        API 클라이언트 초기화
        
        Args:
            base_url (str): API 서버 기본 URL
            api_key (str, optional): API 인증 키
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        
        if api_key:
            self.headers["X-API-Key"] = api_key
            
        logger.info(f"SpeakerServerAPI 초기화 완료. 서버: {base_url}")
    
    def health_check(self) -> bool:
        """
        서버 상태 확인
        
        Returns:
            bool: 서버가 정상 작동 중이면 True
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json().get("status") == "ok"
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def load_audio_file(self, filepath: str) -> str:
        """
        오디오 파일을 로드하고 base64 인코딩
        
        Args:
            filepath (str): 오디오 파일 경로
            
        Returns:
            str: base64로 인코딩된 오디오 데이터
        """
        with open(filepath, "rb") as audio_file:
            return base64.b64encode(audio_file.read()).decode('utf-8')
    
    def register_speaker(self, speaker_id: str, audio_data: str, 
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        화자 등록
        
        Args:
            speaker_id (str): 화자 ID
            audio_data (str): base64로 인코딩된 오디오 데이터
            metadata (dict, optional): 추가 메타데이터
            
        Returns:
            dict: API 응답
        """
        payload = {
            "anonymousId": speaker_id,
            "audioData": audio_data,
            "metadata": metadata or {}
        }
        
        response = requests.post(
            f"{self.base_url}/speakers/register", 
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"화자 등록 실패: {response.status_code} {response.text}")
            response.raise_for_status()
            
        return response.json()
    
    def identify_speaker(self, audio_data: str, threshold: float = 0.7, 
                        context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        화자 식별
        
        Args:
            audio_data (str): base64로 인코딩된 오디오 데이터
            threshold (float): 유사도 임계값
            context (dict, optional): 메타버스 컨텍스트 정보
            
        Returns:
            dict: API 응답
        """
        payload = {
            "audioData": audio_data,
            "threshold": threshold,
            "metaverseContext": context or {}
        }
        
        response = requests.post(
            f"{self.base_url}/speakers/identify", 
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"화자 식별 실패: {response.status_code} {response.text}")
            response.raise_for_status()
            
        return response.json()
    
    def get_speaker_info(self, speaker_id: str) -> Dict[str, Any]:
        """
        화자 정보 조회
        
        Args:
            speaker_id (str): 화자 ID
            
        Returns:
            dict: API 응답
        """
        response = requests.get(
            f"{self.base_url}/speakers/{speaker_id}", 
            headers=self.headers
        )
        
        if response.status_code != 200:
            logger.error(f"화자 정보 조회 실패: {response.status_code} {response.text}")
            response.raise_for_status()
            
        return response.json()
    
    def list_speakers(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        화자 목록 조회
        
        Args:
            limit (int): 최대 조회 수
            offset (int): 시작 오프셋
            
        Returns:
            dict: API 응답
        """
        response = requests.get(
            f"{self.base_url}/speakers?limit={limit}&offset={offset}", 
            headers=self.headers
        )
        
        if response.status_code != 200:
            logger.error(f"화자 목록 조회 실패: {response.status_code} {response.text}")
            response.raise_for_status()
            
        return response.json()
    
    def delete_speaker(self, speaker_id: str) -> Dict[str, Any]:
        """
        화자 삭제
        
        Args:
            speaker_id (str): 화자 ID
            
        Returns:
            dict: API 응답
        """
        response = requests.delete(
            f"{self.base_url}/speakers/{speaker_id}", 
            headers=self.headers
        )
        
        if response.status_code != 200:
            logger.error(f"화자 삭제 실패: {response.status_code} {response.text}")
            response.raise_for_status()
            
        return response.json()
    
    def batch_process(self, operation: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        배치 작업 처리
        
        Args:
            operation (str): 작업 유형 (register, identify, delete)
            items (list): 작업 항목 목록
            
        Returns:
            dict: API 응답
        """
        payload = {
            "operation": operation,
            "items": items
        }
        
        response = requests.post(
            f"{self.base_url}/batch", 
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"배치 작업 처리 실패: {response.status_code} {response.text}")
            response.raise_for_status()
            
        return response.json()