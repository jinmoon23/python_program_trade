# 배포 파일 설명
# Deployment Files Description

이 디렉토리는 AWS EC2 t2.micro 프리티어에 트레이딩 봇을 배포하기 위한 파일들을 포함합니다.

## 📁 파일 목록

### 1. `trading-bot.service`
- **용도**: systemd 서비스 파일
- **위치**: `/etc/systemd/system/trading-bot.service`
- **기능**: 
  - 부팅 시 자동 시작
  - 크래시 시 자동 재시작
  - 로그 자동 기록
  - 리소스 제한 (t2.micro 최적화)

### 2. `setup_ec2.sh`
- **용도**: 자동 설치 스크립트
- **실행**: `./deploy/setup_ec2.sh`
- **기능**:
  - 시스템 업데이트
  - Python 3.11 설치
  - 가상환경 생성
  - 의존성 설치
  - systemd 서비스 등록
  - cron 작업 설정
  - 방화벽 설정

### 3. `DEPLOYMENT_GUIDE.md`
- **용도**: 상세 배포 가이드
- **내용**:
  - EC2 인스턴스 생성 방법
  - SSH 접속 설정
  - 프로젝트 업로드
  - 서비스 관리
  - 문제 해결

### 4. `health_check.sh`
- **용도**: 시스템 상태 확인
- **실행**: `./deploy/health_check.sh`
- **기능**:
  - 서비스 상태 확인
  - 메모리/디스크 사용량
  - 최근 로그 확인
  - 에러 로그 확인

## 🚀 빠른 시작

### 1. EC2 인스턴스 생성
```bash
# AWS 콘솔에서:
# - Ubuntu 22.04 LTS
# - t2.micro (프리티어)
# - 서울 리전 (ap-northeast-2)
```

### 2. 프로젝트 업로드
```bash
# 로컬에서
scp -i your-key.pem -r python_program_trade ubuntu@YOUR_EC2_IP:/home/ubuntu/
```

### 3. .env 파일 업로드
```bash
scp -i your-key.pem .env ubuntu@YOUR_EC2_IP:/home/ubuntu/python_program_trade/
```

### 4. 자동 설치 실행
```bash
# EC2에서
cd /home/ubuntu/python_program_trade
chmod +x deploy/setup_ec2.sh
./deploy/setup_ec2.sh
```

## 📊 모니터링

### 서비스 상태 확인
```bash
sudo systemctl status trading-bot
```

### 실시간 로그
```bash
sudo journalctl -u trading-bot -f
```

### 헬스 체크
```bash
./deploy/health_check.sh
```

## 🔧 관리 명령어

```bash
# 시작
sudo systemctl start trading-bot

# 중지
sudo systemctl stop trading-bot

# 재시작
sudo systemctl restart trading-bot

# 로그 확인
sudo journalctl -u trading-bot -n 100
```

## 💰 비용

- **t2.micro**: 월 750시간 무료 (프리티어)
- **스토리지**: 30GB 무료
- **데이터 전송**: 15GB/월 무료

프리티어 범위 내에서 **완전 무료** 운영 가능 (1년간)

## 📞 지원

자세한 내용은 `DEPLOYMENT_GUIDE.md` 참조
