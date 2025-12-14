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
    
    def __post_init__(self):
        if self.COSMETICS_STOCKS is None:
            # 화장품 관련 종목 리스트
            # Cosmetics-related stock list
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
    
    def get_stock_list(self) -> list:
        """
        종목 코드 리스트 반환
        Return list of stock codes
        """
        return list(self.COSMETICS_STOCKS.keys())
    
    def get_stock_name(self, code: str) -> str:
        """
        종목 코드로 종목명 조회
        Get stock name by code
        """
        return self.COSMETICS_STOCKS.get(code, code)


# 전역 설정 인스턴스 생성
# Create global configuration instances
kis_config = KISConfig()
trading_config = TradingConfig()
log_config = LogConfig()
ma_config = MACrossoverConfig()


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
