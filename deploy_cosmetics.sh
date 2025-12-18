#!/bin/bash
# =====================================================
# 화장품 추세추종 전략 EC2 배포 스크립트
# Cosmetics Trend-Following Strategy EC2 Deployment
# =====================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# EC2 설정 (환경변수 또는 기본값)
EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:-}"
EC2_KEY="${EC2_KEY:-}"
REMOTE_DIR="/home/ubuntu/python_program_trade"

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}🧴 화장품 추세추종 전략 EC2 배포${NC}"
echo -e "${BLUE}   50/200일 SMA 골든크로스/데스크로스 + 15% 트레일링 스탑${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo ""

# 사용법 함수
usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --host <IP>      EC2 호스트 IP 주소"
    echo "  --key <path>     SSH 키 파일 경로"
    echo "  --stop           기존 전략 중지만 실행"
    echo "  --deploy         파일 배포만 실행"
    echo "  --start          새 전략 시작만 실행"
    echo "  --all            전체 배포 (기본값)"
    echo "  --status         현재 상태 확인"
    echo "  --logs           로그 확인"
    echo "  -h, --help       도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 --host 3.34.123.45 --key ~/trading-bot-key.pem --all"
    echo "  $0 --host 3.34.123.45 --key ~/trading-bot-key.pem --stop"
    exit 1
}

# 인자 파싱
ACTION="all"
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            EC2_HOST="$2"
            shift 2
            ;;
        --key)
            EC2_KEY="$2"
            shift 2
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --deploy)
            ACTION="deploy"
            shift
            ;;
        --start)
            ACTION="start"
            shift
            ;;
        --all)
            ACTION="all"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --logs)
            ACTION="logs"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}알 수 없는 옵션: $1${NC}"
            usage
            ;;
    esac
done

# 필수 인자 확인
if [ -z "$EC2_HOST" ]; then
    echo -e "${YELLOW}EC2 호스트 IP를 입력하세요:${NC}"
    read -p "> " EC2_HOST
fi

if [ -z "$EC2_KEY" ]; then
    echo -e "${YELLOW}SSH 키 파일 경로를 입력하세요 (예: ~/trading-bot-key.pem):${NC}"
    read -p "> " EC2_KEY
fi

# 키 파일 확인
EC2_KEY="${EC2_KEY/#\~/$HOME}"
if [ ! -f "$EC2_KEY" ]; then
    echo -e "${RED}❌ SSH 키 파일을 찾을 수 없습니다: $EC2_KEY${NC}"
    exit 1
fi

SSH_CMD="ssh -i $EC2_KEY -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST"
SCP_CMD="scp -i $EC2_KEY -o StrictHostKeyChecking=no"

echo -e "${GREEN}✅ EC2 연결 정보:${NC}"
echo "   Host: $EC2_HOST"
echo "   User: $EC2_USER"
echo "   Key: $EC2_KEY"
echo ""

# SSH 연결 테스트
test_connection() {
    echo -e "${BLUE}🔗 SSH 연결 테스트...${NC}"
    if $SSH_CMD "echo 'Connected'" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ SSH 연결 성공${NC}"
        return 0
    else
        echo -e "${RED}❌ SSH 연결 실패${NC}"
        return 1
    fi
}

# 기존 전략 중지
stop_existing() {
    echo -e "${YELLOW}🛑 기존 전략 중지 중...${NC}"
    
    # 모든 trading-bot 서비스 중지
    $SSH_CMD << 'ENDSSH'
        echo "현재 실행 중인 서비스:"
        sudo systemctl list-units --type=service | grep trading-bot || echo "  (없음)"
        
        # 모든 trading-bot 서비스 중지
        for service in trading-bot trading-bot-cosmetics trading-bot-ma trading-bot-ai trading-bot-scheduled; do
            if sudo systemctl is-active --quiet $service 2>/dev/null; then
                echo "중지: $service"
                sudo systemctl stop $service
            fi
        done
        
        # Python 프로세스 확인 및 종료
        pkill -f "python.*main.py" 2>/dev/null || true
        pkill -f "python.*run_cosmetics" 2>/dev/null || true
        
        echo "✅ 기존 전략 중지 완료"
ENDSSH
    echo -e "${GREEN}✅ 기존 전략 중지 완료${NC}"
}

# 파일 배포
deploy_files() {
    echo -e "${BLUE}📦 파일 배포 중...${NC}"
    
    # 배포할 파일 목록
    FILES=(
        "cosmetics_config.py"
        "strategy_cosmetics.py"
        "run_cosmetics_strategy.py"
        "deploy/trading-bot-cosmetics.service"
    )
    
    # 파일 존재 확인
    for file in "${FILES[@]}"; do
        if [ ! -f "$PROJECT_DIR/$file" ]; then
            echo -e "${RED}❌ 파일을 찾을 수 없습니다: $file${NC}"
            exit 1
        fi
    done
    
    # 원격 디렉토리 준비
    $SSH_CMD "mkdir -p $REMOTE_DIR/logs $REMOTE_DIR/backtest_results"
    
    # 파일 전송
    for file in "${FILES[@]}"; do
        echo "  📄 $file"
        $SCP_CMD "$PROJECT_DIR/$file" "$EC2_USER@$EC2_HOST:$REMOTE_DIR/$file"
    done
    
    # 서비스 파일 설치
    echo -e "${BLUE}⚙️ systemd 서비스 설치...${NC}"
    $SSH_CMD << 'ENDSSH'
        sudo cp /home/ubuntu/python_program_trade/deploy/trading-bot-cosmetics.service /etc/systemd/system/
        sudo systemctl daemon-reload
        echo "✅ 서비스 파일 설치 완료"
ENDSSH
    
    echo -e "${GREEN}✅ 파일 배포 완료${NC}"
}

# 새 전략 시작
start_strategy() {
    echo -e "${BLUE}🚀 화장품 추세추종 전략 시작...${NC}"
    
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
        
        # 서비스 활성화 및 시작
        sudo systemctl enable trading-bot-cosmetics
        sudo systemctl start trading-bot-cosmetics
        
        sleep 2
        
        # 상태 확인
        echo ""
        echo "=========================================="
        echo "서비스 상태:"
        sudo systemctl status trading-bot-cosmetics --no-pager || true
        echo "=========================================="
ENDSSH
    
    echo -e "${GREEN}✅ 전략 시작 완료${NC}"
}

# 상태 확인
check_status() {
    echo -e "${BLUE}📊 현재 상태 확인...${NC}"
    
    $SSH_CMD << 'ENDSSH'
        echo ""
        echo "=========================================="
        echo "🤖 Trading Bot 서비스 상태"
        echo "=========================================="
        
        for service in trading-bot trading-bot-cosmetics trading-bot-ma trading-bot-ai; do
            if sudo systemctl is-active --quiet $service 2>/dev/null; then
                echo "✅ $service: 실행 중"
            else
                echo "⚪ $service: 중지됨"
            fi
        done
        
        echo ""
        echo "=========================================="
        echo "📈 화장품 전략 상세 상태"
        echo "=========================================="
        sudo systemctl status trading-bot-cosmetics --no-pager 2>/dev/null || echo "(서비스 없음)"
        
        echo ""
        echo "=========================================="
        echo "💾 시스템 리소스"
        echo "=========================================="
        free -h | head -2
        df -h / | tail -1
ENDSSH
}

# 로그 확인
show_logs() {
    echo -e "${BLUE}📋 최근 로그 (Ctrl+C로 종료)...${NC}"
    $SSH_CMD "sudo journalctl -u trading-bot-cosmetics -f --no-pager -n 50"
}

# 메인 실행
main() {
    test_connection || exit 1
    
    case $ACTION in
        stop)
            stop_existing
            ;;
        deploy)
            deploy_files
            ;;
        start)
            start_strategy
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        all)
            stop_existing
            echo ""
            deploy_files
            echo ""
            start_strategy
            echo ""
            echo -e "${GREEN}=========================================${NC}"
            echo -e "${GREEN}🎉 배포 완료!${NC}"
            echo -e "${GREEN}=========================================${NC}"
            echo ""
            echo "로그 확인: $0 --host $EC2_HOST --key $EC2_KEY --logs"
            echo "상태 확인: $0 --host $EC2_HOST --key $EC2_KEY --status"
            ;;
    esac
}

main
