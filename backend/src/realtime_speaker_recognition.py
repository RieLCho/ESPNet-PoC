import os
import time
import wave
import numpy as np
import sounddevice as sd
from tempfile import NamedTemporaryFile
from pathlib import Path
from speaker_recognition import SpeakerRecognition

class RealtimeSpeakerRecognition:
    def __init__(self, 
                 embeddings_file="speaker_embeddings.pkl", 
                 sample_rate=16000, 
                 duration=5, 
                 threshold=0.7):
        """
        실시간 화자 인식 시스템 초기화
        
        Args:
            embeddings_file (str): 화자 임베딩 파일 경로
            sample_rate (int): 샘플링 레이트 (Hz)
            duration (int): 녹음 기간 (초)
            threshold (float): 화자 식별을 위한 유사도 임계값
        """
        # 화자 인식 모듈 초기화
        self.speaker_recognition = SpeakerRecognition(embeddings_file)
        self.sample_rate = sample_rate
        self.duration = duration
        self.threshold = threshold
        
        print(f"실시간 화자 인식 시스템이 초기화되었습니다.")
        print(f"샘플링 레이트: {sample_rate} Hz, 녹음 시간: {duration}초, 임계값: {threshold}")
    
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
    
    def identify_speaker_realtime(self):
        """실시간으로 화자 식별 수행"""
        temp_audio_path = self.record_audio()
        try:
            # 화자 식별
            start_time = time.time()
            speaker_id, similarity = self.speaker_recognition.identify_speaker(
                temp_audio_path, 
                threshold=self.threshold
            )
            
            # 결과 출력
            if speaker_id:
                print(f"\n화자 식별 결과: {speaker_id} (유사도: {similarity:.4f})")
            else:
                print(f"\n알 수 없는 화자입니다. (최대 유사도: {similarity:.4f})")
            
            print(f"식별 소요 시간: {time.time() - start_time:.2f}초")
        finally:
            # 임시 파일 삭제
            os.remove(temp_audio_path)
    
    def register_speaker_realtime(self, speaker_id):
        """
        실시간 녹음을 통해 새 화자 등록
        
        Args:
            speaker_id (str): 등록할 화자 ID
        """
        print(f"\n{speaker_id} 화자의 음성을 {self.duration}초 동안 녹음합니다...")
        temp_audio_path = self.record_audio()
        
        try:
            # 화자 등록
            self.speaker_recognition.register_speaker(
                speaker_id,
                temp_audio_path,
                save_immediately=True
            )
            print(f"{speaker_id} 화자가 성공적으로 등록되었습니다!")
        finally:
            # 임시 파일 삭제
            os.remove(temp_audio_path)

    def interactive_mode(self):
        """대화형 모드로 실행"""
        print("\n===== 실시간 화자 인식 시스템 =====")
        print("1: 화자 식별")
        print("2: 새 화자 등록")
        print("3: 종료")
        
        while True:
            try:
                choice = input("\n원하는 작업을 선택하세요 (1-3): ").strip()
                
                if choice == '1':
                    self.identify_speaker_realtime()
                elif choice == '2':
                    speaker_id = input("등록할 화자 ID를 입력하세요: ").strip()
                    if speaker_id:
                        self.register_speaker_realtime(speaker_id)
                    else:
                        print("유효한 화자 ID를 입력해주세요.")
                elif choice == '3':
                    print("프로그램을 종료합니다.")
                    break
                else:
                    print("잘못된 입력입니다. 1, 2, 3 중에서 선택해주세요.")
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                break
            except Exception as e:
                print(f"오류 발생: {e}")


if __name__ == "__main__":
    # 실시간 화자 인식 시스템 초기화 및 실행
    realtime_sr = RealtimeSpeakerRecognition(
        embeddings_file="speaker_embeddings.pkl",
        duration=5,  # 5초 녹음
        threshold=0.7  # 유사도 임계값
    )
    
    # 대화형 모드 실행
    realtime_sr.interactive_mode()