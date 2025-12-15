"""
config.py - KIS Open API 설정 파일
Configuration file for KIS Open API

이 파일은 API 인증 정보와 트레이딩 설정을 관리합니다.
실제 사용 시 .env 파일이나 환경변수를 통해 민감한 정보를 관리하세요.

This file manages API credentials and trading settings.
For production use, manage sensitive data via .env file or environment variables.
"""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# .env 파일에서 환경 변수 로드
# Load environment variables from .env file
load_dotenv()


@dataclass
class KISConfig:
    """
    KIS API 설정 클래스
    KIS API Configuration Class
    
    Attributes:
        app_key: 실전투자 앱 키
        app_secret: 실전투자 앱 시크릿
        virtual_app_key: 모의투자 앱 키
        virtual_app_secret: 모의투자 앱 시크릿
        account_number: 계좌번호 (8자리-2자리 형식, 예: 50123456-01)
        hts_id: HTS 로그인 ID
        is_virtual: 모의투자 여부 (True: 모의투자, False: 실전투자)
    """
    # 실전투자 API 인증 정보 (Real trading credentials)
    app_key: str = os.getenv("KIS_APP_KEY", "YOUR_APP_KEY_HERE")
    app_secret: str = os.getenv("KIS_APP_SECRET", "YOUR_APP_SECRET_HERE")
    
    # 모의투자 API 인증 정보 (Virtual trading credentials)
    virtual_app_key: str = os.getenv("KIS_VIRTUAL_APP_KEY", "YOUR_VIRTUAL_APP_KEY_HERE")
    virtual_app_secret: str = os.getenv("KIS_VIRTUAL_APP_SECRET", "YOUR_VIRTUAL_APP_SECRET_HERE")
    
    # HTS 로그인 ID (한국투자증권 HTS ID)
    hts_id: str = os.getenv("KIS_HTS_ID", "your_hts_id")
    
    # 계좌 정보
    # Account information
    account_number: str = os.getenv("KIS_ACCOUNT_NUMBER", "00000000-01")
    
    # 모의투자 모드 설정 (True = 모의투자, False = 실전투자)
    # Virtual trading mode (True = mock trading, False = real trading)
    is_virtual: bool = True
    
    # 토큰 저장 파일 경로 (자동 토큰 갱신용)
    # Token storage file path (for automatic token refresh)
    token_file: str = os.getenv("KIS_TOKEN_FILE", "kis_token.json")


@dataclass
class TradingConfig:
    """
    트레이딩 전략 설정 클래스
    Trading Strategy Configuration Class
    
    Attributes:
        target_stock: 감시할 종목 코드
        buy_threshold_percent: 매수 트리거 하락률 (%)
        quantity: 주문 수량
        max_position: 최대 보유 수량
    """
    # 감시할 종목 코드 (기본: 삼성전자)
    # Target stock code (default: Samsung Electronics)
    target_stock: str = os.getenv("TARGET_STOCK", "005930")
    
    # 매수 조건: 전일 종가 대비 하락률 (%)
    # Buy condition: price drop percentage from previous close
    buy_threshold_percent: float = float(os.getenv("BUY_THRESHOLD", "5.0"))
    
    # 주문 수량
    # Order quantity
    quantity: int = int(os.getenv("ORDER_QUANTITY", "1"))
    
    # 최대 보유 수량 (이 이상 보유 시 추가 매수 안함)
    # Maximum position (no additional buy if holding more than this)
    max_position: int = int(os.getenv("MAX_POSITION", "10"))
    
    # 실시간 시세 구독할 종목 목록
    # Stock list for real-time price subscription
    watch_list: list = None
    
    def __post_init__(self):
        if self.watch_list is None:
            # 기본 감시 목록: 삼성전자
            # Default watch list: Samsung Electronics
            self.watch_list = [self.target_stock]


@dataclass  
class LogConfig:
    """
    로깅 설정 클래스
    Logging Configuration Class
    """
    # 로그 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
    level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 로그 파일 경로 (None이면 콘솔만 출력)
    file_path: Optional[str] = os.getenv("LOG_FILE", "trading.log")
    
    # 로그 포맷
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class MACrossoverConfig:
    """
    이동평균선 크로스오버 전략 설정 클래스
    Moving Average Crossover Strategy Configuration Class
    
    화장품 관련 종목을 대상으로 골든크로스/데드크로스 매매 전략
    Golden Cross / Death Cross trading strategy for cosmetics-related stocks
    """
    
    # 대상 종목 리스트 (화장품 관련주)
    # Target stock list (cosmetics-related stocks)
    # 종목코드: 종목명
    COSMETICS_STOCKS: dict = None
    
    # ========================================
    # 타임프레임 설정 (Timeframe Settings)
    # ========================================
    use_minute_chart: bool = os.getenv("USE_MINUTE_CHART", "true").lower() == "true"  # 분봉 사용 여부
    chart_period: int = int(os.getenv("CHART_PERIOD", "1"))          # 분봉 주기 (1, 3, 5, 10, 15, 30, 60)
    
    # 이동평균선 설정 (Moving Average Settings)
    # 분봉 사용 시: 20분/60분, 일봉 사용 시: 20일/60일
    short_ma_period: int = int(os.getenv("SHORT_MA_PERIOD", "20"))   # 단기 이평선
    long_ma_period: int = int(os.getenv("LONG_MA_PERIOD", "60"))     # 장기 이평선
    
    # RSI 설정 (RSI Settings)
    rsi_period: int = int(os.getenv("RSI_PERIOD", "14"))             # RSI 기간
    rsi_overbought: int = int(os.getenv("RSI_OVERBOUGHT", "70"))     # 과매수 기준
    rsi_oversold: int = int(os.getenv("RSI_OVERSOLD", "30"))         # 과매도 기준
    
    # 데이터 조회 설정 (Data Fetch Settings)
    lookback_days: int = int(os.getenv("LOOKBACK_DAYS", "200"))      # 조회할 일봉 데이터 수
    
    # 주문 설정 (Order Settings)
    order_quantity: int = int(os.getenv("MA_ORDER_QUANTITY", "1"))   # 주문 수량 (종목당)
    
    # ========================================
    # 배치 처리 설정 (Batch Processing Settings)
    # Rate Limit 방지를 위한 배치 처리
    # ========================================
    batch_size: int = int(os.getenv("BATCH_SIZE", "3"))              # 한 배치당 종목 수
    batch_delay: float = float(os.getenv("BATCH_DELAY", "2.0"))      # 배치 간 대기 시간 (초)
    api_delay: float = float(os.getenv("API_DELAY", "0.5"))          # API 호출 간 대기 시간 (초)
    
    # ========================================
    # 분봉 전략 실행 설정 (Minute Strategy Settings)
    # ========================================
    analysis_interval: int = int(os.getenv("ANALYSIS_INTERVAL", "60"))  # 분석 주기 (초)
    market_open: str = os.getenv("MARKET_OPEN", "09:00")             # 장 시작 시간
    market_close: str = os.getenv("MARKET_CLOSE", "15:30")           # 장 마감 시간
    
    # 스케줄링 설정 (일봉용)
    run_time: str = os.getenv("MA_RUN_TIME", "15:40")                # 실행 시간 (장 마감 전)
    
    # ========================================
    # 손절/익절 설정 (Stop-Loss / Take-Profit Settings)
    # ========================================
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "-1.0"))     # 손절 기준 (%) - 매입가 대비
    take_profit_pct: float = float(os.getenv("TAKE_PROFIT_PCT", "2.0"))  # 익절 기준 (%) - 매입가 대비
    trailing_stop: bool = os.getenv("TRAILING_STOP", "false").lower() == "true"  # 트레일링 스탑 사용
    
    # ========================================
    # 노이즈 필터 설정 (Noise Filter Settings)
    # 1분봉에서 허위 신호 최소화
    # ========================================
    # RSI 필터
    use_rsi_filter: bool = os.getenv("USE_RSI_FILTER", "true").lower() == "true"
    rsi_buy_max: int = int(os.getenv("RSI_BUY_MAX", "65"))           # 매수 시 RSI 상한 (과매수 방지)
    rsi_sell_min: int = int(os.getenv("RSI_SELL_MIN", "35"))         # 매도 시 RSI 하한 (과매도 방지)
    
    # 거래량 필터
    use_volume_filter: bool = os.getenv("USE_VOLUME_FILTER", "true").lower() == "true"
    volume_ma_period: int = int(os.getenv("VOLUME_MA_PERIOD", "20"))  # 거래량 이평 기간
    volume_multiplier: float = float(os.getenv("VOLUME_MULTIPLIER", "1.5"))  # 평균 대비 거래량 배수
    
    # MA 갭 필터 (너무 작은 크로스오버 무시)
    use_ma_gap_filter: bool = os.getenv("USE_MA_GAP_FILTER", "true").lower() == "true"
    min_ma_gap_pct: float = float(os.getenv("MIN_MA_GAP_PCT", "0.1"))  # 최소 MA 갭 (%)
    
    # 연속 신호 필터 (같은 신호 연속 발생 시 무시)
    signal_cooldown: int = int(os.getenv("SIGNAL_COOLDOWN", "5"))     # 신호 간 최소 간격 (분)
    
    # 종목 그룹 (초기값 None, __post_init__에서 설정)
    COSMETICS_STOCKS: dict = None
    AI_STOCKS: dict = None
    TECH_GIANTS: dict = None  # 대형 기술주
    
    def __post_init__(self):
        # ========================================
        # 화장품 관련 종목 (Cosmetics Stocks)
        # ========================================
        if self.COSMETICS_STOCKS is None:
            self.COSMETICS_STOCKS = {
                "090430": "아모레퍼시픽",      # Amorepacific
                "051900": "LG생활건강",        # LG H&H
                "192820": "코스맥스",          # Cosmax
                "161890": "한국콜마",          # Kolmar Korea
                "237880": "클리오",            # Clio
                "950140": "잉글우드랩",        # Inglwood Lab
                "003350": "한국화장품제조",    # Hankook Cosmetics Manufacturing
                "078520": "에이블씨엔씨",      # Able C&C
                "214420": "토니모리",          # Tony Moly
                "241710": "코스메카코리아",    # Cosmecca Korea
            }
        
        # ========================================
        # AI 관련 종목 (AI-related Stocks)
        # ========================================
        if self.AI_STOCKS is None:
            self.AI_STOCKS = {
                "039030": "이오테크닉스",      # EO Technics - AI semiconductor laser
                "403870": "HPSP",              # AI semiconductor equipment
                "348210": "넥스틴",            # Nextin - wafer inspection
                "322310": "오로스테크놀로지",  # Orros Tech - 3D measurement
                "377480": "마인즈랩",          # MINDs Lab - AI voice/chatbot
                "352480": "씨이랩",            # CE Lab - AI video analysis
                "054800": "아이디스",          # IDIS - AI security
                "950160": "코난테크놀로지",    # Konan Tech - AI search/NLP
                "067310": "하나마이크론",      # Hana Micron - AI semiconductor packaging
                "226330": "신테카바이오",      # Syntekabio - AI drug discovery
            }
        
        # ========================================
        # 대형 기술주 (Tech Giants)
        # 삼성전자, SK하이닉스 등 반도체 대형주
        # ========================================
        if self.TECH_GIANTS is None:
            self.TECH_GIANTS = {
                "005930": "삼성전자",          # Samsung Electronics
                "000660": "SK하이닉스",        # SK Hynix
                "005935": "삼성전자우",        # Samsung Electronics Preferred
                "005380": "현대차",            # Hyundai Motor
                "000270": "기아",              # Kia
                "035420": "NAVER",             # Naver
                "035720": "카카오",            # Kakao
                "006400": "삼성SDI",           # Samsung SDI
                "373220": "LG에너지솔루션",   # LG Energy Solution
                "051910": "LG화학",            # LG Chem
            }
    
    def get_stocks(self, group: str = "cosmetics") -> dict:
        """
        종목 그룹별 종목 딕셔너리 반환
        Return stock dictionary by group
        
        Args:
            group: "cosmetics", "ai", "all"
        
        Returns:
            dict: {종목코드: 종목명}
        """
        if group == "cosmetics":
            return self.COSMETICS_STOCKS
        elif group == "ai":
            return self.AI_STOCKS
        elif group == "tech":
            return self.TECH_GIANTS
        elif group == "all":
            # 모든 종목 합치기
            all_stocks = {}
            all_stocks.update(self.COSMETICS_STOCKS)
            all_stocks.update(self.AI_STOCKS)
            all_stocks.update(self.TECH_GIANTS)
            return all_stocks
        else:
            # 커스텀 그룹 (환경변수에서 로드 가능)
            return self.COSMETICS_STOCKS
    
    def get_stock_list(self, group: str = "cosmetics") -> list:
        """
        종목 코드 리스트 반환
        Return list of stock codes
        """
        return list(self.get_stocks(group).keys())
    
    def get_stock_name(self, code: str) -> str:
        """
        종목 코드로 종목명 조회
        Get stock name by code
        """
        # 모든 그룹에서 검색
        all_stocks = self.get_stocks("all")
        return all_stocks.get(code, code)
    
    def get_available_groups(self) -> list:
        """사용 가능한 종목 그룹 리스트"""
        return ["cosmetics", "ai", "tech", "all"]


@dataclass
class MomentumBreakoutConfig:
    """
    모멘텀 브레이크아웃 전략 설정 클래스
    Momentum Breakout Strategy Configuration
    
    대형 기술주(삼성전자, SK하이닉스) 대상 추세 추종 전략
    Trend-following strategy for tech giants
    """
    
    # ========================================
    # 브레이크아웃 설정 (Breakout Settings)
    # ========================================
    breakout_period: int = int(os.getenv("BREAKOUT_PERIOD", "20"))       # N일 고가 돌파 기준
    breakdown_period: int = int(os.getenv("BREAKDOWN_PERIOD", "10"))     # N일 저가 이탈 기준
    
    # ADX 설정 (추세 강도)
    adx_period: int = int(os.getenv("ADX_PERIOD", "14"))                 # ADX 기간
    adx_threshold: int = int(os.getenv("ADX_THRESHOLD", "25"))           # 추세 진입 ADX 기준
    
    # ATR 설정 (변동성 기반 손절)
    atr_period: int = int(os.getenv("ATR_PERIOD", "14"))                 # ATR 기간
    atr_multiplier: float = float(os.getenv("ATR_MULTIPLIER", "2.0"))    # ATR 배수 (손절폭)
    
    # 거래량 필터
    volume_breakout_multiplier: float = float(os.getenv("VOLUME_BREAKOUT_MULT", "1.5"))  # 돌파 시 거래량 배수
    
    # 트레일링 스탑
    use_trailing_stop: bool = os.getenv("USE_TRAILING_STOP", "true").lower() == "true"
    trailing_stop_pct: float = float(os.getenv("TRAILING_STOP_PCT", "2.0"))  # 트레일링 스탑 %
    
    # 주문 설정
    order_quantity: int = int(os.getenv("MOMENTUM_ORDER_QTY", "1"))
    max_positions: int = int(os.getenv("MAX_POSITIONS", "5"))            # 최대 동시 보유 종목 수
    
    # ========================================
    # 이벤트 드리븐 설정 (Event-Driven Settings)
    # ========================================
    use_event_driven: bool = os.getenv("USE_EVENT_DRIVEN", "true").lower() == "true"
    
    # 긍정적 키워드 (매수 신호)
    positive_keywords: list = None
    
    # 부정적 키워드 (즉시 청산)
    negative_keywords: list = None
    
    # 거래량 급등 기준 (뉴스 발생 시)
    news_volume_spike: float = float(os.getenv("NEWS_VOLUME_SPIKE", "3.0"))  # 평균 대비 배수
    
    # 뉴스 체크 간격 (초)
    news_check_interval: int = int(os.getenv("NEWS_CHECK_INTERVAL", "60"))
    
    def __post_init__(self):
        if self.positive_keywords is None:
            self.positive_keywords = [
                "실적 호조", "어닝 서프라이즈", "목표가 상향", "매수 추천",
                "HBM", "AI 반도체", "수주", "계약 체결", "신규 투자",
                "배당 확대", "자사주 매입", "주주환원", "최대 실적",
                "수출 증가", "점유율 확대", "신제품", "기술 혁신"
            ]
        
        if self.negative_keywords is None:
            self.negative_keywords = [
                "실적 부진", "어닝 쇼크", "목표가 하향", "매도 의견",
                "적자 전환", "감산", "구조조정", "소송", "제재",
                "리콜", "사고", "횡령", "배임", "수사", "압수수색"
            ]


# 전역 설정 인스턴스 생성
# Create global configuration instances
kis_config = KISConfig()
trading_config = TradingConfig()
log_config = LogConfig()
ma_config = MACrossoverConfig()
momentum_config = MomentumBreakoutConfig()


def print_config_status():
    """
    현재 설정 상태를 출력합니다 (민감한 정보는 마스킹).
    Print current configuration status (sensitive info masked).
    """
    print("=" * 50)
    print("📊 KIS Trading Bot Configuration Status")
    print("=" * 50)
    
    # API 키 마스킹 (앞 4자리만 표시)
    masked_key = kis_config.app_key[:4] + "*" * (len(kis_config.app_key) - 4) if len(kis_config.app_key) > 4 else "****"
    masked_secret = kis_config.app_secret[:4] + "*" * 8 if len(kis_config.app_secret) > 4 else "****"
    masked_vkey = kis_config.virtual_app_key[:4] + "*" * (len(kis_config.virtual_app_key) - 4) if len(kis_config.virtual_app_key) > 4 else "****"
    masked_vsecret = kis_config.virtual_app_secret[:4] + "*" * 8 if len(kis_config.virtual_app_secret) > 4 else "****"
    
    print(f"🔑 Real App Key: {masked_key}")
    print(f"🔐 Real App Secret: {masked_secret}")
    print(f"🔑 Virtual App Key: {masked_vkey}")
    print(f"🔐 Virtual App Secret: {masked_vsecret}")
    print(f"👤 HTS ID: {kis_config.hts_id}")
    print(f"💳 Account: {kis_config.account_number}")
    print(f"🎮 Mode: {'모의투자 (Virtual)' if kis_config.is_virtual else '실전투자 (Real)'}")
    print("-" * 50)
    print(f"📈 Target Stock: {trading_config.target_stock}")
    print(f"📉 Buy Threshold: -{trading_config.buy_threshold_percent}%")
    print(f"📦 Order Quantity: {trading_config.quantity}")
    print(f"📊 Max Position: {trading_config.max_position}")
    print(f"👀 Watch List: {trading_config.watch_list}")
    print("-" * 50)
    print("📈 MA Crossover Strategy Settings:")
    print(f"   Short MA: {ma_config.short_ma_period}일")
    print(f"   Long MA: {ma_config.long_ma_period}일")
    print(f"   RSI Period: {ma_config.rsi_period}일")
    print(f"   RSI Overbought/Oversold: {ma_config.rsi_overbought}/{ma_config.rsi_oversold}")
    print(f"   Lookback Days: {ma_config.lookback_days}일")
    print(f"   Target Stocks: {len(ma_config.COSMETICS_STOCKS)}개 화장품주")
    print("=" * 50)


if __name__ == "__main__":
    # 설정 파일 직접 실행 시 현재 상태 출력
    # Print current status when running config file directly
    print_config_status()
