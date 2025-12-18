"""
strategy_cosmetics.py - 화장품 추세추종 전략
Cosmetics Trend-Following Strategy

47개 한국 화장품 관련 종목에 대한 골든크로스/데스크로스 매매 전략
Golden Cross / Death Cross trading strategy for 47 Korean cosmetics stocks

전략:
- 매수: 50일 SMA > 200일 SMA (골든크로스)
- 매도: 50일 SMA < 200일 SMA (데스크로스) 또는 15% 트레일링 스탑
"""

import logging
import time
import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import numpy as np

from cosmetics_config import cosmetics_config, backtest_config, CosmeticsStrategyConfig
from kis_client import KISClient

logger = logging.getLogger(__name__)


# ========================================
# 데이터 클래스 정의
# ========================================

@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    name: str
    entry_date: date
    entry_price: float
    quantity: int
    highest_price: float  # 트레일링 스탑용 최고가
    trailing_stop_price: float  # 현재 트레일링 스탑가
    
    def update_trailing_stop(self, current_price: float, trailing_pct: float) -> bool:
        """
        트레일링 스탑 업데이트
        Returns: True if trailing stop was updated
        """
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.trailing_stop_price = current_price * (1 - trailing_pct / 100)
            return True
        return False
    
    def is_stopped_out(self, current_price: float) -> bool:
        """트레일링 스탑 체크"""
        return current_price <= self.trailing_stop_price


@dataclass
class Trade:
    """거래 기록"""
    symbol: str
    name: str
    trade_type: str  # "BUY" or "SELL"
    date: date
    price: float
    quantity: int
    value: float
    commission: float
    tax: float  # 매도 시에만
    reason: str  # "GOLDEN_CROSS", "DEATH_CROSS", "TRAILING_STOP"
    pnl: float = 0.0  # 매도 시 손익
    pnl_pct: float = 0.0  # 매도 시 수익률


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # 기본 정보
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    
    # 수익률 지표
    total_return: float  # 총 수익률 (%)
    cagr: float  # 연평균 수익률 (%)
    
    # 리스크 지표
    max_drawdown: float  # 최대 낙폭 (%)
    max_drawdown_duration: int  # 최대 낙폭 지속일
    sharpe_ratio: float  # 샤프 비율
    sortino_ratio: float  # 소르티노 비율
    
    # 거래 통계
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # 승률 (%)
    avg_win: float  # 평균 수익 (%)
    avg_loss: float  # 평균 손실 (%)
    profit_factor: float  # 이익/손실 비율
    
    # 기간별 수익률
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    yearly_returns: Dict[str, float] = field(default_factory=dict)
    
    # 종목별 성과
    stock_performance: Dict[str, dict] = field(default_factory=dict)
    
    # 상세 데이터
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass
class Signal:
    """매매 신호"""
    symbol: str
    name: str
    signal_type: str  # "BUY", "SELL", "HOLD"
    date: date
    price: float
    reason: str
    short_ma: float
    long_ma: float
    confidence: float = 0.0  # 신호 강도 (0-1)


# ========================================
# 전략 클래스
# ========================================

class CosmeticsTrendStrategy:
    """
    화장품 추세추종 전략
    Cosmetics Trend-Following Strategy
    
    - 50일/200일 SMA 골든크로스/데스크로스
    - 15% 트레일링 스탑
    """
    
    def __init__(self, config: CosmeticsStrategyConfig = None, client: KISClient = None):
        """
        Args:
            config: 전략 설정
            client: KIS API 클라이언트 (실시간 거래용)
        """
        self.config = config or cosmetics_config
        self.client = client
        
        # 전략 파라미터
        self.short_ma_period = self.config.short_ma_period
        self.long_ma_period = self.config.long_ma_period
        self.trailing_stop_pct = self.config.trailing_stop_pct
        
        # 포지션 관리
        self.positions: Dict[str, Position] = {}
        
        # 거래 기록
        self.trades: List[Trade] = []
        
        # 현재 자본
        self.capital = self.config.initial_capital
        
        logger.info(f"화장품 추세추종 전략 초기화")
        logger.info(f"  MA: {self.short_ma_period}/{self.long_ma_period}일")
        logger.info(f"  트레일링 스탑: {self.trailing_stop_pct}%")
        logger.info(f"  대상 종목: {self.config.get_stock_count()}개")
    
    # ========================================
    # 기술적 지표 계산
    # ========================================
    
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """단순 이동평균 계산"""
        return prices.rolling(window=period).mean()
    
    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        매매 신호 계산
        
        Args:
            df: OHLCV DataFrame (date 인덱스, close 컬럼 필수)
        
        Returns:
            DataFrame with signal columns added
        """
        df = df.copy()
        
        # SMA 계산
        df['sma_short'] = self.calculate_sma(df['close'], self.short_ma_period)
        df['sma_long'] = self.calculate_sma(df['close'], self.long_ma_period)
        
        # 크로스오버 감지
        df['ma_diff'] = df['sma_short'] - df['sma_long']
        df['ma_diff_prev'] = df['ma_diff'].shift(1)
        
        # 골든크로스: 단기 MA가 장기 MA 상향 돌파
        df['golden_cross'] = (df['ma_diff'] > 0) & (df['ma_diff_prev'] <= 0)
        
        # 데스크로스: 단기 MA가 장기 MA 하향 돌파
        df['death_cross'] = (df['ma_diff'] < 0) & (df['ma_diff_prev'] >= 0)
        
        # 현재 추세 (단기 MA > 장기 MA면 상승 추세)
        df['trend'] = np.where(df['ma_diff'] > 0, 'UP', 'DOWN')
        
        return df
    
    # ========================================
    # 백테스트 엔진
    # ========================================
    
    def backtest(self, price_data: Dict[str, pd.DataFrame]) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            price_data: {종목코드: OHLCV DataFrame} 딕셔너리
        
        Returns:
            BacktestResult: 백테스트 결과
        """
        logger.info("\n" + "=" * 60)
        logger.info("📊 백테스트 시작")
        logger.info("=" * 60)
        
        # 초기화
        self.capital = self.config.initial_capital
        self.positions = {}
        self.trades = []
        
        # 모든 종목의 날짜 범위 통합
        all_dates = set()
        for df in price_data.values():
            all_dates.update(df.index.tolist())
        
        trading_dates = sorted(all_dates)
        
        if not trading_dates:
            logger.error("거래 데이터가 없습니다.")
            return None
        
        start_date = trading_dates[0]
        end_date = trading_dates[-1]
        
        logger.info(f"  기간: {start_date} ~ {end_date}")
        logger.info(f"  초기 자본: {self.capital:,.0f}원")
        logger.info(f"  종목 수: {len(price_data)}개")
        
        # 신호 계산
        signals_data = {}
        for symbol, df in price_data.items():
            if len(df) >= self.long_ma_period:
                signals_data[symbol] = self.calculate_signals(df)
        
        logger.info(f"  신호 계산 완료: {len(signals_data)}개 종목")
        
        # 자산 곡선 기록
        equity_curve = []
        
        # 일별 시뮬레이션
        for current_date in trading_dates:
            daily_value = self.capital
            
            # 1. 기존 포지션 평가 및 트레일링 스탑 체크
            positions_to_close = []
            
            for symbol, position in self.positions.items():
                if symbol not in signals_data:
                    continue
                
                df = signals_data[symbol]
                if current_date not in df.index:
                    continue
                
                row = df.loc[current_date]
                current_price = row['close']
                
                # 트레일링 스탑 업데이트
                if self.config.use_trailing_stop:
                    position.update_trailing_stop(current_price, self.trailing_stop_pct)
                    
                    # 트레일링 스탑 발동
                    if position.is_stopped_out(current_price):
                        positions_to_close.append((symbol, current_price, "TRAILING_STOP"))
                        continue
                
                # 데스크로스 체크
                if row.get('death_cross', False):
                    positions_to_close.append((symbol, current_price, "DEATH_CROSS"))
                    continue
                
                # 포지션 가치 계산
                daily_value += position.quantity * current_price
            
            # 2. 매도 실행 (트레일링 스탑 또는 데스크로스)
            for symbol, price, reason in positions_to_close:
                self._execute_sell(symbol, price, current_date, reason)
            
            # 3. 매수 신호 체크 (골든크로스)
            for symbol, df in signals_data.items():
                if symbol in self.positions:
                    continue
                
                if current_date not in df.index:
                    continue
                
                row = df.loc[current_date]
                
                if row.get('golden_cross', False):
                    current_price = row['close']
                    self._execute_buy(symbol, current_price, current_date)
            
            # 4. 일별 자산 기록
            total_value = self.capital
            for symbol, position in self.positions.items():
                if symbol in signals_data and current_date in signals_data[symbol].index:
                    price = signals_data[symbol].loc[current_date, 'close']
                    total_value += position.quantity * price
            
            equity_curve.append({
                'date': current_date,
                'cash': self.capital,
                'positions_value': total_value - self.capital,
                'total_value': total_value,
                'num_positions': len(self.positions)
            })
        
        # 마지막 날 모든 포지션 청산
        final_date = trading_dates[-1]
        for symbol in list(self.positions.keys()):
            if symbol in signals_data and final_date in signals_data[symbol].index:
                price = signals_data[symbol].loc[final_date, 'close']
                self._execute_sell(symbol, price, final_date, "END_OF_BACKTEST")
        
        # 결과 계산
        equity_df = pd.DataFrame(equity_curve)
        equity_df.set_index('date', inplace=True)
        
        result = self._calculate_performance(
            equity_df=equity_df,
            trades=self.trades,
            start_date=start_date,
            end_date=end_date
        )
        
        return result
    
    def _execute_buy(self, symbol: str, price: float, trade_date: date) -> bool:
        """매수 실행"""
        name = self.config.get_stock_name(symbol)
        
        # 포지션 사이즈 계산
        quantity = self.config.calculate_position_size(self.capital, price)
        
        if quantity <= 0:
            return False
        
        # 거래 비용 계산
        trade_value = price * quantity
        commission = trade_value * (self.config.commission_rate / 100)
        slippage_cost = trade_value * (self.config.slippage / 100)
        total_cost = trade_value + commission + slippage_cost
        
        if total_cost > self.capital:
            return False
        
        # 포지션 생성
        position = Position(
            symbol=symbol,
            name=name,
            entry_date=trade_date,
            entry_price=price,
            quantity=quantity,
            highest_price=price,
            trailing_stop_price=price * (1 - self.trailing_stop_pct / 100)
        )
        
        self.positions[symbol] = position
        self.capital -= total_cost
        
        # 거래 기록
        trade = Trade(
            symbol=symbol,
            name=name,
            trade_type="BUY",
            date=trade_date,
            price=price,
            quantity=quantity,
            value=trade_value,
            commission=commission,
            tax=0,
            reason="GOLDEN_CROSS"
        )
        self.trades.append(trade)
        
        if backtest_config.log_trades:
            logger.debug(f"  📈 매수: {name}({symbol}) {quantity}주 @ {price:,.0f}원")
        
        return True
    
    def _execute_sell(self, symbol: str, price: float, trade_date: date, reason: str) -> bool:
        """매도 실행"""
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        
        # 거래 비용 계산
        trade_value = price * position.quantity
        commission = trade_value * (self.config.commission_rate / 100)
        tax = trade_value * (self.config.tax_rate / 100)
        slippage_cost = trade_value * (self.config.slippage / 100)
        net_proceeds = trade_value - commission - tax - slippage_cost
        
        # 손익 계산
        entry_value = position.entry_price * position.quantity
        pnl = net_proceeds - entry_value
        pnl_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0
        
        # 자본 업데이트
        self.capital += net_proceeds
        
        # 거래 기록
        trade = Trade(
            symbol=symbol,
            name=position.name,
            trade_type="SELL",
            date=trade_date,
            price=price,
            quantity=position.quantity,
            value=trade_value,
            commission=commission,
            tax=tax,
            reason=reason,
            pnl=pnl,
            pnl_pct=pnl_pct
        )
        self.trades.append(trade)
        
        if backtest_config.log_trades:
            emoji = "📈" if pnl > 0 else "📉"
            logger.debug(f"  {emoji} 매도: {position.name}({symbol}) @ {price:,.0f}원 | {pnl_pct:+.2f}% ({reason})")
        
        # 포지션 삭제
        del self.positions[symbol]
        
        return True
    
    def _calculate_performance(
        self,
        equity_df: pd.DataFrame,
        trades: List[Trade],
        start_date: date,
        end_date: date
    ) -> BacktestResult:
        """성과 지표 계산"""
        
        initial_capital = self.config.initial_capital
        final_capital = equity_df['total_value'].iloc[-1] if len(equity_df) > 0 else initial_capital
        
        # 총 수익률
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        # CAGR 계산
        years = (end_date - start_date).days / 365.25
        if years > 0 and final_capital > 0:
            cagr = (pow(final_capital / initial_capital, 1 / years) - 1) * 100
        else:
            cagr = 0
        
        # 일별 수익률 계산
        equity_df['daily_return'] = equity_df['total_value'].pct_change()
        
        # 최대 낙폭 (MDD) 계산
        equity_df['peak'] = equity_df['total_value'].cummax()
        equity_df['drawdown'] = (equity_df['total_value'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        # MDD 지속 기간
        drawdown_periods = (equity_df['drawdown'] < 0).astype(int)
        if drawdown_periods.sum() > 0:
            drawdown_groups = drawdown_periods.diff().fillna(0).abs().cumsum()
            max_drawdown_duration = drawdown_periods.groupby(drawdown_groups).sum().max()
        else:
            max_drawdown_duration = 0
        
        # 샤프 비율
        if len(equity_df) > 1:
            daily_rf = backtest_config.risk_free_rate / 100 / 252
            excess_returns = equity_df['daily_return'].dropna() - daily_rf
            sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 소르티노 비율
        if len(equity_df) > 1:
            negative_returns = equity_df['daily_return'][equity_df['daily_return'] < 0]
            downside_std = negative_returns.std() if len(negative_returns) > 0 else 1
            sortino_ratio = np.sqrt(252) * excess_returns.mean() / downside_std if downside_std > 0 else 0
        else:
            sortino_ratio = 0
        
        # 거래 통계
        sell_trades = [t for t in trades if t.trade_type == "SELL"]
        total_trades = len(sell_trades)
        
        winning_trades = [t for t in sell_trades if t.pnl > 0]
        losing_trades = [t for t in sell_trades if t.pnl <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        avg_win = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0
        
        total_wins = sum([t.pnl for t in winning_trades]) if winning_trades else 0
        total_losses = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # 월별 수익률
        monthly_returns = {}
        if len(equity_df) > 0:
            equity_df['month'] = equity_df.index.to_series().apply(lambda x: x.strftime('%Y-%m') if hasattr(x, 'strftime') else str(x)[:7])
            for month, group in equity_df.groupby('month'):
                if len(group) > 0:
                    month_return = (group['total_value'].iloc[-1] / group['total_value'].iloc[0] - 1) * 100
                    monthly_returns[month] = month_return
        
        # 연도별 수익률
        yearly_returns = {}
        if len(equity_df) > 0:
            equity_df['year'] = equity_df.index.to_series().apply(lambda x: str(x)[:4])
            for year, group in equity_df.groupby('year'):
                if len(group) > 0:
                    year_return = (group['total_value'].iloc[-1] / group['total_value'].iloc[0] - 1) * 100
                    yearly_returns[year] = year_return
        
        # 종목별 성과
        stock_performance = {}
        for symbol in set([t.symbol for t in sell_trades]):
            symbol_trades = [t for t in sell_trades if t.symbol == symbol]
            stock_performance[symbol] = {
                'name': symbol_trades[0].name if symbol_trades else symbol,
                'trades': len(symbol_trades),
                'total_pnl': sum([t.pnl for t in symbol_trades]),
                'avg_pnl_pct': np.mean([t.pnl_pct for t in symbol_trades]),
                'win_rate': len([t for t in symbol_trades if t.pnl > 0]) / len(symbol_trades) * 100 if symbol_trades else 0
            }
        
        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            cagr=cagr,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            monthly_returns=monthly_returns,
            yearly_returns=yearly_returns,
            stock_performance=stock_performance,
            trades=trades,
            equity_curve=equity_df
        )
        
        return result
    
    # ========================================
    # 현재 신호 생성 (실시간 거래용)
    # ========================================
    
    def generate_current_signals(self, price_data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        현재 매매 신호 생성
        
        Args:
            price_data: {종목코드: OHLCV DataFrame} 딕셔너리
        
        Returns:
            List[Signal]: 현재 매매 신호 리스트
        """
        signals = []
        current_date = date.today()
        
        for symbol, df in price_data.items():
            if len(df) < self.long_ma_period:
                continue
            
            # 신호 계산
            df_signals = self.calculate_signals(df)
            
            if len(df_signals) == 0:
                continue
            
            latest = df_signals.iloc[-1]
            prev = df_signals.iloc[-2] if len(df_signals) > 1 else latest
            
            name = self.config.get_stock_name(symbol)
            price = latest['close']
            short_ma = latest['sma_short']
            long_ma = latest['sma_long']
            
            # 신호 강도 계산 (MA 갭 비율)
            ma_gap = abs(short_ma - long_ma) / long_ma * 100 if long_ma > 0 else 0
            confidence = min(ma_gap / 5, 1.0)  # 5% 갭이면 confidence = 1
            
            # 신호 판단
            if latest['golden_cross']:
                signal = Signal(
                    symbol=symbol,
                    name=name,
                    signal_type="BUY",
                    date=current_date,
                    price=price,
                    reason="골든크로스 (50일 MA > 200일 MA 상향돌파)",
                    short_ma=short_ma,
                    long_ma=long_ma,
                    confidence=confidence
                )
            elif latest['death_cross']:
                signal = Signal(
                    symbol=symbol,
                    name=name,
                    signal_type="SELL",
                    date=current_date,
                    price=price,
                    reason="데스크로스 (50일 MA < 200일 MA 하향돌파)",
                    short_ma=short_ma,
                    long_ma=long_ma,
                    confidence=confidence
                )
            else:
                trend = "상승추세" if latest['trend'] == 'UP' else "하락추세"
                signal = Signal(
                    symbol=symbol,
                    name=name,
                    signal_type="HOLD",
                    date=current_date,
                    price=price,
                    reason=f"대기 ({trend})",
                    short_ma=short_ma,
                    long_ma=long_ma,
                    confidence=confidence
                )
            
            signals.append(signal)
        
        return signals
    
    # ========================================
    # 실시간 거래 (Live Trading)
    # ========================================
    
    def run_live_signals(self) -> List[Signal]:
        """
        실시간 매매 신호 생성 및 반환
        KIS API를 통해 최신 데이터 조회 후 신호 생성
        """
        if not self.client:
            logger.error("KIS 클라이언트가 설정되지 않았습니다.")
            return []
        
        logger.info("\n📊 실시간 신호 분석 시작...")
        
        # 데이터 수집
        price_data = {}
        stocks = self.config.COSMETICS_STOCKS
        
        batch_size = self.config.batch_size
        stock_list = list(stocks.items())
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            
            for symbol, name in batch:
                try:
                    df = self.client.get_daily_prices_df(symbol, count=self.config.min_data_days)
                    if df is not None and len(df) >= self.long_ma_period:
                        price_data[symbol] = df
                        logger.debug(f"  ✅ {name}: {len(df)}일 데이터")
                    else:
                        logger.warning(f"  ⚠️ {name}: 데이터 부족")
                except Exception as e:
                    logger.error(f"  ❌ {name} 데이터 조회 실패: {e}")
                
                time.sleep(self.config.api_delay)
            
            time.sleep(self.config.batch_delay)
        
        logger.info(f"  데이터 수집 완료: {len(price_data)}개 종목")
        
        # 신호 생성
        signals = self.generate_current_signals(price_data)
        
        # 결과 출력
        buy_signals = [s for s in signals if s.signal_type == "BUY"]
        sell_signals = [s for s in signals if s.signal_type == "SELL"]
        
        logger.info(f"\n📈 매수 신호: {len(buy_signals)}개")
        for s in buy_signals:
            logger.info(f"   🟢 {s.name}({s.symbol}) @ {s.price:,.0f}원 | MA50:{s.short_ma:,.0f} > MA200:{s.long_ma:,.0f}")
        
        logger.info(f"\n📉 매도 신호: {len(sell_signals)}개")
        for s in sell_signals:
            logger.info(f"   🔴 {s.name}({s.symbol}) @ {s.price:,.0f}원 | MA50:{s.short_ma:,.0f} < MA200:{s.long_ma:,.0f}")
        
        return signals


# ========================================
# 유틸리티 함수
# ========================================

def print_backtest_result(result: BacktestResult):
    """백테스트 결과 출력"""
    print("\n" + "=" * 70)
    print("📊 백테스트 결과 요약")
    print("=" * 70)
    
    print(f"\n📅 기간: {result.start_date} ~ {result.end_date}")
    print(f"💰 초기 자본: {result.initial_capital:,.0f}원")
    print(f"💵 최종 자본: {result.final_capital:,.0f}원")
    
    print(f"\n📈 수익률 지표:")
    print(f"   총 수익률: {result.total_return:+.2f}%")
    print(f"   CAGR: {result.cagr:+.2f}%")
    
    print(f"\n⚠️ 리스크 지표:")
    print(f"   최대 낙폭 (MDD): {result.max_drawdown:.2f}%")
    print(f"   MDD 지속일: {result.max_drawdown_duration}일")
    print(f"   샤프 비율: {result.sharpe_ratio:.2f}")
    print(f"   소르티노 비율: {result.sortino_ratio:.2f}")
    
    print(f"\n📊 거래 통계:")
    print(f"   총 거래: {result.total_trades}건")
    print(f"   승리: {result.winning_trades}건 / 패배: {result.losing_trades}건")
    print(f"   승률: {result.win_rate:.1f}%")
    print(f"   평균 수익: {result.avg_win:+.2f}% / 평균 손실: {result.avg_loss:.2f}%")
    print(f"   이익/손실 비율: {result.profit_factor:.2f}")
    
    if result.yearly_returns:
        print(f"\n📆 연도별 수익률:")
        for year, ret in sorted(result.yearly_returns.items()):
            emoji = "📈" if ret > 0 else "📉"
            print(f"   {emoji} {year}: {ret:+.2f}%")
    
    print("\n" + "=" * 70)


def save_backtest_result(result: BacktestResult, output_dir: str = "backtest_results"):
    """백테스트 결과 저장"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 요약 저장
    summary = {
        'start_date': str(result.start_date),
        'end_date': str(result.end_date),
        'initial_capital': result.initial_capital,
        'final_capital': result.final_capital,
        'total_return': result.total_return,
        'cagr': result.cagr,
        'max_drawdown': result.max_drawdown,
        'sharpe_ratio': result.sharpe_ratio,
        'total_trades': result.total_trades,
        'win_rate': result.win_rate,
        'yearly_returns': result.yearly_returns,
        'stock_performance': result.stock_performance
    }
    
    with open(f"{output_dir}/summary_{timestamp}.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 거래 내역 저장
    if backtest_config.save_trades and result.trades:
        trades_data = [{
            'symbol': t.symbol,
            'name': t.name,
            'type': t.trade_type,
            'date': str(t.date),
            'price': t.price,
            'quantity': t.quantity,
            'value': t.value,
            'commission': t.commission,
            'tax': t.tax,
            'reason': t.reason,
            'pnl': t.pnl,
            'pnl_pct': t.pnl_pct
        } for t in result.trades]
        
        pd.DataFrame(trades_data).to_csv(f"{output_dir}/trades_{timestamp}.csv", index=False, encoding='utf-8-sig')
    
    # 자산 곡선 저장
    if backtest_config.save_equity_curve and len(result.equity_curve) > 0:
        result.equity_curve.to_csv(f"{output_dir}/equity_curve_{timestamp}.csv", encoding='utf-8-sig')
    
    logger.info(f"결과 저장 완료: {output_dir}/")


if __name__ == "__main__":
    # 테스트 실행
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("\n🧴 화장품 추세추종 전략 테스트")
    print("=" * 60)
    
    # 설정 출력
    from cosmetics_config import print_cosmetics_config
    print_cosmetics_config()
    
    # 전략 인스턴스 생성
    strategy = CosmeticsTrendStrategy()
    
    print("\n✅ 전략 초기화 완료")
    print("   실제 백테스트를 실행하려면 run_cosmetics_backtest.py를 사용하세요.")
