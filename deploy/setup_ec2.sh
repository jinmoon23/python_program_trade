#!/bin/bash
# AWS EC2 t2.micro 자동 설치 스크립트
# EC2 Setup Script for KIS Trading Bot

set -e  # 에러 발생 시 중단

echo "=================================================="
echo "🚀 KIS Trading Bot - EC2 자동 설치"
echo "=================================================="
echo ""

# 1. 시스템 업데이트
echo "📦 시스템 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# 2. 필수 패키지 설치
echo "📦 필수 패키지 설치 중..."
sudo apt install -y python3.11 python3.11-venv python3-pip git curl htop

# 3. 프로젝트 디렉토리로 이동 (이미 클론되어 있다고 가정)
cd /home/ubuntu/python_program_trade

# 4. 가상환경 생성
echo "🐍 Python 가상환경 생성 중..."
python3.11 -m venv venv

# 5. 의존성 설치
echo "📦 Python 패키지 설치 중..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. 로그 디렉토리 생성
echo "📁 로그 디렉토리 생성 중..."
mkdir -p logs

# 7. .env 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다!"
    echo "   로컬에서 .env 파일을 업로드해주세요:"
    echo "   scp -i your-key.pem .env ubuntu@your-ec2-ip:/home/ubuntu/python_program_trade/"
    exit 1
fi

# 8. .env 파일 권한 설정
chmod 600 .env

# 9. systemd 서비스 설치
echo "⚙️  systemd 서비스 설치 중..."
sudo cp deploy/trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trading-bot

# 10. cron 작업 설정 (매일 08:50 재시작)
echo "⏰ cron 작업 설정 중..."
(crontab -l 2>/dev/null; echo "50 8 * * 1-5 sudo systemctl restart trading-bot") | crontab -

# 11. 방화벽 설정 (SSH만 허용)
echo "🔒 방화벽 설정 중..."
sudo ufw --force enable
sudo ufw allow 22/tcp
sudo ufw status

# 12. 서비스 시작
echo "🚀 Trading Bot 서비스 시작 중..."
sudo systemctl start trading-bot

# 13. 상태 확인
echo ""
echo "=================================================="
echo "✅ 설치 완료!"
echo "=================================================="
echo ""
echo "📊 서비스 상태 확인:"
sudo systemctl status trading-bot --no-pager

echo ""
echo "📋 유용한 명령어:"
echo "   서비스 상태: sudo systemctl status trading-bot"
echo "   로그 확인: sudo journalctl -u trading-bot -f"
echo "   서비스 재시작: sudo systemctl restart trading-bot"
echo "   서비스 중지: sudo systemctl stop trading-bot"
echo ""
echo "📁 로그 파일 위치:"
echo "   /home/ubuntu/python_program_trade/logs/bot.log"
echo "   /home/ubuntu/python_program_trade/logs/bot_error.log"
echo ""
