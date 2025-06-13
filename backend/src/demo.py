from speaker_recognition import SpeakerRecognition
import argparse
from pathlib import Path
import os
import time
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser(description="화자 인식 시스템 데모")
    parser.add_argument("--register_audio", help="등록할 화자의 음성 파일 경로")
    parser.add_argument("--speaker_id", help="등록할 화자 ID")
    parser.add_argument("--test_audio", help="테스트할 음성 파일 경로")
    parser.add_argument("--register_dir", help="폴더 내 모든 화자 음성을 등록 (폴더명이 화자 ID로 사용됨)")
    parser.add_argument("--embeddings_file", default="speaker_embeddings.pkl", help="화자 임베딩 저장 파일")
    parser.add_argument("--batch_size", type=int, default=10, help="배치 처리 크기")
    
    args = parser.parse_args()
    
    total_start_time = time.time()
    
    # 화자 인식 시스템 초기화
    speaker_recognition = SpeakerRecognition(embeddings_file=args.embeddings_file)
    
    # 폴더 내 모든 화자 음성 등록
    if args.register_dir:
        register_directory(speaker_recognition, args.register_dir, batch_size=args.batch_size)
    
    # 단일 화자 등록
    elif args.register_audio and args.speaker_id:
        print(f"화자 등록 중: {args.speaker_id} (파일: {args.register_audio})")
        speaker_recognition.register_speaker(args.speaker_id, args.register_audio, save_immediately=True)
        print("화자 등록 완료")
    
    # 화자 식별
    if args.test_audio:
        print(f"음성 파일 분석 중: {args.test_audio}")
        
        if not speaker_recognition.speaker_embeddings:
            print("경고: 등록된 화자가 없습니다. 먼저 화자를 등록해주세요.")
            print("사용법: python src/demo.py --register_audio [오디오 파일] --speaker_id [화자 ID]")
            print("또는: python src/demo.py --register_dir [폴더 경로]")
            return
            
        speaker_id, similarity = speaker_recognition.identify_speaker(args.test_audio)
        
        if speaker_id:
            print(f"식별된 화자: {speaker_id} (유사도: {similarity:.4f})")
        else:
            print(f"알 수 없는 화자 (유사도: {similarity:.4f})")
    
    print(f"총 실행 시간: {time.time() - total_start_time:.2f}초")

def register_directory(speaker_recognition, directory_path, batch_size=10):
    """폴더 내 모든 화자 음성 등록 (폴더명이 화자 ID로 사용)"""
    base_dir = Path(directory_path)
    if not base_dir.exists():
        print(f"오류: 폴더가 존재하지 않습니다: {directory_path}")
        return
    
    count = 0
    registered_files_count = 0
    start_time = time.time()
    
    # 폴더 내의 모든 하위 폴더 목록 먼저 수집
    speaker_dirs = [d for d in base_dir.iterdir() if d.is_dir()]
    print(f"총 {len(speaker_dirs)}개의 화자 폴더를 발견했습니다.")
    
    # 폴더 내의 모든 하위 폴더를 화자 ID로 사용
    for speaker_dir in tqdm(speaker_dirs, desc="화자 폴더 처리", unit="폴더"):
        speaker_id = speaker_dir.name
        audio_files = list(speaker_dir.glob('*.wav'))
        
        if not audio_files:
            print(f"경고: {speaker_id} 폴더에 WAV 파일이 없습니다.")
            continue
        
        print(f"화자 등록 중: {speaker_id} ({len(audio_files)}개 파일)")
        
        # 배치 처리를 위한 준비
        batch_data = []
        
        for audio_file in audio_files:
            batch_data.append((speaker_id, str(audio_file)))
            registered_files_count += 1
            
            # 배치 크기에 도달하거나 마지막 파일인 경우 처리
            if len(batch_data) >= batch_size or audio_file == audio_files[-1]:
                batch_start_time = time.time()
                speaker_recognition.register_speakers_batch(batch_data)
                print(f"  배치 처리 완료 ({len(batch_data)}개 파일, {time.time() - batch_start_time:.2f}초)")
                batch_data = []  # 배치 초기화
        
        count += 1
    
    print(f"총 {count}명의 화자가 등록되었습니다. (총 {registered_files_count}개 파일)")
    print(f"등록 총 소요 시간: {time.time() - start_time:.2f}초")

if __name__ == "__main__":
    main()