#!/bin/bash

##################################################
# 모든 트레이딩 전략 동시 실행 설정 스크립트
# Setup script for running all trading strategies
##################################################

set -e

echo "=================================================="
echo "🚀 모든 트레이딩 전략 동시 실행 설정"
echo "=================================================="
echo ""

# 현재 디렉토리 확인
if [ ! -f "main.py" ]; then
    echo "❌ 오류: python_program_trade 디렉토리에서 실행하세요"
    exit 1
fi

echo "📋 설치할 전략:"
echo "   1. 듀얼 모멘텀 + 변동성 돌파 (trading-bot)"
echo "   2. 이동평균선 전략 (trading-bot-ma)"
echo "   3. AI 전략 (trading-bot-ai)"
echo "   4. 화장품 업종 전략 (trading-bot-cosmetics)"
echo ""

# 기존 서비스 중지
echo "⏸️  기존 서비스 중지 중..."
sudo systemctl stop trading-bot 2>/dev/null || true
sudo systemctl stop trading-bot-ma 2>/dev/null || true
sudo systemctl stop trading-bot-ai 2>/dev/null || true
sudo systemctl stop trading-bot-cosmetics 2>/dev/null || true

# 서비스 파일 복사
echo "📝 서비스 파일 설치 중..."
sudo cp deploy/trading-bot.service /etc/systemd/system/
sudo cp deploy/trading-bot-ma.service /etc/systemd/system/
sudo cp deploy/trading-bot-ai.service /etc/systemd/system/
sudo cp deploy/trading-bot-cosmetics.service /etc/systemd/system/

# systemd 재로드
echo "🔄 systemd 재로드 중..."
sudo systemctl daemon-reload

# 모든 서비스 시작
echo "▶️  모든 서비스 시작 중..."
sudo systemctl start trading-bot
sudo systemctl start trading-bot-ma
sudo systemctl start trading-bot-ai
sudo systemctl start trading-bot-cosmetics

# 상태 확인
echo ""
echo "=================================================="
echo "✅ 설치 완료!"
echo "=================================================="
echo ""
echo "📊 서비스 상태:"
echo ""

for service in trading-bot trading-bot-ma trading-bot-ai trading-bot-cosmetics; do
    status=$(sudo systemctl is-active $service)
    if [ "$status" = "active" ]; then
        echo "   ✅ $service: 실행 중"
    else
        echo "   ❌ $service: 중지됨"
    fi
done

echo ""
echo "📋 유용한 명령어:"
echo "   전체 상태 확인: sudo systemctl status trading-bot*"
echo "   듀얼 모멘텀 로그: sudo journalctl -u trading-bot -f"
echo "   이동평균선 로그: sudo journalctl -u trading-bot-ma -f"
echo "   AI 전략 로그: sudo journalctl -u trading-bot-ai -f"
echo "   화장품 전략 로그: sudo journalctl -u trading-bot-cosmetics -f"
echo ""
echo "   전체 중지: sudo systemctl stop trading-bot*"
echo "   전체 시작: sudo systemctl start trading-bot trading-bot-ma trading-bot-ai trading-bot-cosmetics"
echo ""
echo "💰 리소스 사용량:"
echo "   각 전략: 메모리 200MB, CPU 20%"
echo "   전체: 메모리 ~800MB (t3.micro 1GB 내)"
echo ""
