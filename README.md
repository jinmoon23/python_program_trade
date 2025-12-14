# 🤖 KIS 알고리즘 트레이딩 봇
# KIS Algorithmic Trading Bot

한국투자증권 Open API를 활용한 알고리즘 트레이딩 봇입니다.
`python-kis` 라이브러리를 사용하여 모의투자 환경에서 자동 매매를 수행합니다.

An algorithmic trading bot using Korea Investment & Securities Open API.
Uses `python-kis` library to perform automated trading in mock trading environment.

## 📁 프로젝트 구조 (Project Structure)

```
python_program_trade/
├── config.py          # 설정 관리 (Configuration management)
├── kis_client.py      # KIS API 클라이언트 래퍼 (KIS API client wrapper)
├── strategy.py        # 트레이딩 전략 클래스 (Trading strategy classes)
├── main.py            # 메인 진입점 (Main entry point)
├── requirements.txt   # 의존성 목록 (Dependencies)
├── .env.example       # 환경 변수 예제 (Environment variables example)
├── .gitignore         # Git 제외 파일 (Git ignore)
└── README.md          # 이 파일 (This file)
```

## 🚀 시작하기 (Getting Started)

### 1. 의존성 설치 (Install Dependencies)

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (Setup Environment Variables)

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일을 열어 실제 API 키와 계좌 정보 입력
# Edit .env file with your actual API key and account info
```

### 3. API 연결 테스트 (Test API Connection)

```bash
python main.py --test
```

### 4. 일회성 시세 조회 (One-time Price Query)

```bash
python main.py --once
```

### 5. 봇 실행 (Run Bot)

```bash
python main.py
```

## 📊 기본 전략 (Default Strategy)

**삼성전자 하락 매수 전략 (Samsung Dip-Buy Strategy)**

1. 삼성전자(005930) 실시간 시세 감시
2. 전일 종가 대비 5% 이상 하락 시
3. 시장가로 1주 매수
4. 최대 10주까지 보유

## ⚙️ 설정 옵션 (Configuration Options)

`.env` 파일에서 다음 옵션을 설정할 수 있습니다:

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `KIS_APP_KEY` | API 앱 키 | - |
| `KIS_APP_SECRET` | API 앱 시크릿 | - |
| `KIS_ACCOUNT_NUMBER` | 계좌번호 (8자리-2자리) | - |
| `TARGET_STOCK` | 감시 종목 코드 | 005930 |
| `BUY_THRESHOLD` | 매수 트리거 하락률 (%) | 5.0 |
| `ORDER_QUANTITY` | 주문 수량 | 1 |
| `MAX_POSITION` | 최대 보유 수량 | 10 |
| `LOG_LEVEL` | 로그 레벨 | INFO |

## 🔑 API 키 발급 방법 (How to Get API Keys)

1. [한국투자증권 개발자센터](https://apiportal.koreainvestment.com/) 접속
2. 회원가입 및 로그인
3. **모의투자** 앱 키 신청
4. 발급받은 `app_key`와 `app_secret`을 `.env`에 입력

## ⚠️ 주의사항 (Cautions)

- **모의투자 모드**에서만 테스트하세요
- `.env` 파일은 절대 Git에 커밋하지 마세요
- 실전투자 전환 시 `is_virtual=False` 설정 필요
- 장 운영 시간에만 실시간 시세가 동작합니다

## 📝 라이선스 (License)

MIT License
