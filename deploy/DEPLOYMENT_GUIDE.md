# AWS EC2 배포 가이드
# KIS Trading Bot Deployment Guide for AWS EC2 t2.micro

## 📋 사전 준비

### 1. AWS 계정 생성
- [AWS 프리티어](https://aws.amazon.com/ko/free/) 가입
- 신용카드 등록 필요 (프리티어 범위 내 무료)

### 2. 로컬 준비물
- `.env` 파일 (API 키 포함)
- SSH 키 페어 (`.pem` 파일)

---

## 🚀 1단계: EC2 인스턴스 생성

### AWS 콘솔 접속
1. [AWS EC2 콘솔](https://console.aws.amazon.com/ec2/) 접속
2. 리전 선택: **서울 (ap-northeast-2)**

### 인스턴스 시작
1. **"인스턴스 시작"** 클릭
2. 다음 설정 선택:

```
이름: trading-bot
AMI: Ubuntu Server 22.04 LTS (64-bit x86)
인스턴스 유형: t2.micro (프리티어)
키 페어: 새로 생성 또는 기존 키 선택
  - 이름: trading-bot-key
  - 유형: RSA
  - 형식: .pem
  - 다운로드 후 안전한 곳에 보관

네트워크 설정:
  - VPC: 기본값
  - 서브넷: 기본값
  - 퍼블릭 IP 자동 할당: 활성화
  - 보안 그룹: 새로 생성
    - 규칙: SSH (포트 22) - 내 IP

스토리지: 8GB gp3 (기본값)
```

3. **"인스턴스 시작"** 클릭

---

## 🔑 2단계: SSH 키 설정

### Mac/Linux
```bash
# 키 파일 권한 설정
chmod 400 ~/Downloads/trading-bot-key.pem

# SSH 접속 테스트
ssh -i ~/Downloads/trading-bot-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### Windows (PowerShell)
```powershell
# SSH 접속
ssh -i C:\Users\YourName\Downloads\trading-bot-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

---

## 📦 3단계: 프로젝트 업로드

### 방법 1: Git Clone (추천)
```bash
# EC2에 접속한 상태에서
cd /home/ubuntu
git clone https://github.com/your-username/python_program_trade.git
cd python_program_trade
```

### 방법 2: SCP로 직접 업로드
```bash
# 로컬 컴퓨터에서 실행
cd /Users/edward/Documents/pr_trade
tar -czf trading-bot.tar.gz python_program_trade/

scp -i ~/Downloads/trading-bot-key.pem trading-bot.tar.gz ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/

# EC2에서 압축 해제
ssh -i ~/Downloads/trading-bot-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
cd /home/ubuntu
tar -xzf trading-bot.tar.gz
```

---

## 🔐 4단계: .env 파일 업로드

```bash
# 로컬 컴퓨터에서 실행
scp -i ~/Downloads/trading-bot-key.pem \
    /Users/edward/Documents/pr_trade/python_program_trade/.env \
    ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/python_program_trade/
```

---

## ⚙️ 5단계: 자동 설치 실행

```bash
# EC2에 SSH 접속
ssh -i ~/Downloads/trading-bot-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# 설치 스크립트 실행
cd /home/ubuntu/python_program_trade
chmod +x deploy/setup_ec2.sh
./deploy/setup_ec2.sh
```

설치 스크립트가 자동으로:
- ✅ 시스템 업데이트
- ✅ Python 3.11 설치
- ✅ 가상환경 생성
- ✅ 의존성 설치
- ✅ systemd 서비스 등록
- ✅ cron 작업 설정 (매일 08:50 재시작)
- ✅ 방화벽 설정
- ✅ 서비스 시작

---

## 📊 6단계: 동작 확인

### 서비스 상태 확인
```bash
sudo systemctl status trading-bot
```

### 실시간 로그 확인
```bash
# systemd 로그
sudo journalctl -u trading-bot -f

# 또는 파일 로그
tail -f /home/ubuntu/python_program_trade/logs/bot.log
```

### 에러 로그 확인
```bash
tail -f /home/ubuntu/python_program_trade/logs/bot_error.log
```

---

## 🔧 유용한 명령어

### 서비스 관리
```bash
# 서비스 시작
sudo systemctl start trading-bot

# 서비스 중지
sudo systemctl stop trading-bot

# 서비스 재시작
sudo systemctl restart trading-bot

# 서비스 상태 확인
sudo systemctl status trading-bot

# 부팅 시 자동 시작 활성화
sudo systemctl enable trading-bot

# 부팅 시 자동 시작 비활성화
sudo systemctl disable trading-bot
```

### 로그 확인
```bash
# 최근 100줄
sudo journalctl -u trading-bot -n 100

# 실시간 로그
sudo journalctl -u trading-bot -f

# 오늘 로그만
sudo journalctl -u trading-bot --since today

# 특정 시간 이후 로그
sudo journalctl -u trading-bot --since "2025-12-16 09:00:00"
```

### 시스템 모니터링
```bash
# CPU/메모리 사용률
htop

# 디스크 사용량
df -h

# 메모리 사용량
free -h
```

---

## 🔄 코드 업데이트 방법

### Git 사용 시
```bash
cd /home/ubuntu/python_program_trade
git pull origin main
sudo systemctl restart trading-bot
```

### 파일 직접 업로드 시
```bash
# 로컬에서
scp -i ~/Downloads/trading-bot-key.pem \
    /Users/edward/Documents/pr_trade/python_program_trade/strategy_dmv.py \
    ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/python_program_trade/

# EC2에서
sudo systemctl restart trading-bot
```

---

## 📅 자동 재시작 설정 확인

### cron 작업 확인
```bash
crontab -l
```

출력 예시:
```
50 8 * * 1-5 sudo systemctl restart trading-bot
```

### cron 작업 수정
```bash
crontab -e

# 시간 변경 예시 (08:55로 변경)
55 8 * * 1-5 sudo systemctl restart trading-bot
```

---

## 🔒 보안 설정

### SSH 키 기반 인증만 허용
```bash
sudo nano /etc/ssh/sshd_config

# 다음 설정 확인
PasswordAuthentication no
PubkeyAuthentication yes

# SSH 재시작
sudo systemctl restart sshd
```

### 방화벽 규칙 확인
```bash
sudo ufw status
```

---

## 💰 비용 관리

### 프리티어 사용량 확인
1. AWS 콘솔 → **Billing Dashboard**
2. **Free Tier** 탭에서 사용량 확인

### 프리티어 제한
- t2.micro: 월 750시간 (24/7 운영 가능)
- 스토리지: 30GB EBS
- 데이터 전송: 15GB/월

### 비용 알림 설정
1. AWS 콘솔 → **Billing** → **Budgets**
2. **Create budget** → **Cost budget**
3. 금액: $1 (알림용)

---

## 🐛 문제 해결

### 서비스가 시작되지 않을 때
```bash
# 상세 로그 확인
sudo journalctl -u trading-bot -xe

# 설정 파일 확인
sudo systemctl cat trading-bot

# 수동 실행 테스트
cd /home/ubuntu/python_program_trade
source venv/bin/activate
python main.py --dmv
```

### API 연결 실패
```bash
# .env 파일 확인
cat /home/ubuntu/python_program_trade/.env

# 네트워크 확인
ping -c 3 openapi.koreainvestment.com
```

### 메모리 부족
```bash
# 스왑 파일 생성 (t2.micro는 1GB RAM만 제공)
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📱 모니터링 및 알림 (선택)

### Slack 알림 설정
```python
# config.py에 추가
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# 거래 발생 시 알림
import requests
requests.post(SLACK_WEBHOOK_URL, json={"text": "매수 체결: 삼성전자 1주"})
```

### 이메일 알림
```bash
# sendmail 설치
sudo apt install -y sendmail

# Python에서 사용
import smtplib
```

---

## 🎯 체크리스트

배포 전:
- [ ] AWS 계정 생성 완료
- [ ] EC2 인스턴스 생성 완료
- [ ] SSH 키 다운로드 및 권한 설정
- [ ] .env 파일 준비 완료

배포 중:
- [ ] 프로젝트 업로드 완료
- [ ] .env 파일 업로드 완료
- [ ] setup_ec2.sh 실행 완료
- [ ] 서비스 정상 시작 확인

배포 후:
- [ ] 로그 확인 (에러 없음)
- [ ] cron 작업 설정 확인
- [ ] 비용 알림 설정
- [ ] 백업 계획 수립

---

## 📞 지원

문제 발생 시:
1. 로그 확인: `sudo journalctl -u trading-bot -n 100`
2. 서비스 상태: `sudo systemctl status trading-bot`
3. 수동 실행 테스트: `python main.py --test`

---

## 🔄 백업 및 복구

### 백업
```bash
# 전체 프로젝트 백업
cd /home/ubuntu
tar -czf trading-bot-backup-$(date +%Y%m%d).tar.gz python_program_trade/

# 로컬로 다운로드
scp -i ~/Downloads/trading-bot-key.pem \
    ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/trading-bot-backup-*.tar.gz \
    ~/backups/
```

### 복구
```bash
# 백업 파일 업로드
scp -i ~/Downloads/trading-bot-key.pem \
    ~/backups/trading-bot-backup-20251216.tar.gz \
    ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/

# 압축 해제
tar -xzf trading-bot-backup-20251216.tar.gz
sudo systemctl restart trading-bot
```

---

**배포 완료! 이제 24/7 자동으로 트레이딩 봇이 실행됩니다.** 🎉
