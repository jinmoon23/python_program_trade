"""
strategy.py - 트레이딩 전략 기본 클래스 및 예제 전략
Trading Strategy Base Class and Example Strategies

이 파일은 트레이딩 전략의 기본 구조를 정의하고,
삼성전자 하락 매수 전략 예제를 포함합니다.

This file defines the base structure for trading strategies
and includes a Samsung Electronics dip-buying strategy example.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from kis_client import KISClient
from config import trading_config, ma_config

# 로거 설정
# Logger setup
logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """
    실시간 틱 데이터 클래스
    Real-time Tick Data Class
    
    WebSocket이나 폴링을 통해 받은 시세 데이터를 표준화합니다.
    Standardizes price data received via WebSocket or polling.
    """
    symbol: str           # 종목 코드 (Stock code)
    price: int            # 현재가 (Current price)
    change: int           # 전일 대비 (Change from previous close)
    change_rate: float    # 등락률 % (Change rate %)
    volume: int           # 거래량 (Volume)
    prev_close: int       # 전일 종가 (Previous close)
    timestamp: datetime   # 수신 시간 (Received time)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TickData":
        """딕셔너리에서 TickData 생성 (Create TickData from dictionary)"""
        return cls(
            symbol=data.get("symbol", ""),
            price=data.get("price", 0),
            change=data.get("change", 0),
            change_rate=data.get("change_rate", 0.0),
            volume=data.get("volume", 0),
            prev_close=data.get("prev_close", 0),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
        )


class BaseStrategy(ABC):
    """
    트레이딩 전략 기본 클래스 (추상 클래스)
    Trading Strategy Base Class (Abstract Class)
    
    모든 트레이딩 전략은 이 클래스를 상속받아 구현합니다.
    All trading strategies should inherit from this class.
    
    주요 메서드:
    - on_start(): 전략 시작 시 호출
    - on_tick(): 새로운 시세 데이터 수신 시 호출
    - on_order_filled(): 주문 체결 시 호출
    - on_stop(): 전략 종료 시 호출
    
    Main methods:
    - on_start(): Called when strategy starts
    - on_tick(): Called when new price data is received
    - on_order_filled(): Called when order is filled
    - on_stop(): Called when strategy stops
    """
    
    def __init__(self, client: KISClient, name: str = "BaseStrategy"):
        """
        전략 초기화
        Initialize strategy
        
        Args:
            client: KISClient 인스턴스
            name: 전략 이름
        """
        self.client = client
        self.name = name
        self.is_running = False
        self._order_count = 0  # 주문 횟수 추적 (Order count tracking)
        
        logger.info(f"전략 '{self.name}' 초기화됨 (Strategy '{self.name}' initialized)")
    
    def start(self):
        """
        전략을 시작합니다.
        Start the strategy.
        """
        if self.is_running:
            logger.warning(f"전략 '{self.name}'이 이미 실행 중입니다.")
            return
        
        self.is_running = True
        logger.info(f"🚀 전략 '{self.name}' 시작! (Strategy '{self.name}' started!)")
        self.on_start()
    
    def stop(self):
        """
        전략을 중지합니다.
        Stop the strategy.
        """
        if not self.is_running:
            logger.warning(f"전략 '{self.name}'이 실행 중이 아닙니다.")
            return
        
        self.is_running = False
        self.on_stop()
        logger.info(f"🛑 전략 '{self.name}' 중지됨 (Strategy '{self.name}' stopped)")
    
    def process_tick(self, tick: TickData):
        """
        틱 데이터를 처리합니다 (내부용).
        Process tick data (internal use).
        
        Args:
            tick: 틱 데이터
        """
        if not self.is_running:
            return
        
        try:
            self.on_tick(tick)
        except Exception as e:
            logger.error(f"on_tick 처리 중 오류 발생: {e}")
    
    # ========================================
    # 추상 메서드 (Abstract Methods) - 반드시 구현 필요
    # ========================================
    
    @abstractmethod
    def on_start(self):
        """
        전략 시작 시 호출됩니다.
        Called when strategy starts.
        
        초기화 로직을 여기에 구현하세요.
        Implement initialization logic here.
        """
        pass
    
    @abstractmethod
    def on_tick(self, tick: TickData):
        """
        새로운 시세 데이터 수신 시 호출됩니다.
        Called when new price data is received.
        
        매매 로직을 여기에 구현하세요.
        Implement trading logic here.
        
        Args:
            tick: 실시간 틱 데이터
        """
        pass
    
    # ========================================
    # 선택적 오버라이드 메서드 (Optional Override Methods)
    # ========================================
    
    def on_stop(self):
        """
        전략 종료 시 호출됩니다.
        Called when strategy stops.
        
        정리 로직을 여기에 구현하세요.
        Implement cleanup logic here.
        """
        pass
    
    def on_order_filled(self, order_info: Dict[str, Any]):
        """
        주문 체결 시 호출됩니다.
        Called when order is filled.
        
        Args:
            order_info: 체결 정보
        """
        pass


class SamsungDipBuyStrategy(BaseStrategy):
    """
    삼성전자 하락 매수 전략
    Samsung Electronics Dip-Buying Strategy
    
    전략 로직:
    1. 삼성전자(005930) 실시간 시세를 감시
    2. 전일 종가 대비 설정된 비율(기본 5%) 이상 하락 시
    3. 시장가로 설정된 수량(기본 1주) 매수
    4. 최대 보유 수량을 초과하지 않도록 관리
    
    Strategy logic:
    1. Monitor Samsung Electronics (005930) real-time price
    2. When price drops more than threshold (default 5%) from previous close
    3. Place market buy order for configured quantity (default 1 share)
    4. Manage position to not exceed maximum quantity
    """
    
    def __init__(
        self,
        client: KISClient,
        symbol: str = None,
        threshold_percent: float = None,
        quantity: int = None,
        max_position: int = None
    ):
        """
        삼성전자 하락 매수 전략 초기화
        Initialize Samsung Dip-Buy Strategy
        
        Args:
            client: KISClient 인스턴스
            symbol: 종목 코드 (기본: config에서 로드)
            threshold_percent: 매수 트리거 하락률 (기본: config에서 로드)
            quantity: 주문 수량 (기본: config에서 로드)
            max_position: 최대 보유 수량 (기본: config에서 로드)
        """
        super().__init__(client, name="SamsungDipBuyStrategy")
        
        # 설정값 로드 (config 또는 파라미터에서)
        # Load settings (from config or parameters)
        self.symbol = symbol or trading_config.target_stock
        self.threshold_percent = threshold_percent or trading_config.buy_threshold_percent
        self.quantity = quantity or trading_config.quantity
        self.max_position = max_position or trading_config.max_position
        
        # 전략 상태 변수
        # Strategy state variables
        self.prev_close: Optional[int] = None  # 전일 종가
        self.buy_trigger_price: Optional[int] = None  # 매수 트리거 가격
        self.last_tick: Optional[TickData] = None  # 마지막 틱 데이터
        self.total_bought: int = 0  # 이 세션에서 매수한 총 수량
        
        logger.info(f"📊 전략 설정:")
        logger.info(f"   종목: {self.symbol}")
        logger.info(f"   매수 트리거: -{self.threshold_percent}%")
        logger.info(f"   주문 수량: {self.quantity}주")
        logger.info(f"   최대 보유: {self.max_position}주")
    
    def on_start(self):
        """
        전략 시작 시 전일 종가를 조회하고 매수 트리거 가격을 계산합니다.
        On start, fetch previous close and calculate buy trigger price.
        """
        logger.info(f"📈 {self.symbol} 전일 종가 조회 중...")
        
        # 전일 종가 조회
        # Fetch previous close
        price_info = self.client.get_current_price(self.symbol)
        
        if price_info:
            self.prev_close = int(price_info["prev_close"])
            current_price = int(price_info["price"])
            
            # 매수 트리거 가격 계산: 전일 종가 * (1 - 하락률/100)
            # Calculate buy trigger: prev_close * (1 - threshold/100)
            self.buy_trigger_price = int(self.prev_close * (1 - self.threshold_percent / 100))
            
            logger.info(f"✅ 전일 종가: {self.prev_close:,}원")
            logger.info(f"✅ 현재가: {current_price:,}원")
            logger.info(f"🎯 매수 트리거 가격: {self.buy_trigger_price:,}원 (-{self.threshold_percent}%)")
        else:
            logger.error("❌ 전일 종가 조회 실패. 전략을 시작할 수 없습니다.")
            self.stop()
    
    def on_tick(self, tick: TickData):
        """
        실시간 틱 데이터 수신 시 매매 로직을 실행합니다.
        Execute trading logic when real-time tick data is received.
        
        Args:
            tick: 실시간 틱 데이터
        """
        # 해당 종목이 아니면 무시
        if tick.symbol != self.symbol:
            return
        
        self.last_tick = tick
        
        # 실시간 가격 출력
        # Print real-time price
        change_symbol = "▲" if tick.change > 0 else "▼" if tick.change < 0 else "─"
        logger.info(
            f"📊 [{tick.symbol}] {tick.price:,}원 "
            f"{change_symbol} {abs(tick.change):,}원 ({tick.change_rate:+.2f}%) "
            f"| 거래량: {tick.volume:,}"
        )
        
        # 매수 트리거 가격이 설정되지 않았으면 무시
        if self.buy_trigger_price is None:
            logger.warning("매수 트리거 가격이 설정되지 않았습니다.")
            return
        
        # 매수 조건 체크
        # Check buy condition
        if tick.price <= self.buy_trigger_price:
            self._try_buy(tick)
    
    def _try_buy(self, tick: TickData):
        """
        매수 조건 충족 시 매수를 시도합니다.
        Attempt to buy when buy condition is met.
        
        Args:
            tick: 현재 틱 데이터
        """
        logger.info(f"🔔 매수 조건 충족! 현재가 {tick.price:,}원 <= 트리거 {self.buy_trigger_price:,}원")
        
        # 현재 보유 수량 확인
        # Check current position
        current_position = self.client.get_position(self.symbol)
        
        if current_position >= self.max_position:
            logger.warning(
                f"⚠️ 최대 보유 수량 도달. "
                f"현재: {current_position}주, 최대: {self.max_position}주"
            )
            return
        
        # 주문 가능 수량 계산
        # Calculate orderable quantity
        available_qty = min(self.quantity, self.max_position - current_position)
        
        if available_qty <= 0:
            logger.warning("주문 가능 수량이 없습니다.")
            return
        
        # 시장가 매수 주문 실행
        # Execute market buy order
        logger.info(f"📝 시장가 매수 주문 실행: {self.symbol} {available_qty}주")
        
        order = self.client.buy_market_order(self.symbol, available_qty)
        
        if order:
            self.total_bought += available_qty
            self._order_count += 1
            logger.info(f"✅ 주문 성공! 이 세션 총 매수: {self.total_bought}주")
        else:
            logger.error("❌ 주문 실패!")
    
    def on_stop(self):
        """
        전략 종료 시 요약을 출력합니다.
        Print summary when strategy stops.
        """
        logger.info("=" * 50)
        logger.info(f"📊 전략 '{self.name}' 실행 요약:")
        logger.info(f"   총 주문 횟수: {self._order_count}회")
        logger.info(f"   총 매수 수량: {self.total_bought}주")
        if self.last_tick:
            logger.info(f"   마지막 가격: {self.last_tick.price:,}원")
        logger.info("=" * 50)


class SimplePrintStrategy(BaseStrategy):
    """
    단순 시세 출력 전략 (테스트/디버깅용)
    Simple Price Print Strategy (for testing/debugging)
    
    모든 수신된 틱 데이터를 콘솔에 출력합니다.
    Prints all received tick data to console.
    """
    
    def __init__(self, client: KISClient, symbols: list = None):
        """
        초기화
        Initialize
        
        Args:
            client: KISClient 인스턴스
            symbols: 감시할 종목 목록 (None이면 모든 종목)
        """
        super().__init__(client, name="SimplePrintStrategy")
        self.symbols = symbols
        self.tick_count = 0
    
    def on_start(self):
        """전략 시작"""
        logger.info(f"👀 시세 감시 시작. 종목: {self.symbols or '전체'}")
    
    def on_tick(self, tick: TickData):
        """
        틱 데이터를 출력합니다.
        Print tick data.
        """
        # 특정 종목만 감시하는 경우 필터링
        if self.symbols and tick.symbol not in self.symbols:
            return
        
        self.tick_count += 1
        
        # 가격 변동 방향 이모지
        if tick.change > 0:
            direction = "🔴"  # 상승
        elif tick.change < 0:
            direction = "🔵"  # 하락
        else:
            direction = "⚪"  # 보합
        
        print(
            f"{direction} [{tick.timestamp.strftime('%H:%M:%S')}] "
            f"{tick.symbol}: {tick.price:,}원 "
            f"({tick.change_rate:+.2f}%) "
            f"Vol: {tick.volume:,}"
        )
    
    def on_stop(self):
        """전략 종료"""
        logger.info(f"📊 총 수신 틱: {self.tick_count}개")


# ============================================================
# 이동평균선 크로스오버 전략 (Moving Average Crossover Strategy)
# ============================================================

class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    이동평균선 크로스오버 전략 (골든크로스 / 데드크로스)
    Moving Average Crossover Strategy (Golden Cross / Death Cross)
    
    전략 로직:
    1. 여러 종목의 일봉 데이터를 조회
    2. 단기 이평선(20일)과 장기 이평선(60일) 계산
    3. 골든크로스 (단기 > 장기 돌파) + RSI < 70 → 매수
    4. 데드크로스 (단기 < 장기 돌파) + RSI > 30 → 매도
    5. 종목당 1주 보유, 일 1회 실행
    
    Strategy Logic:
    1. Fetch daily OHLCV data for multiple stocks
    2. Calculate short SMA (20-day) and long SMA (60-day)
    3. Golden Cross (short crosses above long) + RSI < 70 → Buy
    4. Death Cross (short crosses below long) + RSI > 30 → Sell
    5. Hold 1 share per stock, run once daily
    """
    
    def __init__(
        self,
        client: KISClient,
        stock_list: dict = None,
        short_ma: int = None,
        long_ma: int = None,
        rsi_period: int = None,
        rsi_overbought: int = None,
        rsi_oversold: int = None,
        order_quantity: int = None
    ):
        """
        이동평균선 크로스오버 전략 초기화
        Initialize MA Crossover Strategy
        
        Args:
            client: KISClient 인스턴스
            stock_list: 대상 종목 딕셔너리 {코드: 이름}
            short_ma: 단기 이평선 기간 (기본: 20일)
            long_ma: 장기 이평선 기간 (기본: 60일)
            rsi_period: RSI 기간 (기본: 14일)
            rsi_overbought: 과매수 기준 (기본: 70)
            rsi_oversold: 과매도 기준 (기본: 30)
            order_quantity: 주문 수량 (기본: 1주)
        """
        super().__init__(client, name="MACrossoverStrategy")
        
        # 설정값 로드 (config 또는 파라미터에서)
        self.stock_list = stock_list or ma_config.COSMETICS_STOCKS
        self.short_ma = short_ma or ma_config.short_ma_period
        self.long_ma = long_ma or ma_config.long_ma_period
        self.rsi_period = rsi_period or ma_config.rsi_period
        self.rsi_overbought = rsi_overbought or ma_config.rsi_overbought
        self.rsi_oversold = rsi_oversold or ma_config.rsi_oversold
        self.order_quantity = order_quantity or ma_config.order_quantity
        self.lookback_days = ma_config.lookback_days
        
        # 각 종목별 이전 신호 상태 저장 (크로스오버 감지용)
        # Store previous signal state for each stock (for crossover detection)
        self._prev_signals: Dict[str, str] = {}  # 'golden', 'death', or None
        
        # 신호 쿨다운 추적 (노이즈 필터)
        self._last_signal_time: Dict[str, datetime] = {}
        
        # 포지션 추적 (손절/익절용) - {symbol: {"entry_price": int, "quantity": int, "entry_time": datetime}}
        self._positions: Dict[str, Dict] = {}
        
        # 매매 결과 추적
        self.signals_generated = 0
        self.orders_placed = 0
        self.stop_loss_triggered = 0
        self.take_profit_triggered = 0
        
        logger.info("=" * 50)
        logger.info("📊 MA 크로스오버 전략 설정:")
        logger.info(f"   대상 종목: {len(self.stock_list)}개")
        logger.info(f"   단기 이평선: {self.short_ma}일")
        logger.info(f"   장기 이평선: {self.long_ma}일")
        logger.info(f"   RSI 기간: {self.rsi_period}일")
        logger.info(f"   RSI 과매수/과매도: {self.rsi_overbought}/{self.rsi_oversold}")
        logger.info(f"   주문 수량: {self.order_quantity}주")
        logger.info("=" * 50)
    
    def on_start(self):
        """전략 시작 (일일 실행 시 호출)"""
        chart_type = "분봉" if ma_config.use_minute_chart else "일봉"
        logger.info("🚀 MA 크로스오버 전략 시작...")
        logger.info(f"   분석 대상: {len(self.stock_list)}개 종목")
        logger.info(f"   차트 타입: {ma_config.chart_period}{chart_type}")
        logger.info(f"   배치 크기: {ma_config.batch_size}개씩")
    
    def on_tick(self, tick: TickData):
        """실시간 틱 처리 (이 전략에서는 사용하지 않음)"""
        pass
    
    def run_batch_analysis(self) -> Dict[str, Any]:
        """
        배치 기반 분석 실행 - Rate Limit 방지를 위해 배치로 처리
        Run batch-based analysis - Process in batches to avoid rate limits
        
        분봉/일봉 모두 지원, 설정에 따라 자동 선택
        Supports both minute and daily charts, auto-selected by config
        
        Returns:
            dict: 분석 결과 요약
        """
        import time
        
        use_minute = ma_config.use_minute_chart
        chart_type = f"{ma_config.chart_period}분봉" if use_minute else "일봉"
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 MA 크로스오버 배치 분석 시작 ({chart_type})")
        logger.info(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   배치 크기: {ma_config.batch_size}개 | 배치 간격: {ma_config.batch_delay}초")
        logger.info("=" * 60)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "chart_type": chart_type,
            "stocks_analyzed": 0,
            "buy_signals": [],
            "sell_signals": [],
            "orders_placed": [],
            "errors": []
        }
        
        # 종목 리스트를 배치로 분할
        stock_items = list(self.stock_list.items())
        batch_size = ma_config.batch_size
        batches = [stock_items[i:i + batch_size] for i in range(0, len(stock_items), batch_size)]
        
        logger.info(f"   총 {len(batches)}개 배치로 처리 예정")
        
        for batch_idx, batch in enumerate(batches):
            logger.info(f"\n📦 배치 {batch_idx + 1}/{len(batches)} 처리 중...")
            
            for symbol, name in batch:
                try:
                    logger.info(f"\n📈 [{symbol}] {name} 분석 중...")
                    
                    # API 호출 간격 조절
                    time.sleep(ma_config.api_delay)
                    
                    # 차트 데이터 조회 (분봉 또는 일봉)
                    if use_minute:
                        df = self.client.get_minute_chart_df(symbol, period=ma_config.chart_period)
                    else:
                        df = self.client.get_daily_prices_df(symbol, count=self.lookback_days)
                    
                    if df is None or df.empty:
                        logger.warning(f"   ⚠️ 데이터 조회 실패")
                        results["errors"].append({"symbol": symbol, "error": "데이터 조회 실패"})
                        continue
                    
                    if len(df) < self.long_ma:
                        logger.warning(f"   ⚠️ 데이터 부족 ({len(df)}개 < {self.long_ma}개)")
                        results["errors"].append({"symbol": symbol, "error": "데이터 부족"})
                        continue
                    
                    # 기술적 지표 계산
                    indicators = self._calculate_indicators(df)
                    
                    if indicators is None:
                        logger.warning(f"   ⚠️ 지표 계산 실패")
                        continue
                    
                    # 현재 상태 출력
                    self._print_stock_status(symbol, name, indicators)
                    
                    # ========================================
                    # 1단계: 손절/익절 체크 (보유 중인 종목)
                    # ========================================
                    current_price = indicators["close"]
                    sl_tp_signal = self.check_stop_loss_take_profit(symbol, current_price)
                    
                    if sl_tp_signal:
                        # 손절 또는 익절 실행
                        order_result = self._execute_sell(symbol, name, indicators, reason=sl_tp_signal)
                        if order_result:
                            results["orders_placed"].append(order_result)
                            if sl_tp_signal == "STOP_LOSS":
                                results.setdefault("stop_losses", []).append(order_result)
                            else:
                                results.setdefault("take_profits", []).append(order_result)
                        results["stocks_analyzed"] += 1
                        continue  # SL/TP 발동 시 추가 신호 체크 스킵
                    
                    # ========================================
                    # 2단계: MA 크로스오버 신호 체크
                    # ========================================
                    signal = self._check_signal(symbol, indicators)
                    
                    if signal == "BUY":
                        results["buy_signals"].append({
                            "symbol": symbol, "name": name,
                            "price": indicators["close"],
                            "short_ma": indicators["short_ma"],
                            "long_ma": indicators["long_ma"],
                            "rsi": indicators["rsi"]
                        })
                        order_result = self._execute_buy(symbol, name, indicators)
                        if order_result:
                            results["orders_placed"].append(order_result)
                    
                    elif signal == "SELL":
                        results["sell_signals"].append({
                            "symbol": symbol, "name": name,
                            "price": indicators["close"],
                            "short_ma": indicators["short_ma"],
                            "long_ma": indicators["long_ma"],
                            "rsi": indicators["rsi"]
                        })
                        order_result = self._execute_sell(symbol, name, indicators, reason="SIGNAL")
                        if order_result:
                            results["orders_placed"].append(order_result)
                    
                    results["stocks_analyzed"] += 1
                    
                except Exception as e:
                    logger.error(f"   ❌ 분석 오류: {e}")
                    results["errors"].append({"symbol": symbol, "error": str(e)})
            
            # 배치 간 대기 (마지막 배치 제외)
            if batch_idx < len(batches) - 1:
                logger.info(f"   ⏳ 다음 배치까지 {ma_config.batch_delay}초 대기...")
                time.sleep(ma_config.batch_delay)
        
        # 결과 요약 출력
        self._print_summary(results)
        
        return results
    
    def run_daily_analysis(self) -> Dict[str, Any]:
        """
        일일 분석 실행 - 모든 종목에 대해 신호 체크 및 주문
        Run daily analysis - Check signals and place orders for all stocks
        
        Returns:
            dict: 분석 결과 요약
        """
        import pandas as pd
        import time
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 일일 MA 크로스오버 분석 시작")
        logger.info(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "stocks_analyzed": 0,
            "buy_signals": [],
            "sell_signals": [],
            "orders_placed": [],
            "errors": []
        }
        
        for symbol, name in self.stock_list.items():
            try:
                logger.info(f"\n📈 [{symbol}] {name} 분석 중...")
                
                # API 호출 간격 조절 (Rate limit 방지)
                time.sleep(0.5)
                
                # 일봉 데이터 조회
                df = self.client.get_daily_prices_df(symbol, count=self.lookback_days)
                
                if df is None or df.empty:
                    logger.warning(f"   ⚠️ 일봉 데이터 조회 실패")
                    results["errors"].append({"symbol": symbol, "error": "데이터 조회 실패"})
                    continue
                
                if len(df) < self.long_ma:
                    logger.warning(f"   ⚠️ 데이터 부족 ({len(df)}일 < {self.long_ma}일)")
                    results["errors"].append({"symbol": symbol, "error": f"데이터 부족"})
                    continue
                
                # 기술적 지표 계산
                indicators = self._calculate_indicators(df)
                
                if indicators is None:
                    logger.warning(f"   ⚠️ 지표 계산 실패")
                    continue
                
                # 현재 상태 출력
                self._print_stock_status(symbol, name, indicators)
                
                # 신호 확인
                signal = self._check_signal(symbol, indicators)
                
                if signal == "BUY":
                    results["buy_signals"].append({
                        "symbol": symbol,
                        "name": name,
                        "price": indicators["close"],
                        "short_ma": indicators["short_ma"],
                        "long_ma": indicators["long_ma"],
                        "rsi": indicators["rsi"]
                    })
                    
                    # 매수 주문 실행
                    order_result = self._execute_buy(symbol, name, indicators)
                    if order_result:
                        results["orders_placed"].append(order_result)
                
                elif signal == "SELL":
                    results["sell_signals"].append({
                        "symbol": symbol,
                        "name": name,
                        "price": indicators["close"],
                        "short_ma": indicators["short_ma"],
                        "long_ma": indicators["long_ma"],
                        "rsi": indicators["rsi"]
                    })
                    
                    # 매도 주문 실행
                    order_result = self._execute_sell(symbol, name, indicators)
                    if order_result:
                        results["orders_placed"].append(order_result)
                
                results["stocks_analyzed"] += 1
                
            except Exception as e:
                logger.error(f"   ❌ 분석 오류: {e}")
                results["errors"].append({"symbol": symbol, "error": str(e)})
        
        # 결과 요약 출력
        self._print_summary(results)
        
        return results
    
    def _calculate_indicators(self, df) -> Optional[Dict[str, Any]]:
        """
        기술적 지표 계산 (SMA, RSI, 거래량)
        Calculate technical indicators (SMA, RSI, Volume)
        
        Args:
            df: DataFrame (close, volume 컬럼 필수)
        
        Returns:
            dict: 계산된 지표 값들
        """
        try:
            import pandas as pd
            
            # 종가 데이터
            close = df['close'].astype(float)
            volume = df['volume'].astype(float) if 'volume' in df.columns else pd.Series([0] * len(df))
            
            # 단기/장기 이동평균선 계산
            short_ma = close.rolling(window=self.short_ma).mean()
            long_ma = close.rolling(window=self.long_ma).mean()
            
            # RSI 계산 (pandas로 직접 계산)
            rsi = self._calculate_rsi(close, self.rsi_period)
            
            # 거래량 이동평균 계산
            volume_ma = volume.rolling(window=ma_config.volume_ma_period).mean()
            
            # 최신 값 추출
            latest_close = int(close.iloc[-1])
            latest_short_ma = round(short_ma.iloc[-1], 2)
            latest_long_ma = round(long_ma.iloc[-1], 2)
            latest_rsi = round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 50.0
            latest_volume = int(volume.iloc[-1])
            latest_volume_ma = round(volume_ma.iloc[-1], 2) if not pd.isna(volume_ma.iloc[-1]) else 0
            
            # 이전 값 (크로스오버 감지용)
            prev_short_ma = round(short_ma.iloc[-2], 2) if len(short_ma) > 1 else latest_short_ma
            prev_long_ma = round(long_ma.iloc[-2], 2) if len(long_ma) > 1 else latest_long_ma
            
            # MA 갭 계산
            ma_diff = latest_short_ma - latest_long_ma
            ma_diff_pct = ((latest_short_ma - latest_long_ma) / latest_long_ma) * 100 if latest_long_ma else 0
            
            # 거래량 비율 계산
            volume_ratio = latest_volume / latest_volume_ma if latest_volume_ma > 0 else 0
            
            return {
                "close": latest_close,
                "short_ma": latest_short_ma,
                "long_ma": latest_long_ma,
                "prev_short_ma": prev_short_ma,
                "prev_long_ma": prev_long_ma,
                "rsi": latest_rsi,
                "ma_diff": ma_diff,
                "ma_diff_pct": ma_diff_pct,
                "volume": latest_volume,
                "volume_ma": latest_volume_ma,
                "volume_ratio": round(volume_ratio, 2)
            }
            
        except Exception as e:
            logger.error(f"지표 계산 오류: {e}")
            return None
    
    def _calculate_rsi(self, prices, period: int = 14):
        """
        RSI (Relative Strength Index) 계산
        Calculate RSI using pandas
        
        Args:
            prices: 종가 Series
            period: RSI 기간 (기본 14일)
        
        Returns:
            pd.Series: RSI 값
        """
        import pandas as pd
        
        # 가격 변화
        delta = prices.diff()
        
        # 상승/하락 분리
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        # 평균 상승/하락 (EMA 방식)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        
        # RS 및 RSI 계산
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _check_signal(self, symbol: str, indicators: Dict[str, Any]) -> Optional[str]:
        """
        매매 신호 확인 (노이즈 필터 적용)
        Check trading signal with noise filters
        
        Args:
            symbol: 종목 코드
            indicators: 기술적 지표 딕셔너리
        
        Returns:
            str: "BUY", "SELL", 또는 None
        """
        short_ma = indicators["short_ma"]
        long_ma = indicators["long_ma"]
        prev_short_ma = indicators["prev_short_ma"]
        prev_long_ma = indicators["prev_long_ma"]
        rsi = indicators["rsi"]
        ma_diff_pct = abs(indicators["ma_diff_pct"])
        volume_ratio = indicators.get("volume_ratio", 1.0)
        
        # 현재 상태: 단기 > 장기 (골든), 단기 < 장기 (데드)
        current_state = "golden" if short_ma > long_ma else "death"
        prev_state = self._prev_signals.get(symbol)
        
        # 상태 업데이트
        self._prev_signals[symbol] = current_state
        
        # ========================================
        # 노이즈 필터 체크 (Noise Filter Check)
        # ========================================
        
        # 1. MA 갭 필터: 너무 작은 크로스오버 무시
        if ma_config.use_ma_gap_filter and ma_diff_pct < ma_config.min_ma_gap_pct:
            if prev_state != current_state and prev_state is not None:
                logger.info(f"   ⚠️ MA 갭 부족 ({ma_diff_pct:.2f}% < {ma_config.min_ma_gap_pct}%) - 신호 무시")
            return None
        
        # 2. 거래량 필터: 거래량이 평균 대비 충분한지 확인
        if ma_config.use_volume_filter and volume_ratio < ma_config.volume_multiplier:
            if prev_state != current_state and prev_state is not None:
                logger.info(f"   ⚠️ 거래량 부족 ({volume_ratio:.1f}x < {ma_config.volume_multiplier}x) - 신호 무시")
            return None
        
        # 3. 신호 쿨다운 체크
        now = datetime.now()
        last_signal_time = self._last_signal_time.get(symbol)
        if last_signal_time:
            minutes_since = (now - last_signal_time).total_seconds() / 60
            if minutes_since < ma_config.signal_cooldown:
                return None  # 조용히 무시
        
        # ========================================
        # 크로스오버 신호 확인 (Crossover Signal Check)
        # ========================================
        
        # 골든크로스: 이전에 데드 → 현재 골든 (단기가 장기를 상향 돌파)
        if prev_state == "death" and current_state == "golden":
            # RSI 필터: 매수 시 과매수 방지
            if ma_config.use_rsi_filter and rsi > ma_config.rsi_buy_max:
                logger.info(f"   ⚠️ 골든크로스이나 RSI 과매수 ({rsi:.1f} > {ma_config.rsi_buy_max})")
                return None
            
            logger.info(f"   🔔 골든크로스 감지!")
            logger.info(f"      RSI: {rsi:.1f} | 거래량: {volume_ratio:.1f}x | MA갭: {ma_diff_pct:.2f}%")
            self.signals_generated += 1
            self._last_signal_time[symbol] = now
            return "BUY"
        
        # 데드크로스: 이전에 골든 → 현재 데드 (단기가 장기를 하향 돌파)
        elif prev_state == "golden" and current_state == "death":
            # RSI 필터: 매도 시 과매도 방지
            if ma_config.use_rsi_filter and rsi < ma_config.rsi_sell_min:
                logger.info(f"   ⚠️ 데드크로스이나 RSI 과매도 ({rsi:.1f} < {ma_config.rsi_sell_min})")
                return None
            
            logger.info(f"   🔔 데드크로스 감지!")
            logger.info(f"      RSI: {rsi:.1f} | 거래량: {volume_ratio:.1f}x | MA갭: {ma_diff_pct:.2f}%")
            self.signals_generated += 1
            self._last_signal_time[symbol] = now
            return "SELL"
        
        # 초기 상태 설정 (첫 실행 시)
        elif prev_state is None:
            logger.info(f"   ℹ️ 초기 상태 설정: {current_state}")
        
        return None
    
    def _execute_buy(self, symbol: str, name: str, indicators: Dict) -> Optional[Dict]:
        """
        매수 주문 실행 + 포지션 추적
        Execute buy order and track position
        """
        # 현재 보유 수량 확인
        current_position = self.client.get_position(symbol)
        
        if current_position > 0:
            logger.info(f"   ℹ️ 이미 보유 중 ({current_position}주) - 매수 스킵")
            return None
        
        entry_price = indicators["close"]
        logger.info(f"   💰 매수 주문 실행: {name} {self.order_quantity}주 @ {entry_price:,}원")
        
        # 시장가 매수
        order = self.client.buy_market_order(symbol, self.order_quantity)
        
        if order:
            self.orders_placed += 1
            
            # 포지션 추적 시작 (손절/익절 계산용)
            self._positions[symbol] = {
                "entry_price": entry_price,
                "quantity": self.order_quantity,
                "entry_time": datetime.now(),
                "name": name,
                "stop_loss_price": int(entry_price * (1 + ma_config.stop_loss_pct / 100)),
                "take_profit_price": int(entry_price * (1 + ma_config.take_profit_pct / 100))
            }
            
            logger.info(f"      📍 진입가: {entry_price:,}원")
            logger.info(f"      🛑 손절가: {self._positions[symbol]['stop_loss_price']:,}원 ({ma_config.stop_loss_pct}%)")
            logger.info(f"      🎯 익절가: {self._positions[symbol]['take_profit_price']:,}원 (+{ma_config.take_profit_pct}%)")
            
            return {
                "type": "BUY",
                "symbol": symbol,
                "name": name,
                "quantity": self.order_quantity,
                "price": entry_price,
                "stop_loss": self._positions[symbol]['stop_loss_price'],
                "take_profit": self._positions[symbol]['take_profit_price'],
                "order": str(order)
            }
        
        return None
    
    def _execute_sell(self, symbol: str, name: str, indicators: Dict, reason: str = "SIGNAL") -> Optional[Dict]:
        """
        매도 주문 실행 + 포지션 정리
        Execute sell order and clear position
        
        Args:
            reason: 매도 사유 ("SIGNAL", "STOP_LOSS", "TAKE_PROFIT")
        """
        # 현재 보유 수량 확인
        current_position = self.client.get_position(symbol)
        
        if current_position <= 0:
            logger.info(f"   ℹ️ 보유 수량 없음 - 매도 스킵")
            return None
        
        exit_price = indicators["close"]
        entry_info = self._positions.get(symbol, {})
        entry_price = entry_info.get("entry_price", exit_price)
        
        # 수익률 계산
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price else 0
        pnl_emoji = "📈" if pnl_pct > 0 else "📉" if pnl_pct < 0 else "➖"
        
        reason_text = {"SIGNAL": "데드크로스", "STOP_LOSS": "🛑 손절", "TAKE_PROFIT": "🎯 익절"}.get(reason, reason)
        
        logger.info(f"   💸 매도 주문 실행 ({reason_text}): {name} {current_position}주")
        logger.info(f"      진입가: {entry_price:,}원 → 청산가: {exit_price:,}원")
        logger.info(f"      {pnl_emoji} 수익률: {pnl_pct:+.2f}%")
        
        # 시장가 매도 (보유 전량)
        order = self.client.sell_market_order(symbol, current_position)
        
        if order:
            self.orders_placed += 1
            
            # 포지션 정리
            if symbol in self._positions:
                del self._positions[symbol]
            
            return {
                "type": "SELL",
                "reason": reason,
                "symbol": symbol,
                "name": name,
                "quantity": current_position,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl_pct": round(pnl_pct, 2),
                "order": str(order)
            }
        
        return None
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: int) -> Optional[str]:
        """
        손절/익절 조건 확인
        Check stop-loss and take-profit conditions
        
        Args:
            symbol: 종목 코드
            current_price: 현재가
        
        Returns:
            str: "STOP_LOSS", "TAKE_PROFIT", 또는 None
        """
        if symbol not in self._positions:
            return None
        
        pos = self._positions[symbol]
        entry_price = pos["entry_price"]
        
        # 손절 체크 (현재가 <= 손절가)
        if current_price <= pos["stop_loss_price"]:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            logger.warning(f"🛑 [{symbol}] 손절 조건 충족! 현재가: {current_price:,}원 ({pnl_pct:+.2f}%)")
            self.stop_loss_triggered += 1
            return "STOP_LOSS"
        
        # 익절 체크 (현재가 >= 익절가)
        if current_price >= pos["take_profit_price"]:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            logger.info(f"🎯 [{symbol}] 익절 조건 충족! 현재가: {current_price:,}원 ({pnl_pct:+.2f}%)")
            self.take_profit_triggered += 1
            return "TAKE_PROFIT"
        
        return None
    
    def _print_stock_status(self, symbol: str, name: str, indicators: Dict):
        """종목 현재 상태 출력"""
        ma_status = "📈 상승추세" if indicators["short_ma"] > indicators["long_ma"] else "📉 하락추세"
        rsi_status = "🔴 과매수" if indicators["rsi"] > self.rsi_overbought else \
                     "🔵 과매도" if indicators["rsi"] < self.rsi_oversold else "⚪ 중립"
        
        logger.info(f"   현재가: {indicators['close']:,}원")
        logger.info(f"   MA{self.short_ma}: {indicators['short_ma']:,.0f}원 | MA{self.long_ma}: {indicators['long_ma']:,.0f}원")
        logger.info(f"   MA 차이: {indicators['ma_diff_pct']:+.2f}% | {ma_status}")
        logger.info(f"   RSI({self.rsi_period}): {indicators['rsi']:.1f} | {rsi_status}")
    
    def _print_summary(self, results: Dict):
        """분석 결과 요약 출력"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 일일 분석 결과 요약")
        logger.info("=" * 60)
        logger.info(f"   분석 종목: {results['stocks_analyzed']}개")
        logger.info(f"   매수 신호: {len(results['buy_signals'])}개")
        logger.info(f"   매도 신호: {len(results['sell_signals'])}개")
        logger.info(f"   🛑 손절: {len(results.get('stop_losses', []))}개")
        logger.info(f"   🎯 익절: {len(results.get('take_profits', []))}개")
        logger.info(f"   실행 주문: {len(results['orders_placed'])}개")
        logger.info(f"   오류: {len(results['errors'])}개")
        
        # 현재 보유 포지션 출력
        if self._positions:
            logger.info(f"\n   📦 현재 보유 포지션: {len(self._positions)}개")
            for sym, pos in self._positions.items():
                logger.info(f"      - {pos['name']}({sym}): {pos['quantity']}주 @ {pos['entry_price']:,}원")
                logger.info(f"        SL: {pos['stop_loss_price']:,}원 | TP: {pos['take_profit_price']:,}원")
        
        if results["buy_signals"]:
            logger.info("\n   💰 매수 신호 종목:")
            for sig in results["buy_signals"]:
                logger.info(f"      - {sig['name']}({sig['symbol']}): {sig['price']:,}원, RSI={sig['rsi']:.1f}")
        
        if results["sell_signals"]:
            logger.info("\n   💸 매도 신호 종목:")
            for sig in results["sell_signals"]:
                logger.info(f"      - {sig['name']}({sig['symbol']}): {sig['price']:,}원, RSI={sig['rsi']:.1f}")
        
        if results.get("stop_losses"):
            logger.info("\n   🛑 손절 실행:")
            for order in results["stop_losses"]:
                logger.info(f"      - {order['name']}: {order['pnl_pct']:+.2f}%")
        
        if results.get("take_profits"):
            logger.info("\n   🎯 익절 실행:")
            for order in results["take_profits"]:
                logger.info(f"      - {order['name']}: {order['pnl_pct']:+.2f}%")
        
        if results["orders_placed"]:
            logger.info("\n   ✅ 실행된 주문:")
            for order in results["orders_placed"]:
                order_price = order.get('price', order.get('exit_price', 0))
                pnl_str = f" ({order['pnl_pct']:+.2f}%)" if 'pnl_pct' in order else ""
                logger.info(f"      - [{order['type']}] {order['name']}: {order['quantity']}주 @ {order_price:,}원{pnl_str}")
        
        logger.info("=" * 60)
    
    def on_stop(self):
        """전략 종료"""
        logger.info(f"📊 MA 크로스오버 전략 종료")
        logger.info(f"   생성된 신호: {self.signals_generated}개")
        logger.info(f"   실행된 주문: {self.orders_placed}개")
        logger.info(f"   🛑 손절 발동: {self.stop_loss_triggered}개")
        logger.info(f"   🎯 익절 발동: {self.take_profit_triggered}개")
        
        # 최종 보유 포지션 출력
        if self._positions:
            logger.info(f"   📦 미청산 포지션: {len(self._positions)}개")


if __name__ == "__main__":
    # 테스트 실행
    # Test run
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    print("=" * 50)
    print("Strategy 모듈 테스트 (Strategy Module Test)")
    print("=" * 50)
    
    # TickData 테스트
    test_tick = TickData(
        symbol="005930",
        price=72000,
        change=-1500,
        change_rate=-2.04,
        volume=1000000,
        prev_close=73500,
        timestamp=datetime.now()
    )
    
    print(f"\n테스트 TickData:")
    print(f"  종목: {test_tick.symbol}")
    print(f"  현재가: {test_tick.price:,}원")
    print(f"  전일대비: {test_tick.change:+,}원 ({test_tick.change_rate:+.2f}%)")
    print(f"  전일종가: {test_tick.prev_close:,}원")
    
    print("\n✅ Strategy 모듈 로드 성공!")
    print("   실제 실행은 main.py에서 KISClient와 함께 사용하세요.")
