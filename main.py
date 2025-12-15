"""
main.py - KIS 알고리즘 트레이딩 봇 메인 진입점
KIS Algorithmic Trading Bot Main Entry Point

이 파일은 트레이딩 봇의 메인 실행 파일입니다.
- KIS API 연결 및 인증
- 실시간 WebSocket 시세 구독
- 트레이딩 전략 실행

This file is the main execution file for the trading bot.
- KIS API connection and authentication
- Real-time WebSocket price subscription
- Trading strategy execution
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional, List

from config import kis_config, trading_config, log_config, ma_config, print_config_status
from kis_client import KISClient
from strategy import (
    BaseStrategy, SamsungDipBuyStrategy, SimplePrintStrategy, 
    TickData, MovingAverageCrossoverStrategy, MomentumEventStrategy
)

# ========================================
# 로깅 설정 (Logging Setup)
# ========================================

def setup_logging():
    """
    로깅을 설정합니다.
    Setup logging configuration.
    """
    # 로그 포맷 설정
    formatter = logging.Formatter(
        fmt=log_config.format,
        datefmt=log_config.date_format
    )
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.level.upper()))
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 (설정된 경우)
    if log_config.file_path:
        file_handler = logging.FileHandler(log_config.file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

# 로거 가져오기
logger = logging.getLogger(__name__)


# ========================================
# 트레이딩 봇 클래스 (Trading Bot Class)
# ========================================

class TradingBot:
    """
    KIS 트레이딩 봇 메인 클래스
    KIS Trading Bot Main Class
    
    KIS API 연결, 실시간 시세 구독, 전략 실행을 관리합니다.
    Manages KIS API connection, real-time price subscription, and strategy execution.
    """
    
    def __init__(self):
        """
        트레이딩 봇 초기화
        Initialize trading bot
        """
        self.client: Optional[KISClient] = None
        self.strategy: Optional[BaseStrategy] = None
        self.is_running = False
        self._stop_event = asyncio.Event()
        
        # 실시간 시세 구독 관련
        self.watch_list: List[str] = trading_config.watch_list
        self._websocket_task: Optional[asyncio.Task] = None
        
        logger.info("TradingBot 인스턴스 생성됨 (TradingBot instance created)")
    
    async def initialize(self) -> bool:
        """
        봇을 초기화합니다 (API 연결 등).
        Initialize the bot (API connection, etc.).
        
        Returns:
            bool: 초기화 성공 여부
        """
        logger.info("=" * 50)
        logger.info("🤖 KIS Trading Bot 초기화 중...")
        logger.info("=" * 50)
        
        # KIS 클라이언트 생성 및 연결
        self.client = KISClient()
        
        if not self.client.connect():
            logger.error("❌ KIS API 연결 실패. 봇을 시작할 수 없습니다.")
            return False
        
        logger.info("✅ KIS API 연결 성공!")
        return True
    
    def set_strategy(self, strategy: BaseStrategy):
        """
        실행할 전략을 설정합니다.
        Set the strategy to execute.
        
        Args:
            strategy: 실행할 전략 인스턴스
        """
        self.strategy = strategy
        logger.info(f"전략 설정됨: {strategy.name}")
    
    async def start(self):
        """
        트레이딩 봇을 시작합니다.
        Start the trading bot.
        """
        if self.is_running:
            logger.warning("봇이 이미 실행 중입니다.")
            return
        
        if not self.client or not self.client.is_connected():
            logger.error("KIS API에 연결되어 있지 않습니다. initialize()를 먼저 호출하세요.")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        logger.info("=" * 50)
        logger.info("🚀 KIS Trading Bot 시작!")
        logger.info(f"   모드: {'모의투자' if kis_config.is_virtual else '실전투자'}")
        logger.info(f"   감시 종목: {self.watch_list}")
        logger.info("=" * 50)
        
        # 전략 시작
        if self.strategy:
            self.strategy.start()
        
        # 실시간 시세 폴링 시작 (WebSocket 대안)
        # python-kis의 WebSocket은 별도 구현이 필요하므로
        # 여기서는 폴링 방식으로 시세를 조회합니다.
        await self._run_polling_loop()
    
    async def _run_polling_loop(self):
        """
        실시간 시세 폴링 루프를 실행합니다.
        Run real-time price polling loop.
        
        참고: python-kis 라이브러리는 WebSocket을 직접 지원하지 않을 수 있으므로,
        여기서는 REST API를 주기적으로 호출하는 폴링 방식을 사용합니다.
        실제 프로덕션에서는 WebSocket 구현을 추가하는 것이 좋습니다.
        
        Note: python-kis library may not directly support WebSocket,
        so we use polling method that periodically calls REST API.
        For production, implementing WebSocket is recommended.
        """
        logger.info("📡 실시간 시세 폴링 시작 (2초 간격)...")
        
        poll_interval = 2.0  # 폴링 간격 (초)
        
        try:
            while self.is_running and not self._stop_event.is_set():
                for symbol in self.watch_list:
                    if not self.is_running:
                        break
                    
                    # 현재가 조회
                    price_info = self.client.get_current_price(symbol)
                    
                    if price_info:
                        # TickData 생성 (Decimal을 int/float로 변환)
                        tick = TickData(
                            symbol=price_info["symbol"],
                            price=int(price_info["price"]),
                            change=int(price_info["change"]),
                            change_rate=float(price_info["change_rate"]),
                            volume=int(price_info["volume"]),
                            prev_close=int(price_info["prev_close"]),
                            timestamp=datetime.now()
                        )
                        
                        # 전략에 틱 데이터 전달
                        if self.strategy:
                            self.strategy.process_tick(tick)
                
                # 다음 폴링까지 대기
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=poll_interval
                    )
                except asyncio.TimeoutError:
                    pass  # 타임아웃은 정상 (다음 폴링 실행)
                    
        except asyncio.CancelledError:
            logger.info("폴링 루프가 취소되었습니다.")
        except Exception as e:
            logger.error(f"폴링 루프 오류: {e}")
        finally:
            logger.info("📡 실시간 시세 폴링 종료")
    
    async def stop(self):
        """
        트레이딩 봇을 중지합니다.
        Stop the trading bot.
        """
        if not self.is_running:
            return
        
        logger.info("🛑 트레이딩 봇 중지 중...")
        
        self.is_running = False
        self._stop_event.set()
        
        # 전략 중지
        if self.strategy:
            self.strategy.stop()
        
        # WebSocket 태스크 취소
        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ 트레이딩 봇이 중지되었습니다.")


# ========================================
# 메인 실행 함수 (Main Execution Function)
# ========================================

async def main():
    """
    메인 비동기 함수
    Main async function
    """
    # 로깅 설정
    setup_logging()
    
    # 설정 상태 출력
    print_config_status()
    
    # 트레이딩 봇 생성
    bot = TradingBot()
    
    # 종료 시그널 핸들러 설정
    # Setup shutdown signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("\n⚠️ 종료 신호 수신. 봇을 안전하게 종료합니다...")
        asyncio.create_task(bot.stop())
    
    # SIGINT (Ctrl+C) 및 SIGTERM 처리
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows에서는 add_signal_handler가 지원되지 않을 수 있음
            pass
    
    try:
        # 봇 초기화
        if not await bot.initialize():
            logger.error("봇 초기화 실패. 프로그램을 종료합니다.")
            return
        
        # 전략 선택 및 설정
        # 1. 삼성전자 하락 매수 전략 (실제 매매)
        strategy = SamsungDipBuyStrategy(bot.client)
        
        # 2. 단순 시세 출력 전략 (테스트용)
        # strategy = SimplePrintStrategy(bot.client, symbols=["005930"])
        
        bot.set_strategy(strategy)
        
        # 봇 시작
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 키보드 인터럽트 감지")
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
    finally:
        await bot.stop()
        logger.info("👋 프로그램 종료")


def run_bot():
    """
    봇을 실행합니다 (동기 래퍼).
    Run the bot (synchronous wrapper).
    """
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   🤖 KIS Algorithmic Trading Bot                      ║
    ║   한국투자증권 알고리즘 트레이딩 봇                   ║
    ║                                                       ║
    ║   Press Ctrl+C to stop                                ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 중단되었습니다.")


# ========================================
# 유틸리티 함수 (Utility Functions)
# ========================================

def test_connection():
    """
    API 연결만 테스트합니다.
    Test API connection only.
    """
    setup_logging()
    print_config_status()
    
    print("\n🔌 API 연결 테스트 중...")
    
    client = KISClient()
    if client.connect():
        print("✅ API 연결 성공!")
        
        # 삼성전자 현재가 조회 테스트
        print("\n📈 삼성전자(005930) 현재가 조회 테스트...")
        price = client.get_current_price("005930")
        if price:
            print(f"   종목명: {price['name']}")
            print(f"   현재가: {int(price['price']):,}원")
            print(f"   전일대비: {int(price['change']):+,}원 ({float(price['change_rate']):+.2f}%)")
            print(f"   전일종가: {int(price['prev_close']):,}원")
        
        # 계좌 잔고 조회 테스트
        print("\n💰 계좌 잔고 조회 테스트...")
        balance = client.get_balance()
        if balance:
            print(f"   총 평가금액: {int(balance['total_value']):,}원")
            if balance['stocks']:
                print("   보유 종목:")
                for stock in balance['stocks']:
                    print(f"     - {stock['name']}: {stock['quantity']}주")
        
        return True
    else:
        print("❌ API 연결 실패!")
        print("   config.py에서 API 키와 계좌 정보를 확인하세요.")
        return False


def run_once():
    """
    한 번만 시세를 조회하고 전략 조건을 체크합니다 (테스트용).
    Query price once and check strategy conditions (for testing).
    """
    setup_logging()
    
    print("\n🔍 일회성 시세 조회 및 전략 체크...")
    
    client = KISClient()
    if not client.connect():
        print("❌ API 연결 실패!")
        return
    
    symbol = trading_config.target_stock
    threshold = trading_config.buy_threshold_percent
    
    price_info = client.get_current_price(symbol)
    if not price_info:
        print(f"❌ {symbol} 시세 조회 실패!")
        return
    
    prev_close = int(price_info['prev_close'])
    current_price = int(price_info['price'])
    change_rate = float(price_info['change_rate'])
    trigger_price = int(prev_close * (1 - threshold / 100))
    
    print(f"\n📊 {price_info['name']} ({symbol}) 분석:")
    print(f"   전일 종가: {prev_close:,}원")
    print(f"   현재가: {current_price:,}원")
    print(f"   등락률: {change_rate:+.2f}%")
    print(f"\n🎯 매수 조건 (전일대비 -{threshold}% 이하):")
    print(f"   매수 트리거 가격: {trigger_price:,}원")
    
    if current_price <= trigger_price:
        print(f"   ✅ 조건 충족! (현재가 {current_price:,}원 <= 트리거 {trigger_price:,}원)")
    else:
        diff = current_price - trigger_price
        print(f"   ❌ 조건 미충족 (트리거까지 {diff:,}원 추가 하락 필요)")


def run_ma_crossover(stock_group: str = "cosmetics"):
    """
    MA 크로스오버 전략 일회 실행
    Run MA Crossover Strategy once
    
    Args:
        stock_group: 종목 그룹 ("cosmetics", "ai", "all")
    """
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    # 종목 그룹 이름 매핑
    group_names = {
        "cosmetics": "화장품 관련주",
        "ai": "AI 관련주",
        "all": "전체 종목 (화장품 + AI)"
    }
    group_display = group_names.get(stock_group, stock_group)
    
    # 종목 리스트 가져오기
    stock_list = ma_config.get_stocks(stock_group)
    
    print("\n" + "=" * 60)
    print(f"📊 MA 크로스오버 전략 - {group_display} 분석")
    print("=" * 60)
    
    # 대상 종목 출력
    print(f"\n🎯 대상 종목 ({len(stock_list)}개):")
    for code, name in stock_list.items():
        print(f"   [{code}] {name}")
    print()
    
    # API 연결
    client = KISClient()
    if not client.connect():
        print("❌ API 연결 실패!")
        return
    
    # 전략 생성 및 실행 (종목 리스트 전달)
    strategy = MovingAverageCrossoverStrategy(client, stock_list=stock_list)
    strategy.start()
    
    # 배치 분석 실행 (분봉/일봉 자동 선택)
    results = strategy.run_batch_analysis()
    
    strategy.stop()
    
    return results


def run_ma_scheduler():
    """
    MA 크로스오버 전략 스케줄러 실행 (일봉용)
    Run MA Crossover Strategy with scheduler (for daily charts)
    """
    import schedule
    import time
    
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 60)
    print("📊 MA 크로스오버 전략 스케줄러 (일봉)")
    print(f"   실행 시간: 매일 {ma_config.run_time}")
    print("=" * 60)
    
    # API 연결
    client = KISClient()
    if not client.connect():
        print("❌ API 연결 실패!")
        return
    
    # 전략 생성
    strategy = MovingAverageCrossoverStrategy(client)
    
    def daily_job():
        """일일 분석 작업"""
        logger.info(f"\n⏰ 스케줄된 분석 시작: {datetime.now()}")
        strategy.start()
        strategy.run_batch_analysis()
        strategy.stop()
    
    # 스케줄 등록
    schedule.every().day.at(ma_config.run_time).do(daily_job)
    
    logger.info(f"✅ 스케줄러 시작됨. 다음 실행: {ma_config.run_time}")
    logger.info("   (Ctrl+C로 종료)")
    
    # 스케줄러 루프
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
    except KeyboardInterrupt:
        logger.info("\n👋 스케줄러 종료")


def wait_for_market_open():
    """
    장 시작 시간까지 대기
    Wait until market opens
    """
    import time
    
    logger = logging.getLogger(__name__)
    
    while True:
        now = datetime.now()
        market_open = datetime.strptime(ma_config.market_open, "%H:%M").time()
        market_close = datetime.strptime(ma_config.market_close, "%H:%M").time()
        current_time = now.time()
        
        # 주말 체크
        if now.weekday() >= 5:
            logger.info(f"📅 주말입니다. 월요일 장 시작을 기다립니다...")
            time.sleep(3600)  # 1시간 대기
            continue
        
        # 장 운영 중이면 바로 시작
        if market_open <= current_time <= market_close:
            return True
        
        # 장 시작 전이면 대기
        if current_time < market_open:
            # 남은 시간 계산
            now_dt = datetime.combine(now.date(), current_time)
            open_dt = datetime.combine(now.date(), market_open)
            remaining = (open_dt - now_dt).total_seconds()
            
            if remaining <= 60:
                logger.info(f"⏰ 장 시작까지 {int(remaining)}초 남음...")
                time.sleep(remaining)
                logger.info("🔔 장이 시작되었습니다!")
                return True
            elif remaining <= 300:  # 5분 이내
                logger.info(f"⏰ 장 시작까지 {int(remaining/60)}분 {int(remaining%60)}초 남음...")
                time.sleep(10)
            else:
                minutes = int(remaining / 60)
                logger.info(f"⏰ 장 시작까지 {minutes}분 남음... ({ma_config.market_open} 시작)")
                time.sleep(60)
        else:
            # 장 마감 후
            logger.info(f"📴 장이 마감되었습니다. 내일 장 시작을 기다립니다...")
            return False


def run_momentum_event(stock_group: str = "tech", auto_start: bool = True):
    """
    모멘텀 브레이크아웃 + 이벤트 드리븐 전략 실행
    Run Momentum Breakout + Event-Driven Strategy
    
    Args:
        stock_group: 종목 그룹 ("tech", "cosmetics", "ai", "all")
        auto_start: 장 시작 시 자동 실행 여부
    """
    import time
    
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    # 종목 그룹 이름 매핑
    group_names = {
        "tech": "대형 기술주 (삼성전자, SK하이닉스 등)",
        "cosmetics": "화장품 관련주",
        "ai": "AI 관련주",
        "all": "전체 종목"
    }
    group_display = group_names.get(stock_group, stock_group)
    
    # 종목 리스트 가져오기
    stock_list = ma_config.get_stocks(stock_group)
    
    print("\n" + "=" * 60)
    print(f"🚀 모멘텀 브레이크아웃 + 이벤트 드리븐 전략")
    print(f"   대상: {group_display}")
    print(f"   장 시작 시간: {ma_config.market_open}")
    print(f"   장 마감 시간: {ma_config.market_close}")
    print("=" * 60)
    
    # 대상 종목 출력
    print(f"\n🎯 대상 종목 ({len(stock_list)}개):")
    for code, name in stock_list.items():
        print(f"   [{code}] {name}")
    print()
    
    # API 연결
    client = KISClient()
    if not client.connect():
        print("❌ API 연결 실패!")
        return
    
    # 전략 생성
    strategy = MomentumEventStrategy(client, stock_list=stock_list)
    strategy.start()
    
    def is_market_hours() -> bool:
        """장 운영시간 체크"""
        now = datetime.now()
        market_open = datetime.strptime(ma_config.market_open, "%H:%M").time()
        market_close = datetime.strptime(ma_config.market_close, "%H:%M").time()
        current_time = now.time()
        
        # 주말 체크
        if now.weekday() >= 5:
            return False
        
        return market_open <= current_time <= market_close
    
    # 장 시작 대기 (auto_start가 True일 때)
    if auto_start:
        logger.info("⏳ 장 시작 시간까지 대기 중...")
        if not wait_for_market_open():
            logger.info("장이 마감되었습니다. 프로그램을 종료합니다.")
            strategy.stop()
            return
        
        # 장 시작 직후 즉시 첫 분석 실행
        logger.info("🔔 장 시작! 즉시 첫 분석을 실행합니다!")
    
    logger.info("✅ 모멘텀 + 이벤트 전략 활성화됨")
    logger.info(f"   분석 간격: {ma_config.analysis_interval}초")
    logger.info("   (Ctrl+C로 종료)")
    
    analysis_count = 0
    
    try:
        while True:
            if is_market_hours():
                analysis_count += 1
                logger.info(f"\n🔄 분석 #{analysis_count} 시작...")
                
                # 분석 실행
                results = strategy.run_analysis()
                
                logger.info(f"   다음 분석까지 {ma_config.analysis_interval}초 대기...")
                time.sleep(ma_config.analysis_interval)
            else:
                now = datetime.now()
                logger.info(f"⏸️ 장외 시간 ({now.strftime('%H:%M')}) - 장 시작 대기...")
                
                # 장 시작 대기
                if not wait_for_market_open():
                    break
                
    except KeyboardInterrupt:
        logger.info("\n👋 모멘텀 + 이벤트 전략 종료")
        strategy.stop()
        
        logger.info(f"📊 총 분석 횟수: {analysis_count}회")


def run_all_strategies():
    """
    모든 전략을 장 시작과 동시에 자동 실행
    Run all strategies automatically at market open
    
    대형 기술주: 모멘텀 + 이벤트 드리븐
    중소형주: MA 크로스오버
    """
    import time
    import threading
    
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 60)
    print("🚀 통합 자동 트레이딩 시스템")
    print("=" * 60)
    print("\n실행할 전략:")
    print("   1️⃣ 모멘텀 + 이벤트 드리븐 (대형 기술주)")
    print("   2️⃣ MA 크로스오버 (화장품주)")
    print("   3️⃣ MA 크로스오버 (AI주)")
    print("=" * 60)
    
    # API 연결
    client = KISClient()
    if not client.connect():
        print("❌ API 연결 실패!")
        return
    
    # 전략들 생성
    tech_stocks = ma_config.get_stocks("tech")
    cosmetics_stocks = ma_config.get_stocks("cosmetics")
    ai_stocks = ma_config.get_stocks("ai")
    
    strategies = [
        ("모멘텀+이벤트 (대형기술주)", MomentumEventStrategy(client, stock_list=tech_stocks)),
        ("MA크로스오버 (화장품주)", MovingAverageCrossoverStrategy(client, stock_list=cosmetics_stocks)),
        ("MA크로스오버 (AI주)", MovingAverageCrossoverStrategy(client, stock_list=ai_stocks)),
    ]
    
    print(f"\n📊 총 {len(strategies)}개 전략 준비 완료")
    
    # 장 시작 대기
    logger.info("⏳ 장 시작 시간까지 대기 중...")
    if not wait_for_market_open():
        logger.info("장이 마감되었습니다. 프로그램을 종료합니다.")
        return
    
    logger.info("🔔 장 시작! 모든 전략을 실행합니다!")
    
    # 모든 전략 시작
    for name, strategy in strategies:
        strategy.start()
        logger.info(f"   ✅ {name} 활성화")
    
    def is_market_hours() -> bool:
        now = datetime.now()
        market_open = datetime.strptime(ma_config.market_open, "%H:%M").time()
        market_close = datetime.strptime(ma_config.market_close, "%H:%M").time()
        current_time = now.time()
        if now.weekday() >= 5:
            return False
        return market_open <= current_time <= market_close
    
    analysis_count = 0
    
    try:
        while True:
            if is_market_hours():
                analysis_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🔄 통합 분석 #{analysis_count} 시작...")
                logger.info(f"{'='*60}")
                
                # 각 전략 순차 실행 (API Rate Limit 고려)
                for name, strategy in strategies:
                    logger.info(f"\n📊 [{name}] 분석 중...")
                    
                    if isinstance(strategy, MomentumEventStrategy):
                        strategy.run_analysis()
                    else:
                        strategy.run_batch_analysis()
                    
                    # 전략 간 딜레이
                    time.sleep(2)
                
                logger.info(f"\n   다음 분석까지 {ma_config.analysis_interval}초 대기...")
                time.sleep(ma_config.analysis_interval)
            else:
                now = datetime.now()
                logger.info(f"⏸️ 장외 시간 ({now.strftime('%H:%M')}) - 장 시작 대기...")
                
                if not wait_for_market_open():
                    break
                
    except KeyboardInterrupt:
        logger.info("\n👋 통합 트레이딩 시스템 종료")
        for name, strategy in strategies:
            strategy.stop()
        
        logger.info(f"📊 총 분석 횟수: {analysis_count}회")


def run_ma_minute(stock_group: str = "cosmetics"):
    """
    분봉 MA 크로스오버 전략 연속 실행
    Run minute-based MA Crossover Strategy continuously
    
    Args:
        stock_group: 종목 그룹 ("cosmetics", "ai", "all")
    
    장 운영시간(09:00~15:30) 동안 지정된 간격으로 분석 실행
    Runs analysis at specified intervals during market hours
    """
    import time
    
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    # 종목 그룹 이름 매핑
    group_names = {
        "cosmetics": "화장품 관련주",
        "ai": "AI 관련주",
        "all": "전체 종목 (화장품 + AI)"
    }
    group_display = group_names.get(stock_group, stock_group)
    
    # 종목 리스트 가져오기
    stock_list = ma_config.get_stocks(stock_group)
    
    print("\n" + "=" * 60)
    print(f"📊 분봉 MA 크로스오버 전략 (연속 실행) - {group_display}")
    print(f"   차트: {ma_config.chart_period}분봉")
    print(f"   분석 간격: {ma_config.analysis_interval}초")
    print(f"   배치 크기: {ma_config.batch_size}개씩")
    print(f"   장 운영시간: {ma_config.market_open} ~ {ma_config.market_close}")
    print("=" * 60)
    
    # 대상 종목 출력
    print(f"\n🎯 대상 종목 ({len(stock_list)}개):")
    for code, name in stock_list.items():
        print(f"   [{code}] {name}")
    print()
    
    # API 연결
    client = KISClient()
    if not client.connect():
        print("❌ API 연결 실패!")
        return
    
    # 전략 생성 (종목 리스트 전달)
    strategy = MovingAverageCrossoverStrategy(client, stock_list=stock_list)
    strategy.start()
    
    def is_market_hours() -> bool:
        """장 운영시간 체크"""
        now = datetime.now()
        market_open = datetime.strptime(ma_config.market_open, "%H:%M").time()
        market_close = datetime.strptime(ma_config.market_close, "%H:%M").time()
        current_time = now.time()
        
        # 주말 체크 (0=월, 6=일)
        if now.weekday() >= 5:
            return False
        
        return market_open <= current_time <= market_close
    
    logger.info("✅ 분봉 전략 시작됨")
    logger.info(f"   분석 간격: {ma_config.analysis_interval}초")
    logger.info("   (Ctrl+C로 종료)")
    
    analysis_count = 0
    
    try:
        while True:
            if is_market_hours():
                analysis_count += 1
                logger.info(f"\n🔄 분석 #{analysis_count} 시작...")
                
                # 배치 분석 실행
                results = strategy.run_batch_analysis()
                
                logger.info(f"   다음 분석까지 {ma_config.analysis_interval}초 대기...")
                time.sleep(ma_config.analysis_interval)
            else:
                # 장외 시간
                now = datetime.now()
                logger.info(f"⏸️ 장외 시간 ({now.strftime('%H:%M')}) - 1분 후 재확인...")
                time.sleep(60)
                
    except KeyboardInterrupt:
        logger.info("\n👋 분봉 전략 종료")
        strategy.stop()
        
        # 최종 결과 출력
        logger.info(f"📊 총 분석 횟수: {analysis_count}회")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="KIS 알고리즘 트레이딩 봇 (KIS Algorithmic Trading Bot)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="API 연결만 테스트합니다 (Test API connection only)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="일회성 시세 조회 및 전략 체크 (One-time price query and strategy check)"
    )
    parser.add_argument(
        "--ma",
        action="store_true",
        help="MA 크로스오버 전략 일회 실행 (Run MA Crossover once)"
    )
    parser.add_argument(
        "--ma-schedule",
        action="store_true",
        help="MA 크로스오버 전략 스케줄러 실행 - 일봉 (Run MA Crossover with scheduler - daily)"
    )
    parser.add_argument(
        "--ma-minute",
        action="store_true",
        help="분봉 MA 크로스오버 전략 연속 실행 (Run minute MA Crossover continuously)"
    )
    parser.add_argument(
        "--momentum",
        action="store_true",
        help="모멘텀 브레이크아웃 + 이벤트 드리븐 전략 (Momentum Breakout + Event-Driven Strategy)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="run_all",
        help="모든 전략 장 시작과 동시 자동 실행 (Run ALL strategies at market open)"
    )
    parser.add_argument(
        "--stocks",
        type=str,
        choices=["cosmetics", "ai", "tech", "all"],
        default="tech",
        help="종목 그룹: tech(대형기술주), cosmetics(화장품), ai(AI), all(전체)"
    )
    
    args = parser.parse_args()
    
    if args.test:
        test_connection()
    elif args.once:
        run_once()
    elif args.ma:
        run_ma_crossover(stock_group=args.stocks)
    elif args.ma_schedule:
        run_ma_scheduler()
    elif args.ma_minute:
        run_ma_minute(stock_group=args.stocks)
    elif args.momentum:
        run_momentum_event(stock_group=args.stocks)
    elif args.run_all:
        run_all_strategies()
    else:
        # 기본: 모멘텀 + 이벤트 전략 (대형 기술주)
        run_momentum_event(stock_group="tech")
