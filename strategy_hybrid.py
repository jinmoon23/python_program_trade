"""
strategy_hybrid.py - 하이브리드 실시간 + 폴링 전략
Hybrid Real-time WebSocket + REST Polling Strategy

상위 40개 종목: WebSocket 실시간 체결가 모니터링
나머지 60개 종목: 10분봉 REST API 폴링

Top 40 stocks: WebSocket real-time price monitoring
Remaining 60 stocks: 10-minute candle REST API polling
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from pykis import KisRealtimePrice, KisSubscriptionEventArgs, KisWebsocketClient

from kis_client import KISClient
from config import ma_config

logger = logging.getLogger(__name__)


@dataclass
class RealtimeStock:
    """실시간 종목 데이터"""
    symbol: str
    name: str
    price: int = 0
    prev_close: int = 0
    change: int = 0
    change_rate: float = 0.0
    volume: int = 0
    high: int = 0
    low: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    
    # MA 계산용 가격 히스토리
    price_history: List[int] = field(default_factory=list)
    ma_short: float = 0.0
    ma_long: float = 0.0


class HybridStrategy:
    """
    하이브리드 실시간 + 폴링 전략
    Hybrid Real-time + Polling Strategy
    
    - WebSocket: 상위 40개 종목 실시간 모니터링
    - REST API: 나머지 종목 10분봉 폴링
    """
    
    MAX_WEBSOCKET_STOCKS = 40  # KIS API 제한
    
    def __init__(self, client: KISClient, all_stocks: Dict[str, str]):
        """
        Args:
            client: KIS API 클라이언트
            all_stocks: 전체 종목 딕셔너리 {코드: 이름}
        """
        self.client = client
        self.all_stocks = all_stocks
        
        # 종목 분류
        stock_list = list(all_stocks.items())
        self.realtime_stocks = dict(stock_list[:self.MAX_WEBSOCKET_STOCKS])
        self.polling_stocks = dict(stock_list[self.MAX_WEBSOCKET_STOCKS:])
        
        # 실시간 데이터 저장
        self.realtime_data: Dict[str, RealtimeStock] = {}
        self._subscriptions = []
        
        # 전략 설정
        self.short_ma = ma_config.short_ma_period
        self.long_ma = ma_config.long_ma_period
        self.order_quantity = ma_config.order_quantity
        
        # 포지션 추적
        self.positions: Dict[str, dict] = {}
        self.orders_placed = 0
        
        # 상태
        self.is_running = False
        self._polling_thread: Optional[threading.Thread] = None
        
        logger.info(f"하이브리드 전략 초기화")
        logger.info(f"  실시간 종목: {len(self.realtime_stocks)}개")
        logger.info(f"  폴링 종목: {len(self.polling_stocks)}개")
    
    def start(self):
        """전략 시작"""
        logger.info("=" * 60)
        logger.info("🚀 하이브리드 전략 시작")
        logger.info("=" * 60)
        
        self.is_running = True
        
        # 1. 실시간 종목 초기화 및 WebSocket 구독
        self._init_realtime_stocks()
        self._subscribe_realtime()
        
        # 2. 폴링 스레드 시작
        self._start_polling_thread()
        
        logger.info("✅ 전략 시작 완료")
    
    def stop(self):
        """전략 중지"""
        logger.info("전략 중지 중...")
        self.is_running = False
        
        # WebSocket 구독 해제
        for ticket in self._subscriptions:
            try:
                ticket.unsubscribe()
            except:
                pass
        
        # 폴링 스레드 종료 대기
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=5)
        
        logger.info("✅ 전략 중지 완료")
    
    def _init_realtime_stocks(self):
        """실시간 종목 초기화"""
        logger.info(f"\n📊 실시간 종목 초기화 ({len(self.realtime_stocks)}개)...")
        
        for symbol, name in self.realtime_stocks.items():
            # 현재가 조회
            price_info = self.client.get_current_price(symbol)
            
            if price_info:
                self.realtime_data[symbol] = RealtimeStock(
                    symbol=symbol,
                    name=name,
                    price=price_info.get('price', 0),
                    prev_close=price_info.get('prev_close', 0),
                    high=price_info.get('high', 0),
                    low=price_info.get('low', 0),
                    volume=price_info.get('volume', 0)
                )
                logger.debug(f"  ✅ {name}: {price_info.get('price', 0):,}원")
            else:
                self.realtime_data[symbol] = RealtimeStock(symbol=symbol, name=name)
                logger.warning(f"  ⚠️ {name}: 초기화 실패")
            
            time.sleep(0.3)  # API 호출 간격
    
    def _subscribe_realtime(self):
        """WebSocket 실시간 구독"""
        logger.info(f"\n📡 WebSocket 실시간 구독 시작...")
        
        for symbol, name in self.realtime_stocks.items():
            try:
                stock = self.client.kis.stock(symbol)
                
                # 실시간 체결가 구독
                ticket = stock.on("price", self._on_price_update)
                self._subscriptions.append(ticket)
                
                logger.debug(f"  ✅ {name}({symbol}) 구독 완료")
                
            except Exception as e:
                logger.error(f"  ❌ {name}({symbol}) 구독 실패: {e}")
        
        logger.info(f"✅ {len(self._subscriptions)}개 종목 실시간 구독 완료")
    
    def _on_price_update(self, sender: KisWebsocketClient, e: KisSubscriptionEventArgs[KisRealtimePrice]):
        """실시간 체결가 수신 콜백"""
        try:
            price_data = e.response
            symbol = price_data.symbol
            
            if symbol not in self.realtime_data:
                return
            
            stock = self.realtime_data[symbol]
            old_price = stock.price
            
            # 데이터 업데이트
            stock.price = price_data.price
            stock.change = price_data.change
            stock.volume = price_data.volume
            stock.last_update = datetime.now()
            
            # 가격 히스토리 업데이트 (MA 계산용)
            stock.price_history.append(price_data.price)
            if len(stock.price_history) > self.long_ma:
                stock.price_history = stock.price_history[-self.long_ma:]
            
            # MA 계산
            if len(stock.price_history) >= self.short_ma:
                stock.ma_short = sum(stock.price_history[-self.short_ma:]) / self.short_ma
            if len(stock.price_history) >= self.long_ma:
                stock.ma_long = sum(stock.price_history[-self.long_ma:]) / self.long_ma
            
            # 신호 체크
            self._check_realtime_signal(symbol, old_price)
            
        except Exception as e:
            logger.error(f"실시간 데이터 처리 오류: {e}")
    
    def _check_realtime_signal(self, symbol: str, old_price: int):
        """실시간 매매 신호 체크"""
        stock = self.realtime_data[symbol]
        
        # MA가 계산되지 않았으면 스킵
        if stock.ma_short == 0 or stock.ma_long == 0:
            return
        
        # 골든크로스 체크 (단기 MA가 장기 MA 상향 돌파)
        if stock.ma_short > stock.ma_long:
            ma_gap = (stock.ma_short - stock.ma_long) / stock.ma_long * 100
            
            if ma_gap > ma_config.min_ma_gap_pct:
                # 매수 신호
                if symbol not in self.positions:
                    logger.info(f"\n🔔 [실시간] 매수 신호: {stock.name}")
                    logger.info(f"   현재가: {stock.price:,}원")
                    logger.info(f"   MA{self.short_ma}: {stock.ma_short:,.0f} > MA{self.long_ma}: {stock.ma_long:,.0f}")
                    self._execute_buy(symbol, stock.name, stock.price)
        
        # 데드크로스 체크 (단기 MA가 장기 MA 하향 돌파)
        elif stock.ma_short < stock.ma_long:
            if symbol in self.positions:
                logger.info(f"\n🔔 [실시간] 매도 신호: {stock.name}")
                logger.info(f"   현재가: {stock.price:,}원")
                self._execute_sell(symbol, stock.name, stock.price, "SIGNAL")
    
    def _start_polling_thread(self):
        """폴링 스레드 시작"""
        self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._polling_thread.start()
        logger.info(f"📊 폴링 스레드 시작 (10분 간격, {len(self.polling_stocks)}개 종목)")
    
    def _polling_loop(self):
        """폴링 루프 (10분봉 분석)"""
        while self.is_running:
            try:
                self._analyze_polling_stocks()
            except Exception as e:
                logger.error(f"폴링 분석 오류: {e}")
            
            # 10분 대기
            for _ in range(600):
                if not self.is_running:
                    break
                time.sleep(1)
    
    def _analyze_polling_stocks(self):
        """폴링 종목 분석 (10분봉)"""
        logger.info(f"\n📊 [폴링] {len(self.polling_stocks)}개 종목 분석 시작...")
        
        batch_size = ma_config.batch_size
        batch_delay = ma_config.batch_delay
        api_delay = ma_config.api_delay
        
        stock_list = list(self.polling_stocks.items())
        
        for i in range(0, len(stock_list), batch_size):
            if not self.is_running:
                break
            
            batch = stock_list[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stock_list) + batch_size - 1) // batch_size
            
            logger.info(f"\n📦 배치 {batch_num}/{total_batches} 처리 중...")
            
            for symbol, name in batch:
                if not self.is_running:
                    break
                
                self._analyze_single_stock(symbol, name)
                time.sleep(api_delay)
            
            time.sleep(batch_delay)
        
        logger.info(f"✅ [폴링] 분석 완료")
    
    def _analyze_single_stock(self, symbol: str, name: str):
        """단일 종목 분석 (10분봉)"""
        try:
            # 10분봉 데이터 조회
            df = self.client.get_minute_chart_df(symbol, period=ma_config.chart_period)
            
            if df is None or len(df) < self.long_ma:
                return
            
            # MA 계산
            df['ma_short'] = df['close'].rolling(self.short_ma).mean()
            df['ma_long'] = df['close'].rolling(self.long_ma).mean()
            
            current = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else current
            
            price = int(current['close'])
            ma_short = current['ma_short']
            ma_long = current['ma_long']
            
            # 크로스오버 체크
            golden_cross = prev['ma_short'] <= prev['ma_long'] and ma_short > ma_long
            death_cross = prev['ma_short'] >= prev['ma_long'] and ma_short < ma_long
            
            if golden_cross:
                logger.info(f"\n🔔 [폴링] 골든크로스: {name}")
                logger.info(f"   현재가: {price:,}원")
                logger.info(f"   MA{self.short_ma}: {ma_short:,.0f} > MA{self.long_ma}: {ma_long:,.0f}")
                self._execute_buy(symbol, name, price)
            
            elif death_cross and symbol in self.positions:
                logger.info(f"\n🔔 [폴링] 데드크로스: {name}")
                self._execute_sell(symbol, name, price, "SIGNAL")
            
        except Exception as e:
            logger.debug(f"종목 분석 실패 ({name}): {e}")
    
    def _execute_buy(self, symbol: str, name: str, price: int):
        """매수 실행"""
        if symbol in self.positions:
            logger.info(f"   ℹ️ 이미 보유 중 - 스킵")
            return
        
        logger.info(f"   💰 매수 주문: {name} {self.order_quantity}주 @ {price:,}원")
        
        order = self.client.buy_market_order(symbol, self.order_quantity)
        
        if order:
            self.positions[symbol] = {
                'name': name,
                'entry_price': price,
                'quantity': self.order_quantity,
                'entry_time': datetime.now()
            }
            self.orders_placed += 1
            logger.info(f"   ✅ 매수 완료")
        else:
            logger.error(f"   ❌ 매수 실패")
    
    def _execute_sell(self, symbol: str, name: str, price: int, reason: str):
        """매도 실행"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        quantity = position['quantity']
        pnl_pct = (price - entry_price) / entry_price * 100
        
        pnl_emoji = "📈" if pnl_pct > 0 else "📉"
        logger.info(f"   💸 매도 주문 ({reason}): {name} {quantity}주")
        logger.info(f"      {pnl_emoji} {entry_price:,}원 → {price:,}원 ({pnl_pct:+.2f}%)")
        
        order = self.client.sell_market_order(symbol, quantity)
        
        if order:
            del self.positions[symbol]
            self.orders_placed += 1
            logger.info(f"   ✅ 매도 완료")
        else:
            logger.error(f"   ❌ 매도 실패")
    
    def get_status(self) -> dict:
        """현재 상태 반환"""
        return {
            'is_running': self.is_running,
            'realtime_stocks': len(self.realtime_stocks),
            'polling_stocks': len(self.polling_stocks),
            'subscriptions': len(self._subscriptions),
            'positions': len(self.positions),
            'orders_placed': self.orders_placed
        }


def run_hybrid_strategy(stock_group: str = "kospi200"):
    """
    하이브리드 전략 실행
    Run Hybrid Strategy
    """
    from config import ma_config
    import logging
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 60)
    print("🚀 하이브리드 실시간 + 폴링 전략")
    print("   상위 40개: WebSocket 실시간")
    print("   나머지: 10분봉 폴링")
    print("=" * 60)
    
    # API 연결
    client = KISClient()
    if not client.connect():
        print("❌ API 연결 실패!")
        return
    
    # 종목 로드
    stocks = ma_config.get_stocks(stock_group)
    print(f"\n📊 총 {len(stocks)}개 종목 로드")
    
    # 전략 생성 및 시작
    strategy = HybridStrategy(client, stocks)
    strategy.start()
    
    # 메인 루프
    try:
        while True:
            time.sleep(60)
            status = strategy.get_status()
            logger.info(f"📊 상태: 포지션 {status['positions']}개, 주문 {status['orders_placed']}건")
    except KeyboardInterrupt:
        print("\n👋 종료 중...")
        strategy.stop()
    
    print("✅ 전략 종료")


if __name__ == "__main__":
    run_hybrid_strategy()
