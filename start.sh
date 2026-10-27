#!/bin/bash
# 트릿지 성과보고서 자동화 시스템 실행 스크립트

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================================="
echo "🚀 트릿지(Tridge) 성과보고서 자동화 시스템을 시작합니다..."
echo "=========================================================="

if [ ! -d "venv" ]; then
    echo "가상환경(venv)을 찾을 수 없습니다. 설치를 진행합니다."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

echo "웹 대시보드 서버를 구동 중입니다: http://127.0.0.1:8000"
echo "브라우저에서 위 주소로 접속해 주세요. 종료하려면 Ctrl+C를 누르세요."
echo "=========================================================="

./venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
