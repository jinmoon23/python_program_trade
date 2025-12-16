# AWS EC2 빠른 시작 가이드
# Quick Start Guide for AWS EC2 Deployment

## ⏱️ 예상 소요 시간: 30분

---

## 📋 체크리스트

시작 전 준비:
- [ ] AWS 계정 (프리티어)
- [ ] 신용카드 (프리티어 범위 내 무료)
- [ ] `.env` 파일 (API 키 포함)

---

## 🚀 5단계로 완료하기

### 1️⃣ EC2 인스턴스 생성 (5분)

1. [AWS EC2 콘솔](https://console.aws.amazon.com/ec2/) 접속
2. 리전: **서울 (ap-northeast-2)** 선택
3. **"인스턴스 시작"** 클릭
4. 설정:
   ```
   이름: trading-bot
   AMI: Ubuntu Server 22.04 LTS
   인스턴스 유형: t2.micro ✅ 프리티어
   키 페어: 새로 생성 → trading-bot-key.pem 다운로드
   보안 그룹: SSH (22) - 내 IP만 허용
   스토리지: 8GB (기본값)
   ```
5. **"인스턴스 시작"** 클릭
6. 퍼블릭 IP 주소 복사 (예: `3.34.123.45`)

---

### 2️⃣ SSH 접속 (2분)

```bash
# Mac/Linux
chmod 400 ~/Downloads/trading-bot-key.pem
ssh -i ~/Downloads/trading-bot-key.pem ubuntu@YOUR_EC2_IP

# Windows (PowerShell)
ssh -i C:\Users\YourName\Downloads\trading-bot-key.pem ubuntu@YOUR_EC2_IP
```

접속 성공하면 `ubuntu@ip-xxx-xxx-xxx-xxx:~$` 프롬프트가 표시됩니다.

---

### 3️⃣ 프로젝트 업로드 (5분)

#### 방법 A: Git Clone (추천)
```bash
# EC2에서 실행
cd /home/ubuntu
git clone https://github.com/your-username/python_program_trade.git
cd python_program_trade
```

#### 방법 B: 직접 업로드
```bash
# 로컬 컴퓨터에서 실행
cd /Users/edward/Documents/pr_trade
tar -czf bot.tar.gz python_program_trade/

scp -i ~/Downloads/trading-bot-key.pem bot.tar.gz ubuntu@YOUR_EC2_IP:/home/ubuntu/

# EC2에서 압축 해제
ssh -i ~/Downloads/trading-bot-key.pem ubuntu@YOUR_EC2_IP
cd /home/ubuntu
tar -xzf bot.tar.gz
cd python_program_trade
```

---

### 4️⃣ .env 파일 업로드 (2분)

```bash
# 로컬 컴퓨터에서 실행
scp -i ~/Downloads/trading-bot-key.pem \
    /Users/edward/Documents/pr_trade/python_program_trade/.env \
    ubuntu@YOUR_EC2_IP:/home/ubuntu/python_program_trade/
```

**중요**: `.env` 파일에 다음 정보가 포함되어 있는지 확인:
- `KIS_APP_KEY`
- `KIS_APP_SECRET`
- `KIS_VIRTUAL_APP_KEY`
- `KIS_VIRTUAL_APP_SECRET`
- `KIS_ACCOUNT_NUMBER`
- `KIS_HTS_ID`

---

### 5️⃣ 자동 설치 및 실행 (10분)

```bash
# EC2에서 실행
cd /home/ubuntu/python_program_trade
chmod +x deploy/setup_ec2.sh
./deploy/setup_ec2.sh
```

설치 스크립트가 자동으로 모든 것을 설정합니다:
- ✅ Python 3.11 설치
- ✅ 가상환경 생성
- ✅ 패키지 설치
- ✅ systemd 서비스 등록
- ✅ 매일 08:50 자동 재시작 설정
- ✅ 방화벽 설정
- ✅ 봇 시작

---

## ✅ 완료 확인

### 서비스 상태 확인
```bash
sudo systemctl status trading-bot
```

**정상 출력 예시:**
```
● trading-bot.service - KIS Trading Bot
   Loaded: loaded
   Active: active (running)
```

### 실시간 로그 확인
```bash
sudo journalctl -u trading-bot -f
```

**정상 로그 예시:**
```
🚀 듀얼 모멘텀 + 변동성 돌파 전략
⏳ 장 시작 시간까지 대기 중...
```

---

## 🎉 완료!

이제 트레이딩 봇이 24/7 자동으로 실행됩니다:
- ✅ 매일 08:50에 자동 재시작
- ✅ 09:00 장 시작 시 자동 거래 시작
- ✅ 크래시 시 자동 재시작
- ✅ 15:30 장 마감 후 대기

---

## 📊 일상 관리

### 로그 확인 (매일)
```bash
ssh -i ~/Downloads/trading-bot-key.pem ubuntu@YOUR_EC2_IP
sudo journalctl -u trading-bot --since today
```

### 헬스 체크
```bash
cd /home/ubuntu/python_program_trade
./deploy/health_check.sh
```

### 서비스 재시작 (필요 시)
```bash
sudo systemctl restart trading-bot
```

---

## 🔧 코드 업데이트

### Git 사용 시
```bash
cd /home/ubuntu/python_program_trade
git pull origin main
sudo systemctl restart trading-bot
```

### 파일 직접 업로드
```bash
# 로컬에서
scp -i ~/Downloads/trading-bot-key.pem \
    strategy_dmv.py \
    ubuntu@YOUR_EC2_IP:/home/ubuntu/python_program_trade/

# EC2에서
sudo systemctl restart trading-bot
```

---

## 💰 비용 확인

### AWS 콘솔에서 확인
1. [Billing Dashboard](https://console.aws.amazon.com/billing/)
2. **Free Tier** 탭
3. t2.micro 사용량 확인 (월 750시간 무료)

### 비용 알림 설정 (추천)
1. **Budgets** → **Create budget**
2. 금액: $1 (알림용)
3. 이메일 알림 설정

---

## 🐛 문제 해결

### 봇이 시작되지 않을 때
```bash
# 상세 로그 확인
sudo journalctl -u trading-bot -xe

# 수동 실행 테스트
cd /home/ubuntu/python_program_trade
source venv/bin/activate
python main.py --test
```

### API 연결 실패
```bash
# .env 파일 확인
cat .env

# 네트워크 테스트
ping -c 3 openapi.koreainvestment.com
```

### 메모리 부족 (t2.micro는 1GB RAM)
```bash
# 스왑 파일 생성
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📞 추가 도움말

- 상세 가이드: `deploy/DEPLOYMENT_GUIDE.md`
- 파일 설명: `deploy/README.md`
- 헬스 체크: `./deploy/health_check.sh`

---

## 🎯 다음 단계

1. ✅ 첫 거래 확인 (장 시작 후)
2. ✅ 로그 모니터링 습관화
3. ✅ 주간 성과 분석
4. ✅ 전략 파라미터 최적화

**행운을 빕니다! 🚀**
