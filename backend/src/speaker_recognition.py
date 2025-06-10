import torch
import torchaudio
import numpy as np
from pathlib import Path
import pickle
import os
import time
from espnet2.bin.asr_inference import Speech2Text
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

class SpeakerRecognition:
    def __init__(self, embeddings_file="speaker_embeddings.pkl"):
        """
        화자 인식 시스템 초기화
        Args:
            embeddings_file (str): 화자 임베딩을 저장할 파일 경로
        """
        # 텐서 형식을 float32로 설정 (MPS가 float64를 지원하지 않음)
        torch.set_default_dtype(torch.float32)
        
        # MPS(M1/M2), CUDA 또는 CPU 선택
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            try:
                # MPS 디바이스가 가용한지 추가 확인
                _ = torch.zeros(1, device="mps")
                self.device = "mps"
                print("MPS(Apple Silicon) 가속기를 사용합니다.")
            except Exception as e:
                print(f"MPS 초기화 중 오류 발생: {e}")
                print("CPU로 대체합니다.")
                self.device = "cpu"
        elif torch.cuda.is_available():
            self.device = "cuda"
            print("CUDA GPU를 사용합니다.")
        else:
            self.device = "cpu"
            print("CPU를 사용합니다.")
            
        # CPU 사용 시 성능 최적화
        if self.device == "cpu":
            torch.set_num_threads(os.cpu_count())
            print(f"CPU 스레드 수를 {os.cpu_count()}로 설정했습니다.")
        
        # 모델 로딩 시간 측정
        start_time = time.time()
        print("ESPnet 모델을 로딩 중입니다...")
        
        try:
            # ESPnet 모델 로드
            self.speech2text = Speech2Text.from_pretrained(
                "espnet/kan-bayashi_csj_asr_train_asr_transformer_raw_char_sp_valid.acc.ave",
                device=self.device
            )
            print(f"모델 로딩 완료 ({time.time() - start_time:.2f}초)")
        except Exception as e:
            print(f"모델 로딩 실패: {e}")
            print("CPU로 대체하여 다시 시도합니다.")
            self.device = "cpu"
            torch.set_num_threads(os.cpu_count())
            
            try:
                self.speech2text = Speech2Text.from_pretrained(
                    "espnet/kan-bayashi_csj_asr_train_asr_transformer_raw_char_sp_valid.acc.ave",
                    device=self.device
                )
                print(f"CPU 모델 로딩 완료 ({time.time() - start_time:.2f}초)")
            except Exception as e2:
                raise RuntimeError(f"모델 로딩 실패: {e2}")
        
        self.embeddings_file = embeddings_file
        self._save_pending = False  # 저장 필요 여부를 추적하는 플래그
        
        # 저장된 임베딩이 있으면 로드
        if os.path.exists(embeddings_file):
            self.load_embeddings()
        else:
            self.speaker_embeddings = {}

    def extract_speaker_embedding(self, audio_path):
        """
        오디오 파일에서 화자 임베딩 추출
        Args:
            audio_path (str): 오디오 파일 경로
        Returns:
            numpy.ndarray: 화자 임베딩 벡터
        """
        waveform, sample_rate = torchaudio.load(audio_path)
        if sample_rate != 16000:
            waveform = torchaudio.transforms.Resample(sample_rate, 16000)(waveform)
        
        speech = waveform.squeeze().numpy()
        
        # with torch.no_grad() 추가로 메모리 사용 최적화
        with torch.no_grad():
            nbests = self.speech2text(speech)
            
        embedding = nbests[0][2]  # 화자 임베딩 추출
        return embedding

    def extract_speaker_embeddings_batch(self, audio_paths):
        """
        여러 오디오 파일에서 화자 임베딩 추출 (배치 처리)
        Args:
            audio_paths (list): 오디오 파일 경로 리스트
        Returns:
            list: 화자 임베딩 벡터 리스트
        """
        embeddings = []
        # tqdm을 사용하여 진행 상황 표시
        for audio_path in tqdm(audio_paths, desc="임베딩 추출", unit="파일"):
            embedding = self.extract_speaker_embedding(audio_path)
            embeddings.append(embedding)
        return embeddings

    def save_embeddings(self):
        """화자 임베딩을 파일에 저장"""
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump(self.speaker_embeddings, f)
        print(f"임베딩 저장됨: {self.embeddings_file}")
        self._save_pending = False
    
    def load_embeddings(self):
        """파일에서 화자 임베딩 로드"""
        try:
            start_time = time.time()
            with open(self.embeddings_file, 'rb') as f:
                self.speaker_embeddings = pickle.load(f)
            
            # 이전 포맷과의 호환성 유지: 단일 임베딩을 리스트로 변환
            for speaker_id, embeddings in self.speaker_embeddings.items():
                if not isinstance(embeddings, list):
                    self.speaker_embeddings[speaker_id] = [embeddings]
                    
            print(f"임베딩 로드됨: {self.embeddings_file} ({len(self.speaker_embeddings)}명의 화자, {time.time() - start_time:.2f}초)")
        except Exception as e:
            print(f"임베딩 로드 실패: {e}")
            self.speaker_embeddings = {}

    def register_speaker(self, speaker_id, audio_path, save_immediately=False):
        """
        화자 등록 또는 추가 음성 등록
        Args:
            speaker_id (str): 화자 ID
            audio_path (str): 화자의 음성 파일 경로
            save_immediately (bool): 즉시 저장 여부
        """
        embedding = self.extract_speaker_embedding(audio_path)
        
        # 새로운 화자면 리스트 생성, 기존 화자면 임베딩 추가
        if speaker_id not in self.speaker_embeddings:
            self.speaker_embeddings[speaker_id] = [embedding]
        else:
            self.speaker_embeddings[speaker_id].append(embedding)
        
        # 저장 플래그 설정
        self._save_pending = True
        
        # 즉시 저장 요청이 있을 경우에만 저장
        if save_immediately:
            self.save_embeddings()
    
    def register_speakers_batch(self, speaker_data):
        """
        여러 화자/오디오 파일 일괄 등록
        Args:
            speaker_data (list): (speaker_id, audio_path) 튜플의 리스트
        """
        # tqdm을 사용하여 진행 상황 표시
        for speaker_id, audio_path in tqdm(speaker_data, desc="화자 등록", unit="파일"):
            self.register_speaker(speaker_id, audio_path, save_immediately=False)
        
        # 모든 등록 완료 후 한 번만 저장
        if self._save_pending:
            self.save_embeddings()
        
    def identify_speaker(self, audio_path, threshold=0.7):
        """
        입력된 음성의 화자 식별
        Args:
            audio_path (str): 식별할 음성 파일 경로
            threshold (float): 유사도 임계값
        Returns:
            tuple: (가장 유사한 화자 ID, 유사도 점수)
        """
        start_time = time.time()
        test_embedding = self.extract_speaker_embedding(audio_path)
        print(f"임베딩 추출 시간: {time.time() - start_time:.2f}초")
        
        # 리스트인 경우 NumPy 배열로 변환
        if isinstance(test_embedding, list):
            test_embedding = np.array(test_embedding)
        
        start_time = time.time()
        max_similarity = -1
        best_speaker_id = None
        
        if not self.speaker_embeddings:
            return None, -1  # 등록된 화자가 없음
        
        for speaker_id, speaker_embeddings in self.speaker_embeddings.items():
            # 각 화자의 모든 임베딩과 비교하여 최대 유사도 찾기
            speaker_max_similarity = -1
            
            for stored_embedding in speaker_embeddings:
                # 저장된 임베딩도 리스트인 경우 NumPy 배열로 변환
                if isinstance(stored_embedding, list):
                    stored_embedding = np.array(stored_embedding)
                
                # 임베딩 차원 맞추기 - 더 작은 차원으로 맞춤
                min_dim = min(test_embedding.shape[0], stored_embedding.shape[0])
                test_embedding_resized = test_embedding[:min_dim]
                stored_embedding_resized = stored_embedding[:min_dim]
                
                similarity = cosine_similarity(
                    test_embedding_resized.reshape(1, -1),
                    stored_embedding_resized.reshape(1, -1)
                )[0][0]
                
                # 화자별 최대 유사도 업데이트
                if similarity > speaker_max_similarity:
                    speaker_max_similarity = similarity
            
            # 전체 최대 유사도 업데이트
            if speaker_max_similarity > max_similarity:
                max_similarity = speaker_max_similarity
                best_speaker_id = speaker_id
        
        print(f"유사도 계산 시간: {time.time() - start_time:.2f}초")
        
        if max_similarity < threshold:
            return None, max_similarity
            
        return best_speaker_id, max_similarity