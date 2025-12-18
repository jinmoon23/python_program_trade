#!/bin/bash
# =====================================================
# 모든 전략 EC2 배포 스크립트
# Deploy All Strategies to EC2
# =====================================================
# - 단기: strategy_hybrid.py (WebSocket + 폴링, 20/60 MA)
# - 중장기: strategy_cosmetics.py (일봉, 50/200 MA)
# =====================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:-}"
EC2_KEY="${EC2_KEY:-}"
REMOTE_DIR="/home/ubuntu/python_program_trade"

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}🚀 전체 전략 EC2 배포${NC}"
echo -e "${BLUE}   단기: Hybrid (WebSocket + 폴링)${NC}"
echo -e "${BLUE}   중장기: Cosmetics (50/200 SMA)${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo ""

usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --host <IP>      EC2 호스트 IP 주소"
    echo "  --key <path>     SSH 키 파일 경로"
    echo "  --all            전체 배포 (기본값)"
    echo "  --status         현재 상태 확인"
    echo "  --logs           모든 로그 확인"
    echo "  --stop           모든 전략 중지"
    echo "  -h, --help       도움말 표시"
    exit 1
}

ACTION="all"
while [[ $# -gt 0 ]]; do
    case $1 in
        --host) EC2_HOST="$2"; shift 2 ;;
        --key) EC2_KEY="$2"; shift 2 ;;
        --all) ACTION="all"; shift ;;
        --status) ACTION="status"; shift ;;
        --logs) ACTION="logs"; shift ;;
        --stop) ACTION="stop"; shift ;;
        -h|--help) usage ;;
        *) echo -e "${RED}알 수 없는 옵션: $1${NC}"; usage ;;
    esac
done

if [ -z "$EC2_HOST" ]; then
    read -p "EC2 호스트 IP: " EC2_HOST
fi
if [ -z "$EC2_KEY" ]; then
    read -p "SSH 키 파일 경로: " EC2_KEY
fi

EC2_KEY="${EC2_KEY/#\~/$HOME}"
if [ ! -f "$EC2_KEY" ]; then
    echo -e "${RED}❌ SSH 키 파일을 찾을 수 없습니다: $EC2_KEY${NC}"
    exit 1
fi

SSH_CMD="ssh -i $EC2_KEY -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST"
SCP_CMD="scp -i $EC2_KEY -o StrictHostKeyChecking=no"

echo -e "${GREEN}✅ EC2: $EC2_HOST${NC}"
echo ""

test_connection() {
    echo -e "${BLUE}🔗 SSH 연결 테스트...${NC}"
    if $SSH_CMD "echo 'OK'" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 연결 성공${NC}"
        return 0
    else
        echo -e "${RED}❌ 연결 실패${NC}"
        return 1
    fi
}

stop_all() {
    echo -e "${YELLOW}🛑 모든 전략 중지...${NC}"
    $SSH_CMD << 'ENDSSH'
        for svc in trading-bot trading-bot-cosmetics trading-bot-ma trading-bot-ai trading-bot-hybrid; do
            if sudo systemctl is-active --quiet $svc 2>/dev/null; then
                echo "중지: $svc"
                sudo systemctl stop $svc
            fi
        done
        pkill -f "python.*main.py" 2>/dev/null || true
        pkill -f "python.*run_cosmetics" 2>/dev/null || true
        echo "✅ 모든 전략 중지 완료"
ENDSSH
}

deploy_files() {
    echo -e "${BLUE}📦 파일 배포...${NC}"
    
    # 핵심 파일
    FILES=(
        "config.py"
        "kis_client.py"
        "main.py"
        "strategy.py"
        "strategy_hybrid.py"
        "strategy_dmv.py"
        "cosmetics_config.py"
        "strategy_cosmetics.py"
        "run_cosmetics_strategy.py"
        "requirements.txt"
    )
    
    # 서비스 파일
    SERVICE_FILES=(
        "deploy/trading-bot-ma.service"
        "deploy/trading-bot-cosmetics.service"
    )
    
    $SSH_CMD "mkdir -p $REMOTE_DIR/logs $REMOTE_DIR/backtest_results $REMOTE_DIR/deploy"
    
    echo "  📄 핵심 파일 전송..."
    for file in "${FILES[@]}"; do
        if [ -f "$PROJECT_DIR/$file" ]; then
            $SCP_CMD "$PROJECT_DIR/$file" "$EC2_USER@$EC2_HOST:$REMOTE_DIR/$file" 2>/dev/null
            echo "     ✓ $file"
        fi
    done
    
    echo "  📄 서비스 파일 전송..."
    for file in "${SERVICE_FILES[@]}"; do
        if [ -f "$PROJECT_DIR/$file" ]; then
            $SCP_CMD "$PROJECT_DIR/$file" "$EC2_USER@$EC2_HOST:$REMOTE_DIR/$file" 2>/dev/null
            echo "     ✓ $file"
        fi
    done
    
    echo -e "${BLUE}⚙️ 서비스 설치...${NC}"
    $SSH_CMD << 'ENDSSH'
        sudo cp /home/ubuntu/python_program_trade/deploy/trading-bot-ma.service /etc/systemd/system/
        sudo cp /home/ubuntu/python_program_trade/deploy/trading-bot-cosmetics.service /etc/systemd/system/
        sudo systemctl daemon-reload
        echo "✅ 서비스 파일 설치 완료"
ENDSSH
}

start_all() {
    echo -e "${BLUE}🚀 모든 전략 시작...${NC}"
    $SSH_CMD << 'ENDSSH'
        cd /home/ubuntu/python_program_trade
        
        # 가상환경 확인
        if [ ! -d "venv" ]; then
            echo "가상환경 생성 중..."
            python3 -m venv venv
            source venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
        fi
        
        echo ""
        echo "=========================================="
        echo "📈 단기 전략 (Hybrid) 시작..."
        echo "=========================================="
        sudo systemctl enable trading-bot-ma
        sudo systemctl start trading-bot-ma
        sleep 2
        
        echo ""
        echo "=========================================="
        echo "🧴 중장기 전략 (Cosmetics) 시작..."
        echo "=========================================="
        sudo systemctl enable trading-bot-cosmetics
        sudo systemctl start trading-bot-cosmetics
        sleep 2
        
        echo ""
        echo "=========================================="
        echo "📊 전체 상태"
        echo "=========================================="
        for svc in trading-bot-ma trading-bot-cosmetics; do
            if sudo systemctl is-active --quiet $svc; then
                echo "✅ $svc: 실행 중"
            else
                echo "❌ $svc: 중지됨"
            fi
        done
ENDSSH
}

check_status() {
    echo -e "${BLUE}📊 전략 상태 확인...${NC}"
    $SSH_CMD << 'ENDSSH'
        echo ""
        echo "=========================================="
        echo "🤖 Trading Bot 서비스 상태"
        echo "=========================================="
        
        for svc in trading-bot trading-bot-ma trading-bot-cosmetics trading-bot-ai trading-bot-hybrid; do
            if sudo systemctl is-active --quiet $svc 2>/dev/null; then
                desc=$(systemctl show -p Description --value $svc 2>/dev/null || echo "")
                echo "✅ $svc: 실행 중"
                echo "   └─ $desc"
            fi
        done
        
        echo ""
        echo "=========================================="
        echo "📈 단기 전략 (Hybrid) 상세"
        echo "=========================================="
        sudo systemctl status trading-bot-ma --no-pager -l 2>/dev/null | head -15 || echo "(없음)"
        
        echo ""
        echo "=========================================="
        echo "🧴 중장기 전략 (Cosmetics) 상세"
        echo "=========================================="
        sudo systemctl status trading-bot-cosmetics --no-pager -l 2>/dev/null | head -15 || echo "(없음)"
        
        echo ""
        echo "=========================================="
        echo "💾 시스템 리소스"
        echo "=========================================="
        free -h | head -2
        df -h / | tail -1
ENDSSH
}

show_logs() {
    echo -e "${BLUE}📋 최근 로그...${NC}"
    $SSH_CMD << 'ENDSSH'
        echo ""
        echo "=========================================="
        echo "📈 단기 전략 (Hybrid) 로그"
        echo "=========================================="
        sudo journalctl -u trading-bot-ma --no-pager -n 20 2>/dev/null || echo "(없음)"
        
        echo ""
        echo "=========================================="
        echo "🧴 중장기 전략 (Cosmetics) 로그"
        echo "=========================================="
        sudo journalctl -u trading-bot-cosmetics --no-pager -n 20 2>/dev/null || echo "(없음)"
ENDSSH
}

main() {
    test_connection || exit 1
    
    case $ACTION in
        stop)
            stop_all
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        all)
            stop_all
            echo ""
            deploy_files
            echo ""
            start_all
            echo ""
            echo -e "${GREEN}=========================================${NC}"
            echo -e "${GREEN}🎉 전체 배포 완료!${NC}"
            echo -e "${GREEN}=========================================${NC}"
            echo ""
            echo "상태 확인: $0 --host $EC2_HOST --key $EC2_KEY --status"
            echo "로그 확인: $0 --host $EC2_HOST --key $EC2_KEY --logs"
            ;;
    esac
}

main
