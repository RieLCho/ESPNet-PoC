FROM espnet/espnet:gpu-latest

WORKDIR /app
COPY requirements.txt .
COPY src/ ./src/
COPY models/ ./models/

RUN pip install --no-cache-dir -r requirements.txt

# 일본어 처리를 위한 추가 패키지 설치
RUN apt-get update && \
    apt-get install -y mecab mecab-ipadic-utf8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 기본 실행 명령
ENTRYPOINT ["python", "src/demo.py"] 