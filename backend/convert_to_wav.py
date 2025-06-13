#!/usr/bin/env python3
import os
import subprocess
import argparse
from pathlib import Path
from tqdm import tqdm

def convert_video_to_wav(input_dir, output_dir, sample_rate=16000):
    """
    input_dir 내의 모든 비디오 파일을 WAV 오디오 파일로 변환합니다.
    
    Args:
        input_dir (str): 입력 비디오 파일이 있는 디렉토리 경로
        output_dir (str): 출력 WAV 파일을 저장할 디렉토리 경로
        sample_rate (int): 출력 WAV 파일의 샘플링 레이트 (Hz)
    """
    # 입력 디렉토리 확인
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print(f"오류: 입력 디렉토리가 존재하지 않습니다: {input_dir}")
        return False
    
    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 비디오 파일 찾기 (mp4, mkv, avi 등 다양한 형식 지원)
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(list(input_path.glob(f'*{ext}')))
    
    if not video_files:
        print(f"오류: {input_dir}에 비디오 파일이 없습니다")
        return False
    
    print(f"총 {len(video_files)}개의 비디오 파일을 발견했습니다.")
    
    # 각 비디오 파일을 WAV로 변환
    for i, video_file in enumerate(tqdm(video_files, desc="비디오 변환", unit="파일")):
        output_file = output_path / f"{i+1}.wav"
        
        # ffmpeg 명령 실행: 비디오에서 오디오 추출 및 16kHz로 변환
        cmd = [
            'ffmpeg',
            '-i', str(video_file),            # 입력 파일
            '-vn',                            # 비디오 스트림 제외
            '-acodec', 'pcm_s16le',           # 오디오 코덱: 16-bit PCM
            '-ar', str(sample_rate),          # 샘플링 레이트
            '-ac', '1',                       # 모노 채널
            '-y',                             # 기존 파일 덮어쓰기
            str(output_file)                  # 출력 파일
        ]
        
        try:
            # 출력 로그를 최소화하기 위해 stderr를 리디렉션
            subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
            print(f"처리 완료: {video_file.name} -> {output_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"오류: {video_file.name} 처리 중 문제 발생: {e}")
            continue
    
    print(f"변환 완료. {output_dir}에 WAV 파일이 저장되었습니다.")
    return True

def main():
    parser = argparse.ArgumentParser(description="비디오 파일을 WAV 오디오로 변환")
    parser.add_argument("--input", default="data/kazusa", help="입력 비디오 디렉토리")
    parser.add_argument("--output", default="data/kazusa_wav", help="출력 WAV 디렉토리")
    parser.add_argument("--sample-rate", type=int, default=16000, help="출력 샘플링 레이트(Hz)")
    
    args = parser.parse_args()
    
    convert_video_to_wav(args.input, args.output, args.sample_rate)

if __name__ == "__main__":
    main()