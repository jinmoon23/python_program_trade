#!/bin/bash
# KIS 트레이딩 봇 실행 스크립트
# KIS Trading Bot Startup Script

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

echo "=================================================="
echo "🤖 KIS Trading Bot - 실행 메뉴"
echo "=================================================="
echo ""
echo "=== 🔥 자동 실행 (장 시작 대기 후 즉시 실행) ==="
echo "1. ⭐ 모든 전략 자동 실행 (추천)"
echo "2. 🎯 듀얼 모멘텀 + 변동성 돌파 (범용 단기 전략) ⭐NEW"
echo "3. 🚀 모멘텀 + 이벤트 (대형 기술주)"
echo ""
echo "=== 개별 전략 ==="
echo "4. MA 크로스오버 - 대형 기술주"
echo "5. MA 크로스오버 - 화장품주"
echo "6. MA 크로스오버 - AI주"
echo ""
echo "=== 유틸리티 ==="
echo "7. API 연결 테스트"
echo "8. 일회성 시세 조회"
echo ""
read -p "선택 (1-8): " choice

case $choice in
    1)
        echo "⭐ 모든 전략 자동 실행 (장 시작 대기 중)..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --all
        ;;
    2)
        echo "🎯 듀얼 모멘텀 + 변동성 돌파 전략 시작..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --dmv
        ;;
    3)
        echo "🚀 모멘텀 + 이벤트 전략 시작 (대형 기술주)..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --momentum --stocks tech
        ;;
    4)
        echo "🚀 MA 크로스오버 전략 (대형 기술주) 시작..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --ma-minute --stocks tech
        ;;
    5)
        echo "🚀 MA 크로스오버 전략 (화장품주) 시작..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --ma-minute --stocks cosmetics
        ;;
    6)
        echo "🚀 MA 크로스오버 전략 (AI주) 시작..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --ma-minute --stocks ai
        ;;
    7)
        echo "🔌 API 연결 테스트..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --test
        ;;
    8)
        echo "📊 일회성 시세 조회..."
        $VENV_PYTHON "$SCRIPT_DIR/main.py" --once
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac
