"""
strategy_dmv.py - 듀얼 모멘텀 + 변동성 돌파 전략
Dual Momentum + Volatility Breakout Strategy

한국 시장 전체에 적용 가능한 범용 단기 모멘텀 전략
Universal short-term momentum strategy for Korean market
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time
import pandas as pd
import numpy as np

from kis_client import KISClient
from config import dmv_config
from strategy import BaseStrategy

logger = logging.getLogger(__name__)


class DualMomentumVolatilityStrategy(BaseStrategy):
    """
    듀얼 모멘텀 + 변동성 돌파 전략
    Dual Momentum + Volatility Breakout Strategy
    
    전략 구성:
    1. 종목 선별: 상대/절대 모멘텀 + 유동성/변동성 필터
    2. 진입: 변동성 돌파 + 거래량 확인
    3. 청산: 익절/손절/시간 청산
    """
    
    def __init__(self, client: KISClient, universe: List[str] = None):
        """
        Args:
            client: KIS API 클라이언트
            universe: 종목 유니버스 (None이면 자동 생성)
        """
        super().__init__(client, name="DualMomentumVolatilityStrategy")
        
        # 설정 로드
        self.momentum_period = dmv_config.momentum_period
        self.ma_period = dmv_config.ma_period
        self.breakout_k = dmv_config.volatility_breakout_k
        self.volume_multiplier = dmv_config.volume_multiplier
        self.rsi_period = dmv_config.rsi_period
        self.rsi_max = dmv_config.rsi_max
        
        self.take_profit_1 = dmv_config.take_profit_1
        self.take_profit_2 = dmv_config.take_profit_2
        self.stop_loss = dmv_config.stop_loss
        
        self.max_positions = dmv_config.max_positions
        self.order_quantity = dmv_config.order_quantity
        
        # 종목 유니버스 (None이면 장 시작 시 자동 생성)
        self.universe = universe or []
        
        # 선별된 종목 리스트 (매일 갱신)
        self.selected_stocks: Dict[str, str] = {}  # {code: name}
        
        # 포지션 추적: {symbol: {entry_price, quantity, entry_time, half_sold}}
        self._positions: Dict[str, Dict] = {}
        
        # 일일 손익 추적
        self.daily_pnl = 0.0
        self.daily_trades = 0
        
        # 통계
        self.total_entries = 0
        self.total_exits = 0
        self.tp1_exits = 0  # 1차 익절
        self.tp2_exits = 0  # 2차 익절
        self.sl_exits = 0   # 손절
        self.time_exits = 0 # 시간 청산
    
    def on_start(self):
        """전략 시작"""
        logger.info("=" * 60)
        logger.info("🚀 듀얼 모멘텀 + 변동성 돌파 전략 시작")
        logger.info("=" * 60)
        logger.info(f"   모멘텀 기간: {self.momentum_period}일")
        logger.info(f"   변동성 돌파 계수: {self.breakout_k}")
        logger.info(f"   익절: {self.take_profit_1}% / {self.take_profit_2}%")
        logger.info(f"   손절: {self.stop_loss}%")
        logger.info(f"   최대 포지션: {self.max_positions}개")
        logger.info("=" * 60)
    
    def on_stop(self):
        """전략 종료"""
        logger.info("=" * 60)
        logger.info("📊 듀얼 모멘텀 전략 종료 요약")
        logger.info(f"   총 진입: {self.total_entries}회")
        logger.info(f"   총 청산: {self.total_exits}회")
        logger.info(f"   1차 익절: {self.tp1_exits}회")
        logger.info(f"   2차 익절: {self.tp2_exits}회")
        logger.info(f"   손절: {self.sl_exits}회")
        logger.info(f"   시간 청산: {self.time_exits}회")
        logger.info(f"   일일 손익: {self.daily_pnl:+.2f}%")
        if self._positions:
            logger.info(f"   미청산 포지션: {len(self._positions)}개")
        logger.info("=" * 60)
    
    def on_tick(self, tick):
        """실시간 틱 처리 (사용 안 함)"""
        pass
    
    def select_stocks(self) -> Dict[str, str]:
        """
        종목 선별: 상대/절대 모멘텀 + 필터링
        Stock selection: Relative/Absolute momentum + Filters
        
        Returns:
            Dict[code, name]: 선별된 종목 딕셔너리
        """
        logger.info("\n📊 종목 선별 시작...")
        
        # 간단한 구현: 기존 universe 사용 (실제로는 시총/거래대금 상위 종목 조회 필요)
        if not self.universe:
            logger.warning("   ⚠️ 유니버스가 비어있습니다. 기본 종목 사용")
            # 기본 대형주 사용
            from config import ma_config
            self.universe = list(ma_config.TECH_GIANTS.keys())
        
        selected = {}
        
        for symbol in self.universe:
            try:
                # 일봉 데이터 조회
                df = self.client.get_daily_prices_df(symbol, count=self.momentum_period + 20)
                
                if df is None or len(df) < self.momentum_period:
                    continue
                
                # 상대 모멘텀: N일 수익률
                momentum_return = ((df['close'].iloc[-1] / df['close'].iloc[-self.momentum_period]) - 1) * 100
                
                # 절대 모멘텀: MA 위
                ma = df['close'].rolling(self.ma_period).mean().iloc[-1]
                current_price = df['close'].iloc[-1]
                
                if current_price > ma and momentum_return > 0:
                    # 종목명 조회
                    name = ma_config.get_stock_name(symbol)
                    selected[symbol] = name
                    logger.info(f"   ✅ {name}({symbol}): 모멘텀 {momentum_return:.2f}%")
                
            except Exception as e:
                logger.debug(f"   종목 선별 오류 ({symbol}): {e}")
                continue
        
        logger.info(f"\n   📋 선별 완료: {len(selected)}개 종목")
        return selected
    
    def run_analysis(self) -> Dict[str, Any]:
        """
        메인 분석 루프
        Main analysis loop
        
        Returns:
            Dict: 분석 결과
        """
        now = datetime.now()
        current_time = now.time()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"🔄 듀얼 모멘텀 분석 시작")
        logger.info(f"   시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        results = {
            "timestamp": now.isoformat(),
            "selected_stocks": 0,
            "entry_signals": [],
            "exit_signals": [],
            "orders_placed": [],
            "errors": []
        }
        
        # 1. 일일 손실 제한 체크
        if self.daily_pnl <= dmv_config.daily_loss_limit:
            logger.warning(f"⚠️ 일일 손실 제한 도달 ({self.daily_pnl:.2f}%) - 거래 중단")
            return results
        
        # 2. 보유 포지션 청산 조건 체크 (우선)
        for symbol in list(self._positions.keys()):
            exit_signal = self._check_exit_conditions(symbol, current_time)
            if exit_signal:
                results["exit_signals"].append(exit_signal)
                order = self._execute_sell(symbol, exit_signal)
                if order:
                    results["orders_placed"].append(order)
        
        # 3. 시간 청산 체크
        time_exit = datetime.strptime(dmv_config.time_exit, "%H:%M").time()
        if current_time >= time_exit:
            logger.info(f"⏰ 시간 청산 시간 도달 ({dmv_config.time_exit})")
            for symbol in list(self._positions.keys()):
                order = self._execute_sell(symbol, {"reason": "시간 청산", "type": "TIME_EXIT"})
                if order:
                    results["orders_placed"].append(order)
                    self.time_exits += 1
            return results
        
        # 4. 진입 시간 체크
        entry_start = datetime.strptime(dmv_config.entry_start_time, "%H:%M").time()
        entry_end = datetime.strptime(dmv_config.entry_end_time, "%H:%M").time()
        
        if not (entry_start <= current_time <= entry_end):
            logger.info(f"   ⏸️ 진입 시간 외 ({current_time.strftime('%H:%M')})")
            return results
        
        # 5. 최대 포지션 체크
        if len(self._positions) >= self.max_positions:
            logger.info(f"   📦 최대 포지션 도달 ({self.max_positions}개)")
            return results
        
        # 6. 종목 선별 (매일 1회 - 09:00~09:10 사이)
        if not self.selected_stocks and time(9, 0) <= current_time <= time(9, 10):
            self.selected_stocks = self.select_stocks()
            results["selected_stocks"] = len(self.selected_stocks)
        
        # 7. 진입 신호 체크
        for symbol, name in self.selected_stocks.items():
            if symbol in self._positions:
                continue  # 이미 보유 중
            
            entry_signal = self._check_entry_conditions(symbol, name)
            if entry_signal:
                results["entry_signals"].append(entry_signal)
                order = self._execute_buy(symbol, name, entry_signal)
                if order:
                    results["orders_placed"].append(order)
        
        # 결과 요약
        logger.info("\n" + "=" * 60)
        logger.info("📊 분석 결과")
        logger.info("=" * 60)
        logger.info(f"   선별 종목: {len(self.selected_stocks)}개")
        logger.info(f"   진입 신호: {len(results['entry_signals'])}개")
        logger.info(f"   청산 신호: {len(results['exit_signals'])}개")
        logger.info(f"   실행 주문: {len(results['orders_placed'])}개")
        logger.info(f"   현재 포지션: {len(self._positions)}개")
        logger.info(f"   일일 손익: {self.daily_pnl:+.2f}%")
        logger.info("=" * 60)
        
        return results
    
    def _check_entry_conditions(self, symbol: str, name: str) -> Optional[Dict]:
        """
        진입 조건 체크: 변동성 돌파
        Check entry conditions: Volatility breakout
        """
        try:
            # 일봉 데이터 (전일 정보)
            df_daily = self.client.get_daily_prices_df(symbol, count=30)
            if df_daily is None or len(df_daily) < 2:
                return None
            
            prev_close = df_daily['close'].iloc[-2]
            prev_high = df_daily['high'].iloc[-2]
            prev_low = df_daily['low'].iloc[-2]
            
            # 변동성 돌파가 계산
            breakout_price = prev_close + (prev_high - prev_low) * self.breakout_k
            
            # 분봉 데이터 (현재가)
            df_minute = self.client.get_minute_chart_df(symbol, period=1)
            if df_minute is None or len(df_minute) < 20:
                return None
            
            current_price = df_minute['close'].iloc[-1]
            current_volume = df_minute['volume'].iloc[-1]
            avg_volume = df_minute['volume'].rolling(20).mean().iloc[-1]
            
            # RSI 계산
            rsi = self._calculate_rsi(df_minute['close'], self.rsi_period)
            
            # 진입 조건 체크
            if current_price < breakout_price:
                return None
            
            if current_volume < avg_volume * self.volume_multiplier:
                logger.debug(f"   {name}: 거래량 부족 ({current_volume/avg_volume:.1f}x)")
                return None
            
            if rsi > self.rsi_max:
                logger.debug(f"   {name}: RSI 과매수 ({rsi:.1f})")
                return None
            
            # 상한가 임박 체크
            if dmv_config.avoid_limit_up:
                change_pct = ((current_price / prev_close) - 1) * 100
                if change_pct >= dmv_config.limit_up_threshold:
                    logger.debug(f"   {name}: 상한가 임박 ({change_pct:.1f}%)")
                    return None
            
            logger.info(f"   🔔 진입 신호: {name}({symbol})")
            logger.info(f"      현재가: {current_price:,}원")
            logger.info(f"      돌파가: {breakout_price:,}원")
            logger.info(f"      거래량: {current_volume/avg_volume:.1f}x")
            logger.info(f"      RSI: {rsi:.1f}")
            
            return {
                "symbol": symbol,
                "name": name,
                "price": current_price,
                "breakout_price": breakout_price,
                "volume_ratio": current_volume / avg_volume,
                "rsi": rsi
            }
            
        except Exception as e:
            logger.error(f"   진입 조건 체크 오류 ({symbol}): {e}")
            return None
    
    def _check_exit_conditions(self, symbol: str, current_time: time) -> Optional[Dict]:
        """
        청산 조건 체크: 익절/손절
        Check exit conditions: Take profit / Stop loss
        """
        pos = self._positions.get(symbol)
        if not pos:
            return None
        
        try:
            # 현재가 조회
            df = self.client.get_minute_chart_df(symbol, period=1)
            if df is None or df.empty:
                return None
            
            current_price = df['close'].iloc[-1]
            entry_price = pos['entry_price']
            pnl_pct = ((current_price / entry_price) - 1) * 100
            
            # 손절 체크
            if pnl_pct <= self.stop_loss:
                logger.info(f"   🛑 손절: {pos['name']}({symbol}) {pnl_pct:.2f}%")
                self.sl_exits += 1
                return {
                    "symbol": symbol,
                    "reason": "손절",
                    "type": "STOP_LOSS",
                    "pnl_pct": pnl_pct,
                    "quantity": pos['quantity']
                }
            
            # 2차 익절 체크 (전량)
            if pnl_pct >= self.take_profit_2:
                logger.info(f"   🎯 2차 익절: {pos['name']}({symbol}) {pnl_pct:.2f}%")
                self.tp2_exits += 1
                return {
                    "symbol": symbol,
                    "reason": "2차 익절",
                    "type": "TAKE_PROFIT_2",
                    "pnl_pct": pnl_pct,
                    "quantity": pos['quantity']
                }
            
            # 1차 익절 체크 (50% 물량)
            if pnl_pct >= self.take_profit_1 and not pos.get('half_sold', False):
                logger.info(f"   🎯 1차 익절: {pos['name']}({symbol}) {pnl_pct:.2f}%")
                self.tp1_exits += 1
                return {
                    "symbol": symbol,
                    "reason": "1차 익절",
                    "type": "TAKE_PROFIT_1",
                    "pnl_pct": pnl_pct,
                    "quantity": pos['quantity'] // 2  # 50% 물량
                }
            
            return None
            
        except Exception as e:
            logger.error(f"   청산 조건 체크 오류 ({symbol}): {e}")
            return None
    
    def _execute_buy(self, symbol: str, name: str, signal: Dict) -> Optional[Dict]:
        """매수 주문 실행"""
        # 이미 보유 중인지 확인
        if symbol in self._positions:
            return None
        
        # 현재 보유 수량 확인
        current_position = self.client.get_position(symbol)
        if current_position > 0:
            logger.info(f"   ℹ️ 이미 보유 중 ({current_position}주)")
            return None
        
        entry_price = signal['price']
        
        # 시장가 매수 주문
        order = self.client.buy_market_order(symbol, self.order_quantity)
        
        if order:
            logger.info(f"   💰 매수 주문 실행: {name} {self.order_quantity}주 @ {entry_price:,}원")
            
            self.total_entries += 1
            self.daily_trades += 1
            
            # 포지션 추적
            self._positions[symbol] = {
                "name": name,
                "entry_price": entry_price,
                "quantity": self.order_quantity,
                "entry_time": datetime.now(),
                "half_sold": False
            }
            
            return {
                "type": "BUY",
                "symbol": symbol,
                "name": name,
                "quantity": self.order_quantity,
                "price": entry_price,
                "order": str(order)
            }
        
        return None
    
    def _execute_sell(self, symbol: str, signal: Dict) -> Optional[Dict]:
        """매도 주문 실행"""
        pos = self._positions.get(symbol)
        if not pos:
            return None
        
        # 현재 보유 수량 확인
        current_position = self.client.get_position(symbol)
        if current_position == 0:
            logger.info(f"   ℹ️ 보유 수량 없음")
            # 포지션 정리
            del self._positions[symbol]
            return None
        
        # 매도 수량 결정
        sell_quantity = signal.get('quantity', pos['quantity'])
        sell_quantity = min(sell_quantity, current_position)
        
        # 시장가 매도 주문
        order = self.client.sell_market_order(symbol, sell_quantity)
        
        if order:
            pnl_pct = signal.get('pnl_pct', 0.0)
            logger.info(f"   💸 매도 주문 실행: {pos['name']} {sell_quantity}주")
            logger.info(f"      수익률: {pnl_pct:+.2f}%")
            
            self.total_exits += 1
            self.daily_pnl += pnl_pct
            
            # 1차 익절인 경우 half_sold 플래그 설정
            if signal.get('type') == 'TAKE_PROFIT_1':
                pos['half_sold'] = True
                pos['quantity'] = pos['quantity'] - sell_quantity
            else:
                # 전량 청산 시 포지션 삭제
                del self._positions[symbol]
            
            return {
                "type": "SELL",
                "symbol": symbol,
                "name": pos['name'],
                "quantity": sell_quantity,
                "pnl_pct": pnl_pct,
                "reason": signal.get('reason', 'Unknown'),
                "order": str(order)
            }
        
        return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """RSI 계산"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1]
        except:
            return 50.0  # 기본값
