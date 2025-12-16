#!/bin/bash
# 장중에만 실행되도록 스케줄 설정 (프리티어 최적화)
# Setup market hours only schedule (Free tier optimization)

set -e

echo "=================================================="
echo "⏰ 장중 스케줄 설정 (프리티어 최적화)"
echo "=================================================="
echo ""
echo "📊 예상 사용량:"
echo "   평일 09:00-15:30 (6.5시간/일)"
echo "   월 약 130시간 (프리티어 750시간 중 17%만 사용)"
echo "   ✅ 620시간 절약!"
echo ""

# 1. systemd 서비스 설치
echo "⚙️  systemd 서비스 설치 중..."
sudo cp /home/ubuntu/python_program_trade/deploy/trading-bot-scheduled.service /etc/systemd/system/trading-bot.service
sudo systemctl daemon-reload

# 2. 부팅 시 자동 시작 비활성화 (cron으로 제어)
sudo systemctl disable trading-bot

# 3. cron 작업 설정
echo "⏰ cron 작업 설정 중..."

# 기존 trading-bot 관련 cron 제거
crontab -l 2>/dev/null | grep -v trading-bot | crontab - 2>/dev/null || true

# 새로운 cron 작업 추가
(crontab -l 2>/dev/null; cat << 'EOF'
# KIS Trading Bot - 장중에만 실행 (월~금)
# 08:50 시작 (장 시작 10분 전)
50 8 * * 1-5 sudo systemctl start trading-bot

# 15:35 중지 (장 마감 5분 후)
35 15 * * 1-5 sudo systemctl stop trading-bot

# 주말 안전 중지 (토요일 00:00)
0 0 * * 6 sudo systemctl stop trading-bot
EOF
) | crontab -

echo ""
echo "=================================================="
echo "✅ 스케줄 설정 완료!"
echo "=================================================="
echo ""
echo "📅 실행 스케줄:"
echo "   월~금: 08:50 시작 → 15:35 중지"
echo "   토~일: 중지"
echo ""
echo "💰 비용 절감:"
echo "   24/7 실행: 월 720시간"
echo "   장중만 실행: 월 130시간"
echo "   절감: 590시간 (82%)"
echo ""
echo "📋 cron 작업 확인:"
crontab -l | grep trading-bot
echo ""
echo "🔍 현재 서비스 상태:"
sudo systemctl status trading-bot --no-pager || echo "   (아직 시작 전 - 내일 08:50에 자동 시작됩니다)"
echo ""
echo "📝 유용한 명령어:"
echo "   수동 시작: sudo systemctl start trading-bot"
echo "   수동 중지: sudo systemctl stop trading-bot"
echo "   상태 확인: sudo systemctl status trading-bot"
echo "   로그 확인: sudo journalctl -u trading-bot -f"
echo ""
