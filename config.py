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
class TransactionFeeConfig:
    """
    거래 수수료 설정 클래스
    Transaction Fee Configuration Class
    
    한국 주식 거래 수수료 구조:
    - 매수: 증권사 수수료만
    - 매도: 증권사 수수료 + 거래세 + 농특세
    
    Korean stock transaction fee structure:
    - Buy: Brokerage commission only
    - Sell: Brokerage commission + Securities transaction tax + Agricultural tax
    """
    
    # 증권사 수수료 (Brokerage Commission)
    # 일반적으로 0.015% ~ 0.5% (증권사/거래 유형별 상이)
    # MTS/HTS 기준 약 0.015% ~ 0.05%
    commission_rate: float = float(os.getenv("COMMISSION_RATE", "0.015"))  # 0.015% (한국투자증권 MTS 기준)
    
    # 거래세 (Securities Transaction Tax) - 매도 시에만 부과
    # 코스피: 0.05% (2023년 기준, 향후 인하 예정)
    # 코스닥: 0.20% (2023년 기준)
    tax_rate_kospi: float = float(os.getenv("TAX_RATE_KOSPI", "0.18"))  # 0.18% (거래세 0.03% + 농특세 0.15%)
    tax_rate_kosdaq: float = float(os.getenv("TAX_RATE_KOSDAQ", "0.18"))  # 0.18% (거래세 0.18%, 농특세 없음)
    
    # 기본 시장 (Default Market)
    default_market: str = os.getenv("DEFAULT_MARKET", "kospi")  # "kospi" or "kosdaq"
    
    # 최소 수익률 기준 (수수료 고려)
    # Minimum profit threshold (considering fees)
    # 왕복 수수료를 커버하기 위한 최소 수익률
    min_profit_threshold: float = float(os.getenv("MIN_PROFIT_THRESHOLD", "0.5"))  # 0.5%
    
    # 수수료 고려 매도 활성화
    use_fee_aware_sell: bool = os.getenv("USE_FEE_AWARE_SELL", "true").lower() == "true"
    
    def get_total_buy_fee(self) -> float:
        """
        매수 시 총 수수료율 반환 (%)
        Returns total buy fee rate (%)
        """
        return self.commission_rate
    
    def get_total_sell_fee(self, market: str = None) -> float:
        """
        매도 시 총 수수료율 반환 (%)
        Returns total sell fee rate (%)
        
        Args:
            market: "kospi" or "kosdaq" (None이면 default_market 사용)
        """
        market = market or self.default_market
        tax_rate = self.tax_rate_kospi if market == "kospi" else self.tax_rate_kosdaq
        return self.commission_rate + tax_rate
    
    def get_round_trip_fee(self, market: str = None) -> float:
        """
        왕복 거래 수수료율 반환 (매수 + 매도) (%)
        Returns round-trip fee rate (buy + sell) (%)
        """
        return self.get_total_buy_fee() + self.get_total_sell_fee(market)
    
    def calculate_break_even_rate(self, market: str = None) -> float:
        """
        손익분기 수익률 계산 (%)
        Calculate break-even profit rate (%)
        
        이 수익률 이상이어야 수수료 차감 후 수익 발생
        """
        return self.get_round_trip_fee(market)
    
    def calculate_net_profit(self, entry_price: int, exit_price: int, quantity: int, market: str = None) -> dict:
        """
        순수익 계산 (수수료 차감 후)
        Calculate net profit after fees
        
        Args:
            entry_price: 매수가
            exit_price: 매도가
            quantity: 수량
            market: 시장 구분
        
        Returns:
            dict: {gross_profit, buy_fee, sell_fee, net_profit, net_profit_rate}
        """
        buy_amount = entry_price * quantity
        sell_amount = exit_price * quantity
        
        buy_fee = buy_amount * (self.get_total_buy_fee() / 100)
        sell_fee = sell_amount * (self.get_total_sell_fee(market) / 100)
        
        gross_profit = sell_amount - buy_amount
        net_profit = gross_profit - buy_fee - sell_fee
        net_profit_rate = (net_profit / buy_amount) * 100 if buy_amount > 0 else 0
        
        return {
            "gross_profit": int(gross_profit),
            "buy_fee": int(buy_fee),
            "sell_fee": int(sell_fee),
            "total_fee": int(buy_fee + sell_fee),
            "net_profit": int(net_profit),
            "net_profit_rate": round(net_profit_rate, 2)
        }
    
    def is_profitable_trade(self, entry_price: int, exit_price: int, market: str = None) -> bool:
        """
        수수료 고려 시 수익 거래인지 확인
        Check if trade is profitable after fees
        """
        gross_rate = ((exit_price - entry_price) / entry_price) * 100
        return gross_rate > self.calculate_break_even_rate(market)


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
    chart_period: int = int(os.getenv("CHART_PERIOD", "10"))         # 분봉 주기 (1, 3, 5, 10, 15, 30, 60) - 10분봉 기본
    
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
    batch_size: int = int(os.getenv("BATCH_SIZE", "5"))              # 한 배치당 종목 수 (10분봉용)
    batch_delay: float = float(os.getenv("BATCH_DELAY", "3.0"))      # 배치 간 대기 시간 (초)
    api_delay: float = float(os.getenv("API_DELAY", "1.0"))          # API 호출 간 대기 시간 (초)
    
    # ========================================
    # 분봉 전략 실행 설정 (Minute Strategy Settings)
    # ========================================
    analysis_interval: int = int(os.getenv("ANALYSIS_INTERVAL", "600"))  # 분석 주기 (초) - 10분
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
    KOSPI200_STOCKS: dict = None  # KOSPI 200 주요 종목
    
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
        
        # ========================================
        # KOSPI 200 주요 종목 (KOSPI 200 Major Stocks)
        # 시가총액 상위 100개 대표 종목 (10분봉 사용으로 확장)
        # ========================================
        if self.KOSPI200_STOCKS is None:
            self.KOSPI200_STOCKS = {
                # 대형주 Top 50
                "005930": "삼성전자",
                "000660": "SK하이닉스",
                "005380": "현대차",
                "000270": "기아",
                "005490": "POSCO홀딩스",
                "035420": "NAVER",
                "035720": "카카오",
                "006400": "삼성SDI",
                "051910": "LG화학",
                "373220": "LG에너지솔루션",
                "003670": "포스코퓨처엠",
                "028260": "삼성물산",
                "105560": "KB금융",
                "055550": "신한지주",
                "086790": "하나금융지주",
                "096770": "SK이노베이션",
                "034730": "SK",
                "012330": "현대모비스",
                "066570": "LG전자",
                "003550": "LG",
                "032830": "삼성생명",
                "017670": "SK텔레콤",
                "030200": "KT",
                "000810": "삼성화재",
                "018260": "삼성에스디에스",
                "033780": "KT&G",
                "010130": "고려아연",
                "009150": "삼성전기",
                "011200": "HMM",
                "034020": "두산에너빌리티",
                "010950": "S-Oil",
                "036570": "엔씨소프트",
                "009540": "한국조선해양",
                "011070": "LG이노텍",
                "003490": "대한항공",
                "024110": "기업은행",
                "316140": "우리금융지주",
                "000720": "현대건설",
                "047050": "포스코인터내셔널",
                "015760": "한국전력",
                "090430": "아모레퍼시픽",
                "004020": "현대제철",
                "010140": "삼성중공업",
                "011790": "SKC",
                "267250": "HD현대",
                "009830": "한화솔루션",
                "042660": "한화오션",
                "352820": "하이브",
                "259960": "크래프톤",
                "251270": "넷마블",
                "068270": "셀트리온",
                # 중형주 51-100
                "326030": "SK바이오팜",
                "207940": "삼성바이오로직스",
                "000100": "유한양행",
                "128940": "한미약품",
                "006800": "미래에셋증권",
                "005940": "NH투자증권",
                "016360": "삼성증권",
                "139480": "이마트",
                "004170": "신세계",
                "023530": "롯데쇼핑",
                "069960": "현대백화점",
                "004990": "롯데지주",
                "271560": "오리온",
                "097950": "CJ제일제당",
                "051600": "한전KPS",
                "034220": "LG디스플레이",
                "000150": "두산",
                "009420": "한올바이오파마",
                "180640": "한진칼",
                "002790": "아모레G",
                "051900": "LG생활건강",
                "004800": "효성",
                "006260": "LS",
                "001040": "CJ",
                "000880": "한화",
                "011170": "롯데케미칼",
                # "010620": "현대미포조선",  # 조회 실패
                "241560": "두산밥캣",
                "161390": "한국타이어앤테크놀로지",
                "028050": "삼성엔지니어링",
                "009240": "한샘",
                "005850": "에스엘",
                "000120": "CJ대한통운",
                "071050": "한국금융지주",
                "029780": "삼성카드",
                # "003410": "쌍용C&E",  # 조회 실패
                "001450": "현대해상",
                "000240": "한국앤컴퍼니",
                "002380": "KCC",
                "000070": "삼양홀딩스",
                "005830": "DB손해보험",
                "138930": "BNK금융지주",
                "175330": "JB금융지주",
                "024720": "한국콜마홀딩스",
                "192820": "코스맥스",
                "161890": "한국콜마",
                "039490": "키움증권",
                "001120": "LX인터내셔널",
                # "003620": "쌍용양회",  # 조회 실패
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
        elif group == "kospi200":
            return self.KOSPI200_STOCKS
        elif group == "all":
            # 모든 종목 합치기
            all_stocks = {}
            all_stocks.update(self.COSMETICS_STOCKS)
            all_stocks.update(self.AI_STOCKS)
            all_stocks.update(self.TECH_GIANTS)
            all_stocks.update(self.KOSPI200_STOCKS)
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
class DualMomentumVolatilityConfig:
    """
    듀얼 모멘텀 + 변동성 돌파 전략 설정
    Dual Momentum + Volatility Breakout Strategy Configuration
    
    한국 시장 전체에 적용 가능한 범용 단기 모멘텀 전략
    Universal short-term momentum strategy for Korean market
    """
    
    # ========================================
    # 종목 선별 설정 (Stock Selection)
    # ========================================
    # 유니버스 크기
    universe_size: int = int(os.getenv("DMV_UNIVERSE_SIZE", "200"))  # 시총/거래대금 상위 N개
    
    # 상대 모멘텀 (Relative Momentum)
    momentum_period: int = int(os.getenv("DMV_MOMENTUM_PERIOD", "20"))  # 모멘텀 계산 기간 (일)
    momentum_top_pct: float = float(os.getenv("DMV_MOMENTUM_TOP_PCT", "0.2"))  # 상위 N% 선별
    
    # 절대 모멘텀 (Absolute Momentum)
    ma_period: int = int(os.getenv("DMV_MA_PERIOD", "20"))  # 이평선 기간
    
    # 유동성 필터
    min_trading_value: int = int(os.getenv("DMV_MIN_TRADING_VALUE", "10000000000"))  # 최소 거래대금 (100억)
    
    # 변동성 필터
    min_volatility: float = float(os.getenv("DMV_MIN_VOLATILITY", "15.0"))  # 최소 변동성 %
    max_volatility: float = float(os.getenv("DMV_MAX_VOLATILITY", "40.0"))  # 최대 변동성 %
    
    # 시가총액 필터 (작전주 회피)
    min_market_cap: int = int(os.getenv("DMV_MIN_MARKET_CAP", "50000000000"))  # 최소 시총 (500억)
    
    # ========================================
    # 진입 조건 (Entry Conditions)
    # ========================================
    # 변동성 돌파 계수
    volatility_breakout_k: float = float(os.getenv("DMV_BREAKOUT_K", "0.5"))  # 돌파가 = 전일종가 + (고-저) × K
    
    # 거래량 조건
    volume_multiplier: float = float(os.getenv("DMV_VOLUME_MULT", "1.5"))  # 평균 대비 거래량 배수
    
    # RSI 필터
    rsi_period: int = int(os.getenv("DMV_RSI_PERIOD", "14"))
    rsi_max: int = int(os.getenv("DMV_RSI_MAX", "70"))  # 과매수 회피
    
    # 진입 시간 제한
    entry_start_time: str = os.getenv("DMV_ENTRY_START", "09:30")  # 진입 시작 시간
    entry_end_time: str = os.getenv("DMV_ENTRY_END", "14:30")  # 진입 종료 시간
    
    # ========================================
    # 청산 조건 (Exit Conditions)
    # ========================================
    # 익절 설정
    take_profit_1: float = float(os.getenv("DMV_TP1", "3.0"))  # 1차 익절 % (50% 물량)
    take_profit_2: float = float(os.getenv("DMV_TP2", "5.0"))  # 2차 익절 % (전량)
    
    # 손절 설정
    stop_loss: float = float(os.getenv("DMV_STOP_LOSS", "-2.0"))  # 손절 %
    
    # 시간 청산
    time_exit: str = os.getenv("DMV_TIME_EXIT", "15:20")  # 강제 청산 시간
    
    # ========================================
    # 포지션 관리 (Position Management)
    # ========================================
    max_positions: int = int(os.getenv("DMV_MAX_POSITIONS", "5"))  # 최대 동시 보유 종목
    position_size_pct: float = float(os.getenv("DMV_POSITION_SIZE", "20.0"))  # 종목당 투자 비중 %
    order_quantity: int = int(os.getenv("DMV_ORDER_QTY", "1"))  # 기본 주문 수량
    
    # ========================================
    # 리스크 관리 (Risk Management)
    # ========================================
    # 상한가 종목 회피
    avoid_limit_up: bool = os.getenv("DMV_AVOID_LIMIT_UP", "true").lower() == "true"
    limit_up_threshold: float = float(os.getenv("DMV_LIMIT_UP_THRESHOLD", "25.0"))  # 상한가 임박 %
    
    # 일일 손실 제한
    daily_loss_limit: float = float(os.getenv("DMV_DAILY_LOSS_LIMIT", "-5.0"))  # 일일 최대 손실 %
    
    # ========================================
    # 분석 설정 (Analysis Settings)
    # ========================================
    analysis_interval: int = int(os.getenv("DMV_ANALYSIS_INTERVAL", "60"))  # 분석 주기 (초)
    
    def __post_init__(self):
        """설정 검증"""
        if self.take_profit_1 >= self.take_profit_2:
            raise ValueError("1차 익절은 2차 익절보다 작아야 합니다")
        if self.stop_loss >= 0:
            raise ValueError("손절은 음수여야 합니다")


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
fee_config = TransactionFeeConfig()
ma_config = MACrossoverConfig()
momentum_config = MomentumBreakoutConfig()
dmv_config = DualMomentumVolatilityConfig()


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
    print("-" * 50)
    print("💰 Transaction Fee Settings:")
    print(f"   Commission Rate: {fee_config.commission_rate}%")
    print(f"   Tax Rate (KOSPI): {fee_config.tax_rate_kospi}%")
    print(f"   Tax Rate (KOSDAQ): {fee_config.tax_rate_kosdaq}%")
    print(f"   Round-trip Fee: {fee_config.get_round_trip_fee():.3f}%")
    print(f"   Break-even Rate: {fee_config.calculate_break_even_rate():.3f}%")
    print(f"   Min Profit Threshold: {fee_config.min_profit_threshold}%")
    print("=" * 50)


if __name__ == "__main__":
    # 설정 파일 직접 실행 시 현재 상태 출력
    # Print current status when running config file directly
    print_config_status()
