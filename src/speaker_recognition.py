import torch
import torchaudio
import numpy as np
from pathlib import Path
from espnet2.bin.asr_inference import Speech2Text
from sklearn.metrics.pairwise import cosine_similarity

class SpeakerRecognition:
    def __init__(self, asr_model_path):
        """
        화자 인식 시스템 초기화
        Args:
            asr_model_path (str): ESPnet ASR 모델 경로
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.speech2text = Speech2Text.from_pretrained(
            "espnet/kan-bayashi_csj_asr_train_asr_transformer_raw_char_sp_valid.acc.ave",
            device=self.device
        )
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

    def register_speaker(self, speaker_id, audio_path):
        """
        새로운 화자 등록
        Args:
            speaker_id (str): 화자 ID
            audio_path (str): 화자의 음성 파일 경로
        """
        embedding = self.extract_speaker_embedding(audio_path)
        self.speaker_embeddings[speaker_id] = embedding
        
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
        
        max_similarity = -1
        best_speaker_id = None
        
        for speaker_id, stored_embedding in self.speaker_embeddings.items():
            similarity = cosine_similarity(
                test_embedding.reshape(1, -1),
                stored_embedding.reshape(1, -1)
            )[0][0]
            
            if similarity > max_similarity:
                max_similarity = similarity
                best_speaker_id = speaker_id
        
        if max_similarity < threshold:
            return None, max_similarity
            
        return best_speaker_id, max_similarity 