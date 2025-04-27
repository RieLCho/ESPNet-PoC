import os
import time
import wave
import numpy as np
import sounddevice as sd
from tempfile import NamedTemporaryFile
from pathlib import Path
import uuid
from typing import Optional, Dict, Any

# 서버 API 모듈 import
from server_api import SpeakerServerAPI

class RealtimeSpeakerRecognition:
    def __init__(self, 
                 server_url="http://localhost:8000",
                 api_key=None,
                 sample_rate=16000, 
                 duration=5, 
                 threshold=0.7,
                 use_local_fallback=True,
                 embeddings_file="speaker_embeddings.pkl"):
        """
        실시간 화자 인식 시스템 초기화
        
        Args:
            server_url (str): 화자 인식 서버 URL
            api_key (str, optional): API 인증 키
            sample_rate (int): 샘플링 레이트 (Hz)
            duration (int): 녹음 기간 (초)
            threshold (float): 화자 식별을 위한 유사도 임계값
            use_local_fallback (bool): 서버 연결 실패 시 로컬 모델 사용 여부
            embeddings_file (str): 로컬 화자 임베딩 파일 경로 (로컬 폴백용)
        """
        self.server_api = SpeakerServerAPI(server_url, api_key)
        self.sample_rate = sample_rate
        self.duration = duration
        self.threshold = threshold
        self.use_local_fallback = use_local_fallback
        
        # 로컬 폴백을 위한 설정
        self.local_model = None
        self.embeddings_file = embeddings_file
        
        print(f"실시간 화자 인식 시스템이 초기화되었습니다.")
        print(f"서버: {server_url}")
        print(f"샘플링 레이트: {sample_rate} Hz, 녹음 시간: {duration}초, 임계값: {threshold}")
        
        # 서버 연결 테스트
        if self._test_server_connection():
            print("서버 연결 성공: 온라인 화자 인식 시스템이 활성화되었습니다.")
        else:
            print("서버 연결 실패!")
            if use_local_fallback:
                print("로컬 폴백 모델을 초기화합니다...")
                self._init_local_model()
            else:
                print("로컬 폴백이 비활성화되어 있습니다.")
    
    def _test_server_connection(self) -> bool:
        """서버 연결 상태 확인"""
        try:
            return self.server_api.health_check()
        except Exception as e:
            print(f"서버 연결 오류: {e}")
            return False
    
    def _init_local_model(self):
        """로컬 폴백 모델 초기화"""
        try:
            from speaker_recognition import SpeakerRecognition
            self.local_model = SpeakerRecognition(self.embeddings_file)
            print("로컬 폴백 모델 초기화 완료")
        except Exception as e:
            print(f"로컬 모델 초기화 실패: {e}")
            self.local_model = None
    
    def record_audio(self):
        """
        마이크에서 오디오를 녹음
        
        Returns:
            str: 임시 녹음 파일 경로
        """
        print(f"\n{self.duration}초 동안 녹음을 시작합니다...")
        
        # 녹음 설정
        recording = sd.rec(
            int(self.duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16'
        )
        
        # 녹음이 완료될 때까지 대기
        sd.wait()
        print("녹음 완료!")
        
        # 임시 파일에 오디오 저장
        with NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
            temp_filename = temp_audio_file.name
            
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(1)  # 모노 채널
                wf.setsampwidth(2)  # int16 = 2 바이트
                wf.setframerate(self.sample_rate)
                wf.writeframes(recording.tobytes())
        
        return temp_filename
    
    def identify_speaker_realtime(self, metaverse_context: Dict[str, Any] = None):
        """
        실시간으로 화자 식별 수행
        
        Args:
            metaverse_context (Dict[str, Any], optional): 메타버스 환경 컨텍스트 정보
        """
        temp_audio_path = self.record_audio()
        try:
            start_time = time.time()
            
            # 서버 API를 통한 화자 식별 시도
            try:
                # 오디오 파일을 바이트로 로드
                audio_data = self.server_api.load_audio_file(temp_audio_path)
                
                # 서버에 화자 식별 요청
                response = self.server_api.identify_speaker(
                    audio_data, 
                    context=metaverse_context,
                    threshold=self.threshold
                )
                
                # 응답 처리
                processing_time = time.time() - start_time
                speaker_id = response.get("anonymousId")
                similarity = response.get("confidence", 0.0)
                encounters = response.get("encounters", 0)
                
                if speaker_id:
                    print(f"\n화자 식별 결과: {speaker_id} (유사도: {similarity:.4f}, 이전 만남: {encounters}회)")
                else:
                    print(f"\n알 수 없는 화자입니다. (최대 유사도: {similarity:.4f})")
                
                print(f"총 소요 시간: {processing_time:.2f}초 (서버 처리: {response.get('processingTime', 0.0):.2f}초)")
                
            except Exception as e:
                print(f"서버 API 호출 실패: {e}")
                
                # 로컬 폴백 사용
                if self.use_local_fallback and self.local_model:
                    print("로컬 모델로 폴백합니다...")
                    speaker_id, similarity = self.local_model.identify_speaker(
                        temp_audio_path, 
                        threshold=self.threshold
                    )
                    
                    if speaker_id:
                        print(f"\n화자 식별 결과 (로컬): {speaker_id} (유사도: {similarity:.4f})")
                    else:
                        print(f"\n알 수 없는 화자입니다. (최대 유사도: {similarity:.4f})")
                    
                    print(f"식별 소요 시간 (로컬): {time.time() - start_time:.2f}초")
                else:
                    print("화자 식별에 실패했습니다.")
                
        finally:
            # 임시 파일 삭제
            os.remove(temp_audio_path)
    
    def register_speaker_realtime(self, speaker_id: str, metadata: Dict[str, Any] = None):
        """
        실시간 녹음을 통해 새 화자 등록
        
        Args:
            speaker_id (str): 등록할 화자 ID
            metadata (Dict[str, Any], optional): 추가 메타데이터
        """
        print(f"\n{speaker_id} 화자의 음성을 {self.duration}초 동안 녹음합니다...")
        temp_audio_path = self.record_audio()
        
        try:
            start_time = time.time()
            
            # 서버 API를 통한 화자 등록 시도
            try:
                # 오디오 파일을 바이트로 로드
                audio_data = self.server_api.load_audio_file(temp_audio_path)
                
                # 서버에 화자 등록 요청
                response = self.server_api.register_speaker(
                    speaker_id,
                    audio_data,
                    metadata=metadata
                )
                
                # 응답 처리
                if response.get("status") == "success":
                    print(f"{speaker_id} 화자가 성공적으로 등록되었습니다!")
                    print(f"처리 시간: {time.time() - start_time:.2f}초 (서버 처리: {response.get('processingTime', 0.0):.2f}초)")
                else:
                    print(f"화자 등록 실패: {response.get('error', '알 수 없는 오류')}")
                
            except Exception as e:
                print(f"서버 API 호출 실패: {e}")
                
                # 로컬 폴백 사용
                if self.use_local_fallback and self.local_model:
                    print("로컬 모델로 폴백합니다...")
                    self.local_model.register_speaker(
                        speaker_id,
                        temp_audio_path,
                        save_immediately=True
                    )
                    print(f"{speaker_id} 화자가 성공적으로 등록되었습니다! (로컬)")
                    print(f"처리 시간 (로컬): {time.time() - start_time:.2f}초")
                else:
                    print("화자 등록에 실패했습니다.")
                
        finally:
            # 임시 파일 삭제
            os.remove(temp_audio_path)

    def get_speaker_info(self, speaker_id: str) -> Optional[Dict[str, Any]]:
        """
        화자 정보 조회
        
        Args:
            speaker_id (str): 조회할 화자 ID
            
        Returns:
            Optional[Dict[str, Any]]: 화자 정보 또는 None (조회 실패 시)
        """
        try:
            return self.server_api.get_speaker_info(speaker_id)
        except Exception as e:
            print(f"화자 정보 조회 실패: {e}")
            return None

    def list_speakers(self, limit: int = 10) -> Optional[Dict[str, Any]]:
        """
        등록된 화자 목록 조회
        
        Args:
            limit (int): 최대 조회 수
            
        Returns:
            Optional[Dict[str, Any]]: 화자 목록 정보 또는 None (조회 실패 시)
        """
        try:
            response = self.server_api.list_speakers(limit=limit, offset=0)
            
            if 'speakers' in response:
                print(f"\n등록된 화자 목록 ({response.get('total', 0)}명 중 {len(response['speakers'])}명):")
                for i, speaker in enumerate(response['speakers'], 1):
                    print(f"{i}. ID: {speaker['anonymousId']}, 오디오 수: {speaker['audioCount']}")
                
            return response
        except Exception as e:
            print(f"화자 목록 조회 실패: {e}")
            return None
    
    def delete_speaker(self, speaker_id: str) -> bool:
        """
        화자 삭제
        
        Args:
            speaker_id (str): 삭제할 화자 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            response = self.server_api.delete_speaker(speaker_id)
            
            if response.get('status') == 'success':
                print(f"{speaker_id} 화자가 삭제되었습니다.")
                return True
            else:
                print(f"화자 삭제 실패: {response.get('error', '알 수 없는 오류')}")
                return False
        except Exception as e:
            print(f"화자 삭제 API 호출 실패: {e}")
            
            # 로컬 폴백 시도
            if self.use_local_fallback and self.local_model:
                try:
                    if speaker_id in self.local_model.speaker_embeddings:
                        del self.local_model.speaker_embeddings[speaker_id]
                        self.local_model.save_embeddings()
                        print(f"{speaker_id} 화자가 로컬에서 삭제되었습니다.")
                        return True
                except Exception as local_e:
                    print(f"로컬 화자 삭제 실패: {local_e}")
            
            return False

    def interactive_mode(self):
        """대화형 모드로 실행"""
        print("\n===== 실시간 화자 인식 시스템 =====")
        print("1: 화자 식별")
        print("2: 새 화자 등록")
        print("3: 화자 목록 조회")
        print("4: 화자 삭제")
        print("5: 서버 연결 테스트")
        print("9: 종료")
        
        while True:
            try:
                choice = input("\n원하는 작업을 선택하세요 (1-9): ").strip()
                
                if choice == '1':
                    # 메타버스 컨텍스트 정보 수집 (예시)
                    context = {
                        "spaceId": "virtual-plaza-123",
                        "timestamp": time.time(),
                        "nearbyUsers": 5,
                        "environmentType": "conference"
                    }
                    self.identify_speaker_realtime(metaverse_context=context)
                
                elif choice == '2':
                    speaker_id = input("등록할 화자 ID를 입력하세요 (빈 값은 자동 생성): ").strip()
                    if not speaker_id:
                        speaker_id = f"user_{uuid.uuid4().hex[:8]}"
                        print(f"자동 생성된 ID: {speaker_id}")
                    
                    # 추가 메타데이터 수집
                    use_metadata = input("메타데이터를 추가하시겠습니까? (y/n): ").strip().lower() == 'y'
                    metadata = {}
                    
                    if use_metadata:
                        metadata["nickname"] = input("별명 (선택): ").strip()
                        metadata["notes"] = input("메모 (선택): ").strip()
                        metadata["registrationDevice"] = "microphone"
                        metadata["timestamp"] = time.time()
                    
                    self.register_speaker_realtime(speaker_id, metadata=metadata)
                
                elif choice == '3':
                    limit = input("조회할 최대 화자 수를 입력하세요 (기본값: 10): ").strip()
                    try:
                        limit = int(limit) if limit else 10
                    except ValueError:
                        limit = 10
                    
                    self.list_speakers(limit=limit)
                
                elif choice == '4':
                    speaker_id = input("삭제할 화자 ID를 입력하세요: ").strip()
                    if speaker_id:
                        confirm = input(f"{speaker_id} 화자를 삭제하시겠습니까? (y/n): ").strip().lower()
                        if confirm == 'y':
                            self.delete_speaker(speaker_id)
                    else:
                        print("유효한 화자 ID를 입력해주세요.")
                
                elif choice == '5':
                    if self._test_server_connection():
                        print("서버 연결 성공: 온라인 화자 인식 시스템이 활성화되었습니다.")
                    else:
                        print("서버 연결 실패!")
                        
                        if not self.local_model and self.use_local_fallback:
                            print("로컬 폴백 모델을 초기화합니다...")
                            self._init_local_model()
                
                elif choice == '9':
                    print("프로그램을 종료합니다.")
                    break
                
                else:
                    print("잘못된 입력입니다. 1, 2, 3, 4, 5, 9 중에서 선택해주세요.")
            
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                break
            
            except Exception as e:
                print(f"오류 발생: {e}")


if __name__ == "__main__":
    import os
    
    # 서버 URL과 API 키 설정 (환경 변수에서 로드하거나 기본값 사용)
    server_url = os.environ.get("SPEAKER_SERVER_URL", "http://localhost:8000")
    api_key = os.environ.get("SPEAKER_API_KEY", "test_api_key_1234")
    
    # 실시간 화자 인식 시스템 초기화 및 실행
    realtime_sr = RealtimeSpeakerRecognition(
        server_url=server_url,
        api_key=api_key,
        duration=5,  # 5초 녹음
        threshold=0.7,  # 유사도 임계값
        use_local_fallback=True  # 서버 연결 실패 시 로컬 모델 사용
    )
    
    # 대화형 모드 실행
    realtime_sr.interactive_mode()