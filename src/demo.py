from speaker_recognition import SpeakerRecognition
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="화자 인식 시스템 데모")
    parser.add_argument("--model_path", required=True, help="ESPnet ASR 모델 경로")
    parser.add_argument("--register_audio", help="등록할 화자의 음성 파일 경로")
    parser.add_argument("--speaker_id", help="등록할 화자 ID")
    parser.add_argument("--test_audio", help="테스트할 음성 파일 경로")
    
    args = parser.parse_args()
    
    # 화자 인식 시스템 초기화
    speaker_recognition = SpeakerRecognition(args.model_path)
    
    # 화자 등록
    if args.register_audio and args.speaker_id:
        print(f"화자 등록 중: {args.speaker_id}")
        speaker_recognition.register_speaker(args.speaker_id, args.register_audio)
        print("화자 등록 완료")
    
    # 화자 식별
    if args.test_audio:
        print(f"음성 파일 분석 중: {args.test_audio}")
        speaker_id, similarity = speaker_recognition.identify_speaker(args.test_audio)
        
        if speaker_id:
            print(f"식별된 화자: {speaker_id} (유사도: {similarity:.4f})")
        else:
            print(f"알 수 없는 화자 (유사도: {similarity:.4f})")

if __name__ == "__main__":
    main() 