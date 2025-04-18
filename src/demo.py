from speaker_recognition import SpeakerRecognition
import argparse
from pathlib import Path
import os

def main():
    parser = argparse.ArgumentParser(description="화자 인식 시스템 데모")
    parser.add_argument("--register_audio", help="등록할 화자의 음성 파일 경로")
    parser.add_argument("--speaker_id", help="등록할 화자 ID")
    parser.add_argument("--test_audio", help="테스트할 음성 파일 경로")
    parser.add_argument("--register_dir", help="폴더 내 모든 화자 음성을 등록 (폴더명이 화자 ID로 사용됨)")
    parser.add_argument("--embeddings_file", default="speaker_embeddings.pkl", help="화자 임베딩 저장 파일")
    
    args = parser.parse_args()
    
    # 화자 인식 시스템 초기화
    speaker_recognition = SpeakerRecognition(embeddings_file=args.embeddings_file)
    
    # 폴더 내 모든 화자 음성 등록
    if args.register_dir:
        register_directory(speaker_recognition, args.register_dir)
    
    # 단일 화자 등록
    elif args.register_audio and args.speaker_id:
        print(f"화자 등록 중: {args.speaker_id} (파일: {args.register_audio})")
        speaker_recognition.register_speaker(args.speaker_id, args.register_audio)
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

def register_directory(speaker_recognition, directory_path):
    """폴더 내 모든 화자 음성 등록 (폴더명이 화자 ID로 사용)"""
    base_dir = Path(directory_path)
    if not base_dir.exists():
        print(f"오류: 폴더가 존재하지 않습니다: {directory_path}")
        return
    
    count = 0
    registered_files_count = 0
    
    # 폴더 내의 모든 하위 폴더를 화자 ID로 사용
    for speaker_dir in base_dir.iterdir():
        if not speaker_dir.is_dir():
            continue
        
        speaker_id = speaker_dir.name
        audio_files = list(speaker_dir.glob('*.wav'))
        
        if not audio_files:
            print(f"경고: {speaker_id} 폴더에 WAV 파일이 없습니다.")
            continue
        
        # 폴더 내 모든 오디오 파일 등록
        print(f"화자 등록 중: {speaker_id} ({len(audio_files)}개 파일)")
        for audio_file in audio_files:
            print(f"  - 파일 등록 중: {audio_file.name}")
            speaker_recognition.register_speaker(speaker_id, str(audio_file))
            registered_files_count += 1
        
        count += 1
    
    print(f"총 {count}명의 화자가 등록되었습니다. (총 {registered_files_count}개 파일)")

if __name__ == "__main__":
    main()