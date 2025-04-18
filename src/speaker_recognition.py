import torch
import torchaudio
import numpy as np
from pathlib import Path
import pickle
import os
from espnet2.bin.asr_inference import Speech2Text
from sklearn.metrics.pairwise import cosine_similarity

class SpeakerRecognition:
    def __init__(self, embeddings_file="speaker_embeddings.pkl"):
        """
        화자 인식 시스템 초기화
        Args:
            embeddings_file (str): 화자 임베딩을 저장할 파일 경로
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.speech2text = Speech2Text.from_pretrained(
            "espnet/kan-bayashi_csj_asr_train_asr_transformer_raw_char_sp_valid.acc.ave",
            device=self.device
        )
        self.embeddings_file = embeddings_file
        
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
        nbests = self.speech2text(speech)
        embedding = nbests[0][2]  # 화자 임베딩 추출
        return embedding

    def save_embeddings(self):
        """화자 임베딩을 파일에 저장"""
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump(self.speaker_embeddings, f)
        print(f"임베딩 저장됨: {self.embeddings_file}")
    
    def load_embeddings(self):
        """파일에서 화자 임베딩 로드"""
        try:
            with open(self.embeddings_file, 'rb') as f:
                self.speaker_embeddings = pickle.load(f)
            
            # 이전 포맷과의 호환성 유지: 단일 임베딩을 리스트로 변환
            for speaker_id, embeddings in self.speaker_embeddings.items():
                if not isinstance(embeddings, list):
                    self.speaker_embeddings[speaker_id] = [embeddings]
                    
            print(f"임베딩 로드됨: {self.embeddings_file} ({len(self.speaker_embeddings)}명의 화자)")
        except Exception as e:
            print(f"임베딩 로드 실패: {e}")
            self.speaker_embeddings = {}

    def register_speaker(self, speaker_id, audio_path):
        """
        화자 등록 또는 추가 음성 등록
        Args:
            speaker_id (str): 화자 ID
            audio_path (str): 화자의 음성 파일 경로
        """
        embedding = self.extract_speaker_embedding(audio_path)
        
        # 새로운 화자면 리스트 생성, 기존 화자면 임베딩 추가
        if speaker_id not in self.speaker_embeddings:
            self.speaker_embeddings[speaker_id] = [embedding]
        else:
            self.speaker_embeddings[speaker_id].append(embedding)
        
        self.save_embeddings()  # 임베딩 저장
        
    def identify_speaker(self, audio_path, threshold=0.7):
        """
        입력된 음성의 화자 식별
        Args:
            audio_path (str): 식별할 음성 파일 경로
            threshold (float): 유사도 임계값
        Returns:
            tuple: (가장 유사한 화자 ID, 유사도 점수)
        """
        test_embedding = self.extract_speaker_embedding(audio_path)
        
        # 리스트인 경우 NumPy 배열로 변환
        if isinstance(test_embedding, list):
            test_embedding = np.array(test_embedding)
        
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
        
        if max_similarity < threshold:
            return None, max_similarity
            
        return best_speaker_id, max_similarity