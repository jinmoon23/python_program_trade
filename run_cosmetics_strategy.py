#!/usr/bin/env python3
"""
run_cosmetics_strategy.py - 화장품 추세추종 전략 실행 스크립트
Cosmetics Trend-Following Strategy Runner

독립적인 실행 경로로 다른 전략과 구분됩니다.
Standalone execution path, separate from other strategies.

사용법 (Usage):
    # 백테스트 실행
    python run_cosmetics_strategy.py backtest
    
    # 백테스트 (샘플 데이터로 테스트)
    python run_cosmetics_strategy.py backtest --sample
    
    # 현재 신호 생성 (실시간)
    python run_cosmetics_strategy.py signals
    
    # 실시간 거래 모드
    python run_cosmetics_strategy.py live
"""

import sys
import os
import logging
import argparse
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import numpy as np

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cosmetics_config import cosmetics_config, backtest_config, print_cosmetics_config
from strategy_cosmetics import (
    CosmeticsTrendStrategy,
    BacktestResult,
    Signal,
    print_backtest_result,
    save_backtest_result
)
from kis_client import KISClient
from config import log_config


# ========================================
# 로깅 설정
# ========================================

def setup_logging(level: str = "INFO"):
    """로깅 설정"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('cosmetics_strategy.log', encoding='utf-8')
        ]
    )
    
    return logging.getLogger(__name__)


# ========================================
# 데이터 수집
# ========================================

class CosmeticsDataFetcher:
    """화장품 종목 데이터 수집기"""
    
    def __init__(self, client: KISClient = None):
        self.client = client
        self.logger = logging.getLogger(__name__)
    
    def fetch_all_stocks(self, days: int = 500) -> Dict[str, pd.DataFrame]:
        """
        모든 화장품 종목의 일봉 데이터 수집
        
        Args:
            days: 조회할 일수 (기본 500일 = 약 2년)
        
        Returns:
            Dict[str, pd.DataFrame]: {종목코드: OHLCV DataFrame}
        """
        if not self.client:
            self.logger.error("KIS 클라이언트가 없습니다. connect_api()를 먼저 호출하세요.")
            return {}
        
        price_data = {}
        stocks = cosmetics_config.COSMETICS_STOCKS
        total = len(stocks)
        
        self.logger.info(f"\n📊 {total}개 종목 데이터 수집 시작...")
        
        batch_size = cosmetics_config.batch_size
        stock_list = list(stocks.items())
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stock_list) + batch_size - 1) // batch_size
            
            self.logger.info(f"\n📦 배치 {batch_num}/{total_batches} 처리 중...")
            
            for symbol, name in batch:
                try:
                    df = self.client.get_daily_prices_df(symbol, count=days)
                    
                    if df is not None and len(df) >= cosmetics_config.long_ma_period:
                        price_data[symbol] = df
                        self.logger.info(f"  ✅ {name}({symbol}): {len(df)}일 데이터")
                    else:
                        self.logger.warning(f"  ⚠️ {name}({symbol}): 데이터 부족 ({len(df) if df is not None else 0}일)")
                
                except Exception as e:
                    self.logger.error(f"  ❌ {name}({symbol}) 조회 실패: {e}")
                
                time.sleep(cosmetics_config.api_delay)
            
            time.sleep(cosmetics_config.batch_delay)
        
        self.logger.info(f"\n✅ 데이터 수집 완료: {len(price_data)}/{total}개 종목")
        
        return price_data
    
    def generate_sample_data(self, days: int = 750) -> Dict[str, pd.DataFrame]:
        """
        테스트용 샘플 데이터 생성
        
        Args:
            days: 생성할 일수 (기본 750일 = 약 3년)
        
        Returns:
            Dict[str, pd.DataFrame]: {종목코드: OHLCV DataFrame}
        """
        self.logger.info(f"\n🔧 샘플 데이터 생성 중 ({days}일)...")
        
        np.random.seed(42)
        price_data = {}
        
        # 날짜 범위 생성
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 거래일만 필터링 (주말 제외)
        all_dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        for symbol, name in cosmetics_config.COSMETICS_STOCKS.items():
            # 랜덤 시작 가격 (10,000 ~ 500,000원)
            initial_price = np.random.randint(10000, 500000)
            
            # 가격 생성 (랜덤 워크 + 추세)
            returns = np.random.normal(0.0002, 0.02, len(all_dates))  # 일 평균 0.02% 수익률
            
            # 일부 종목에 추세 부여
            if np.random.random() > 0.5:
                trend = np.linspace(0, 0.3, len(all_dates))  # 상승 추세
            else:
                trend = np.linspace(0, -0.2, len(all_dates))  # 하락 추세
            
            prices = initial_price * np.exp(np.cumsum(returns) + trend)
            
            # OHLCV 생성
            df_data = []
            for i, dt in enumerate(all_dates):
                close = prices[i]
                daily_range = close * np.random.uniform(0.01, 0.03)
                
                high = close + np.random.uniform(0, daily_range)
                low = close - np.random.uniform(0, daily_range)
                open_price = np.random.uniform(low, high)
                volume = np.random.randint(100000, 10000000)
                
                df_data.append({
                    'date': dt,
                    'open': int(open_price),
                    'high': int(high),
                    'low': int(low),
                    'close': int(close),
                    'volume': volume
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('date', inplace=True)
            
            price_data[symbol] = df
        
        self.logger.info(f"✅ {len(price_data)}개 종목 샘플 데이터 생성 완료")
        
        return price_data


# ========================================
# API 연결
# ========================================

def connect_api() -> Optional[KISClient]:
    """KIS API 연결"""
    logger = logging.getLogger(__name__)
    
    logger.info("🔗 KIS API 연결 중...")
    
    client = KISClient()
    
    if client.connect():
        logger.info("✅ KIS API 연결 성공!")
        return client
    else:
        logger.error("❌ KIS API 연결 실패!")
        return None


# ========================================
# 백테스트 실행
# ========================================

def run_backtest(use_sample: bool = False, save_results: bool = True):
    """
    백테스트 실행
    
    Args:
        use_sample: True면 샘플 데이터 사용, False면 실제 API 데이터 사용
        save_results: True면 결과 저장
    """
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 70)
    print("🧴 화장품 추세추종 전략 - 백테스트")
    print("   50일/200일 SMA 골든크로스/데스크로스 + 15% 트레일링 스탑")
    print("=" * 70)
    
    # 설정 출력
    print_cosmetics_config()
    
    # 데이터 수집
    fetcher = CosmeticsDataFetcher()
    
    if use_sample:
        logger.info("\n📊 샘플 데이터로 백테스트 실행")
        price_data = fetcher.generate_sample_data(days=1000)  # 약 4년
    else:
        # API 연결
        client = connect_api()
        if not client:
            logger.error("API 연결 실패. --sample 옵션으로 샘플 데이터를 사용하세요.")
            return
        
        fetcher.client = client
        
        # 실제 데이터 수집 (약 3년치)
        days_needed = cosmetics_config.lookback_years * 252 + cosmetics_config.long_ma_period
        price_data = fetcher.fetch_all_stocks(days=days_needed)
    
    if not price_data:
        logger.error("데이터가 없습니다. 백테스트를 종료합니다.")
        return
    
    # 전략 생성 및 백테스트 실행
    strategy = CosmeticsTrendStrategy()
    
    logger.info("\n🚀 백테스트 실행 중...")
    result = strategy.backtest(price_data)
    
    if result:
        # 결과 출력
        print_backtest_result(result)
        
        # 결과 저장
        if save_results:
            save_backtest_result(result, backtest_config.output_dir)
        
        # 종목별 성과 상위/하위 5개
        if result.stock_performance:
            sorted_stocks = sorted(
                result.stock_performance.items(),
                key=lambda x: x[1]['total_pnl'],
                reverse=True
            )
            
            print("\n🏆 종목별 성과 (상위 5개):")
            for symbol, perf in sorted_stocks[:5]:
                print(f"   📈 {perf['name']}({symbol}): {perf['total_pnl']:+,.0f}원 ({perf['avg_pnl_pct']:+.2f}%) | {perf['trades']}건")
            
            print("\n📉 종목별 성과 (하위 5개):")
            for symbol, perf in sorted_stocks[-5:]:
                print(f"   📉 {perf['name']}({symbol}): {perf['total_pnl']:+,.0f}원 ({perf['avg_pnl_pct']:+.2f}%) | {perf['trades']}건")
    else:
        logger.error("백테스트 실패!")


# ========================================
# 현재 신호 생성
# ========================================

def run_signals():
    """현재 매매 신호 생성"""
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 70)
    print("🧴 화장품 추세추종 전략 - 현재 신호")
    print("   50일/200일 SMA 골든크로스/데스크로스 분석")
    print("=" * 70)
    
    # API 연결
    client = connect_api()
    if not client:
        return
    
    # 전략 생성
    strategy = CosmeticsTrendStrategy(client=client)
    
    # 신호 생성
    signals = strategy.run_live_signals()
    
    # 결과 요약
    buy_signals = [s for s in signals if s.signal_type == "BUY"]
    sell_signals = [s for s in signals if s.signal_type == "SELL"]
    hold_up = [s for s in signals if s.signal_type == "HOLD" and s.short_ma > s.long_ma]
    hold_down = [s for s in signals if s.signal_type == "HOLD" and s.short_ma <= s.long_ma]
    
    print("\n" + "=" * 70)
    print("📊 신호 요약")
    print("=" * 70)
    
    print(f"\n🟢 매수 신호 (골든크로스): {len(buy_signals)}개")
    if buy_signals:
        for s in buy_signals:
            print(f"   {s.name}({s.symbol}) @ {s.price:,.0f}원")
            print(f"      MA50: {s.short_ma:,.0f} > MA200: {s.long_ma:,.0f} (갭: {(s.short_ma/s.long_ma-1)*100:+.2f}%)")
    
    print(f"\n🔴 매도 신호 (데스크로스): {len(sell_signals)}개")
    if sell_signals:
        for s in sell_signals:
            print(f"   {s.name}({s.symbol}) @ {s.price:,.0f}원")
            print(f"      MA50: {s.short_ma:,.0f} < MA200: {s.long_ma:,.0f} (갭: {(s.short_ma/s.long_ma-1)*100:+.2f}%)")
    
    print(f"\n📈 상승 추세 (홀딩): {len(hold_up)}개")
    print(f"📉 하락 추세 (관망): {len(hold_down)}개")
    
    # 신호를 JSON으로 저장
    signals_data = [{
        'symbol': s.symbol,
        'name': s.name,
        'signal': s.signal_type,
        'price': s.price,
        'reason': s.reason,
        'ma50': s.short_ma,
        'ma200': s.long_ma,
        'confidence': s.confidence
    } for s in signals]
    
    output_file = f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(signals_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 신호 저장 완료: {output_file}")


# ========================================
# 실시간 거래 모드
# ========================================

def run_live():
    """실시간 거래 모드"""
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 70)
    print("🧴 화장품 추세추종 전략 - 실시간 거래 모드")
    print("   ⚠️ 주의: 실제 주문이 실행됩니다!")
    print("=" * 70)
    
    # API 연결
    client = connect_api()
    if not client:
        return
    
    # 전략 생성
    strategy = CosmeticsTrendStrategy(client=client)
    
    # 현재 잔고 확인
    balance = client.get_balance()
    if balance:
        print(f"\n💰 현재 잔고:")
        print(f"   총 평가금액: {balance.get('total_value', 0):,.0f}원")
        print(f"   예수금: {balance.get('cash', 0):,.0f}원")
        
        if balance.get('stocks'):
            print(f"   보유 종목: {len(balance['stocks'])}개")
            for stock in balance['stocks']:
                print(f"      - {stock.get('name')}: {stock.get('quantity')}주 @ {stock.get('current_price'):,.0f}원")
    
    print("\n⏰ 일별 신호 체크 모드로 실행합니다...")
    print(f"   실행 시간: 매일 {cosmetics_config.run_time}")
    print("   종료하려면 Ctrl+C를 누르세요.")
    
    try:
        while True:
            current_time = datetime.now().strftime("%H:%M")
            
            # 설정된 시간에 신호 체크
            if current_time == cosmetics_config.run_time:
                logger.info(f"\n⏰ {current_time} - 일일 신호 체크 시작")
                
                signals = strategy.run_live_signals()
                
                # 매수/매도 신호 처리
                buy_signals = [s for s in signals if s.signal_type == "BUY"]
                sell_signals = [s for s in signals if s.signal_type == "SELL"]
                
                logger.info(f"📊 신호: 매수 {len(buy_signals)}개, 매도 {len(sell_signals)}개")
                
                # 실제 주문 실행 (주석 해제하여 활성화)
                # for signal in buy_signals:
                #     client.buy_market_order(signal.symbol, cosmetics_config.order_quantity)
                # 
                # for signal in sell_signals:
                #     client.sell_market_order(signal.symbol, cosmetics_config.order_quantity)
                
                # 다음 날까지 대기 (1분 후 다시 체크 방지)
                time.sleep(120)
            
            # 1분마다 시간 체크
            time.sleep(60)
    
    except KeyboardInterrupt:
        print("\n\n👋 실시간 거래 모드 종료")


# ========================================
# 메인 함수
# ========================================

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="화장품 추세추종 전략 (Cosmetics Trend-Following Strategy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python run_cosmetics_strategy.py backtest           # 실제 데이터로 백테스트
  python run_cosmetics_strategy.py backtest --sample  # 샘플 데이터로 백테스트
  python run_cosmetics_strategy.py signals            # 현재 신호 생성
  python run_cosmetics_strategy.py live               # 실시간 거래 모드
        """
    )
    
    parser.add_argument(
        'command',
        choices=['backtest', 'signals', 'live', 'config'],
        help='실행할 명령'
    )
    
    parser.add_argument(
        '--sample',
        action='store_true',
        help='샘플 데이터 사용 (백테스트 전용)'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='결과 저장 안함'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='로그 레벨 (기본: INFO)'
    )
    
    args = parser.parse_args()
    
    # 로깅 설정
    logger = setup_logging(args.log_level)
    
    # 명령 실행
    if args.command == 'backtest':
        run_backtest(use_sample=args.sample, save_results=not args.no_save)
    
    elif args.command == 'signals':
        run_signals()
    
    elif args.command == 'live':
        run_live()
    
    elif args.command == 'config':
        print_cosmetics_config()


if __name__ == "__main__":
    main()
