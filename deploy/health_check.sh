#!/bin/bash
# 헬스 체크 스크립트
# Health Check Script for Trading Bot

echo "=================================================="
echo "🏥 Trading Bot 헬스 체크"
echo "=================================================="
echo ""

# 1. 서비스 상태
echo "📊 서비스 상태:"
sudo systemctl is-active trading-bot
if [ $? -eq 0 ]; then
    echo "   ✅ 서비스 실행 중"
else
    echo "   ❌ 서비스 중지됨"
fi
echo ""

# 2. 프로세스 확인
echo "🔍 프로세스 확인:"
ps aux | grep "python main.py" | grep -v grep
echo ""

# 3. 메모리 사용량
echo "💾 메모리 사용량:"
free -h
echo ""

# 4. 디스크 사용량
echo "💿 디스크 사용량:"
df -h /home/ubuntu
echo ""

# 5. 최근 로그 (마지막 10줄)
echo "📋 최근 로그 (마지막 10줄):"
sudo journalctl -u trading-bot -n 10 --no-pager
echo ""

# 6. 에러 로그 확인
echo "⚠️  최근 에러 (있는 경우):"
sudo journalctl -u trading-bot -p err -n 5 --no-pager
echo ""

# 7. cron 작업 확인
echo "⏰ cron 작업:"
crontab -l | grep trading-bot
echo ""

echo "=================================================="
echo "✅ 헬스 체크 완료"
echo "=================================================="
