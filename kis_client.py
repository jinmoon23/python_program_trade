"""
kis_client.py - KIS Open API 클라이언트 래퍼
KIS Open API Client Wrapper

python-kis 라이브러리를 사용하여 한국투자증권 API와 통신합니다.
인증, 토큰 관리, REST API, WebSocket 기능을 제공합니다.

Uses python-kis library to communicate with Korea Investment Securities API.
Provides authentication, token management, REST API, and WebSocket features.
"""

import logging
from typing import Optional, Callable, List
from datetime import datetime
from pathlib import Path

from pykis import PyKis
from pykis.api.account.order import KisOrder

from config import kis_config, trading_config, log_config

# 로거 설정
# Logger setup
logger = logging.getLogger(__name__)


class KISClient:
    """
    한국투자증권 Open API 클라이언트 래퍼 클래스
    Korea Investment Securities Open API Client Wrapper Class
    
    주요 기능:
    - 자동 인증 및 토큰 관리
    - 국내 주식 시세 조회
    - 국내 주식 주문 (매수/매도)
    - 실시간 시세 WebSocket 구독
    
    Main features:
    - Automatic authentication and token management
    - Domestic stock price inquiry
    - Domestic stock orders (buy/sell)
    - Real-time price WebSocket subscription
    """
    
    def __init__(self):
        """
        KISClient 초기화
        Initialize KISClient
        """
        self.kis: Optional[PyKis] = None
        self._is_connected = False
        
        logger.info("KISClient 인스턴스 생성됨 (KISClient instance created)")
    
    def connect(self) -> bool:
        """
        KIS API에 연결하고 인증을 수행합니다.
        Connect to KIS API and perform authentication.
        
        Returns:
            bool: 연결 성공 여부 (Connection success status)
        """
        try:
            logger.info("KIS API 연결 시작... (Starting KIS API connection...)")
            
            # 계좌번호 파싱 (8자리-2자리 형식)
            # Parse account number (8-digit-2-digit format)
            account_parts = kis_config.account_number.split("-")
            if len(account_parts) != 2:
                raise ValueError(f"잘못된 계좌번호 형식: {kis_config.account_number} (Invalid account format)")
            
            account_no = account_parts[0]
            account_code = account_parts[1]
            
            # PyKis 클라이언트 생성 (자동 토큰 관리)
            # Create PyKis client (automatic token management)
            # python-kis는 토큰을 자동으로 관리하고 갱신합니다.
            # python-kis automatically manages and refreshes tokens.
            
            # 계좌번호 형식: "계좌번호-상품코드"
            account_str = f"{account_no}-{account_code}"
            
            # python-kis 2.x는 실전+모의 모두 인증 정보 필요
            # python-kis 2.x requires both real and virtual credentials
            self.kis = PyKis(
                id=kis_config.hts_id,                        # HTS 로그인 ID
                account=account_str,                          # 계좌번호
                appkey=kis_config.app_key,                    # 실전투자 AppKey
                secretkey=kis_config.app_secret,              # 실전투자 SecretKey
                virtual_id=kis_config.hts_id,                 # 모의투자 ID (동일)
                virtual_appkey=kis_config.virtual_app_key,    # 모의투자 AppKey
                virtual_secretkey=kis_config.virtual_app_secret,  # 모의투자 SecretKey
                keep_token=True                               # 토큰 자동 저장
            )
            
            self._is_connected = True
            
            mode_str = "모의투자 (Virtual)" if kis_config.is_virtual else "실전투자 (Real)"
            logger.info(f"✅ KIS API 연결 성공! 모드: {mode_str}")
            logger.info(f"   계좌번호: {kis_config.account_number}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ KIS API 연결 실패: {e}")
            self._is_connected = False
            return False
    
    def is_connected(self) -> bool:
        """
        연결 상태를 반환합니다.
        Returns connection status.
        """
        return self._is_connected
    
    # ========================================
    # 시세 조회 메서드 (Price Query Methods)
    # ========================================
    
    def get_current_price(self, symbol: str) -> Optional[dict]:
        """
        현재가 정보를 조회합니다.
        Get current price information.
        
        Args:
            symbol: 종목 코드 (Stock code)
        
        Returns:
            dict: 현재가 정보 또는 None
                - price: 현재가
                - change: 전일 대비 변동
                - change_rate: 전일 대비 변동률 (%)
                - volume: 거래량
                - prev_close: 전일 종가
        """
        if not self._check_connection():
            return None
        
        try:
            # 국내 주식 현재가 조회
            # Get domestic stock current price
            stock = self.kis.stock(symbol)
            quote = stock.quote()
            
            result = {
                "symbol": symbol,
                "name": quote.name if hasattr(quote, 'name') else symbol,
                "price": quote.price,  # 현재가
                "change": quote.change,  # 전일 대비
                "change_rate": quote.rate * 100 if hasattr(quote, 'rate') else 0,  # 등락률 (%)
                "volume": quote.volume if hasattr(quote, 'volume') else 0,  # 거래량
                "prev_close": quote.prev_close if hasattr(quote, 'prev_close') else (quote.price - quote.change),
                "high": quote.high if hasattr(quote, 'high') else 0,  # 고가
                "low": quote.low if hasattr(quote, 'low') else 0,  # 저가
                "open": quote.open if hasattr(quote, 'open') else 0,  # 시가
                "timestamp": datetime.now().isoformat()
            }
            
            logger.debug(f"현재가 조회 성공 - {symbol}: {result['price']:,}원")
            return result
            
        except Exception as e:
            logger.error(f"현재가 조회 실패 ({symbol}): {e}")
            return None
    
    def get_previous_close(self, symbol: str) -> Optional[int]:
        """
        전일 종가를 조회합니다.
        Get previous closing price.
        
        Args:
            symbol: 종목 코드 (Stock code)
        
        Returns:
            int: 전일 종가 또는 None
        """
        price_info = self.get_current_price(symbol)
        if price_info:
            return price_info.get("prev_close")
        return None
    
    # ========================================
    # 주문 메서드 (Order Methods)
    # ========================================
    
    def buy_market_order(self, symbol: str, quantity: int) -> Optional[KisOrder]:
        """
        시장가 매수 주문을 실행합니다.
        Execute market buy order.
        
        Args:
            symbol: 종목 코드 (Stock code)
            quantity: 주문 수량 (Order quantity)
        
        Returns:
            KisOrder: 주문 결과 또는 None
        """
        if not self._check_connection():
            return None
        
        try:
            stock = self.kis.stock(symbol)
            
            # 시장가 매수 주문
            # Market buy order
            order = stock.buy(qty=quantity)
            
            logger.info(f"✅ 시장가 매수 주문 성공!")
            logger.info(f"   종목: {symbol}, 수량: {quantity}주")
            logger.info(f"   주문번호: {order.order_no if hasattr(order, 'order_no') else order}")
            
            return order
            
        except Exception as e:
            logger.error(f"❌ 매수 주문 실패 ({symbol}, {quantity}주): {e}")
            return None
    
    def buy_limit_order(self, symbol: str, quantity: int, price: int) -> Optional[KisOrder]:
        """
        지정가 매수 주문을 실행합니다.
        Execute limit buy order.
        
        Args:
            symbol: 종목 코드 (Stock code)
            quantity: 주문 수량 (Order quantity)
            price: 지정가 (Limit price)
        
        Returns:
            KisOrder: 주문 결과 또는 None
        """
        if not self._check_connection():
            return None
        
        try:
            stock = self.kis.stock(symbol)
            
            # 지정가 매수 주문
            # Limit buy order
            order = stock.buy(price=price, qty=quantity)
            
            logger.info(f"✅ 지정가 매수 주문 성공!")
            logger.info(f"   종목: {symbol}, 수량: {quantity}주, 가격: {price:,}원")
            logger.info(f"   주문번호: {order.order_no if hasattr(order, 'order_no') else order}")
            
            return order
            
        except Exception as e:
            logger.error(f"❌ 매수 주문 실패 ({symbol}, {quantity}주, {price:,}원): {e}")
            return None
    
    def sell_market_order(self, symbol: str, quantity: int) -> Optional[KisOrder]:
        """
        시장가 매도 주문을 실행합니다.
        Execute market sell order.
        
        Args:
            symbol: 종목 코드 (Stock code)
            quantity: 주문 수량 (Order quantity)
        
        Returns:
            KisOrder: 주문 결과 또는 None
        """
        if not self._check_connection():
            return None
        
        try:
            stock = self.kis.stock(symbol)
            
            # 시장가 매도 주문
            # Market sell order
            order = stock.sell(qty=quantity)
            
            logger.info(f"✅ 시장가 매도 주문 성공!")
            logger.info(f"   종목: {symbol}, 수량: {quantity}주")
            logger.info(f"   주문번호: {order.order_no if hasattr(order, 'order_no') else order}")
            
            return order
            
        except Exception as e:
            logger.error(f"❌ 매도 주문 실패 ({symbol}, {quantity}주): {e}")
            return None
    
    def sell_limit_order(self, symbol: str, quantity: int, price: int) -> Optional[KisOrder]:
        """
        지정가 매도 주문을 실행합니다.
        Execute limit sell order.
        
        Args:
            symbol: 종목 코드 (Stock code)
            quantity: 주문 수량 (Order quantity)
            price: 지정가 (Limit price)
        
        Returns:
            KisOrder: 주문 결과 또는 None
        """
        if not self._check_connection():
            return None
        
        try:
            stock = self.kis.stock(symbol)
            
            # 지정가 매도 주문
            # Limit sell order
            order = stock.sell(price=price, qty=quantity)
            
            logger.info(f"✅ 지정가 매도 주문 성공!")
            logger.info(f"   종목: {symbol}, 수량: {quantity}주, 가격: {price:,}원")
            logger.info(f"   주문번호: {order.order_no if hasattr(order, 'order_no') else order}")
            
            return order
            
        except Exception as e:
            logger.error(f"❌ 매도 주문 실패 ({symbol}, {quantity}주, {price:,}원): {e}")
            return None
    
    # ========================================
    # 계좌 조회 메서드 (Account Query Methods)
    # ========================================
    
    def get_balance(self) -> Optional[dict]:
        """
        계좌 잔고를 조회합니다.
        Get account balance.
        
        Returns:
            dict: 잔고 정보 또는 None
        """
        if not self._check_connection():
            return None
        
        try:
            balance = self.kis.account().balance()
            
            result = {
                "total_value": balance.total if hasattr(balance, 'total') else 0,  # 총 평가금액
                "cash": balance.dnca_tot_amt if hasattr(balance, 'dnca_tot_amt') else 0,  # 예수금
                "stocks": []  # 보유 종목 리스트
            }
            
            # 보유 종목 정보
            if hasattr(balance, 'stocks'):
                for stock in balance.stocks:
                    result["stocks"].append({
                        "symbol": stock.symbol if hasattr(stock, 'symbol') else "",
                        "name": stock.name if hasattr(stock, 'name') else "",
                        "quantity": stock.qty if hasattr(stock, 'qty') else 0,
                        "avg_price": stock.avg_price if hasattr(stock, 'avg_price') else 0,
                        "current_price": stock.price if hasattr(stock, 'price') else 0,
                        "profit_loss": stock.profit if hasattr(stock, 'profit') else 0,
                        "profit_rate": stock.profit_rate if hasattr(stock, 'profit_rate') else 0
                    })
            
            logger.info(f"잔고 조회 성공 - 총 평가금액: {result['total_value']:,}원")
            return result
            
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return None
    
    def get_position(self, symbol: str) -> int:
        """
        특정 종목의 보유 수량을 조회합니다.
        Get position quantity for a specific stock.
        
        Args:
            symbol: 종목 코드 (Stock code)
        
        Returns:
            int: 보유 수량 (0 if not found or error)
        """
        balance = self.get_balance()
        if balance and "stocks" in balance:
            for stock in balance["stocks"]:
                if stock.get("symbol") == symbol:
                    return stock.get("quantity", 0)
        return 0
    
    # ========================================
    # 일봉 데이터 조회 메서드 (Daily OHLCV Methods)
    # ========================================
    
    def get_daily_ohlcv(self, symbol: str, count: int = 200) -> Optional[List[dict]]:
        """
        일봉(일별) OHLCV 데이터를 조회합니다.
        Get daily OHLCV data.
        
        Args:
            symbol: 종목 코드 (Stock code)
            count: 조회할 일수 (Number of days to fetch)
        
        Returns:
            List[dict]: 일봉 데이터 리스트 (최신순) 또는 None
                - date: 날짜 (YYYYMMDD)
                - open: 시가
                - high: 고가
                - low: 저가
                - close: 종가
                - volume: 거래량
        """
        if not self._check_connection():
            return None
        
        try:
            from datetime import date, timedelta
            import pandas as pd
            
            # python-kis 2.x의 일봉 조회
            # Fetch daily candles using python-kis 2.x
            stock = self.kis.stock(symbol)
            
            # 시작일 계산 (count일 전부터)
            start_date = date.today() - timedelta(days=count)
            
            # daily_chart 메서드로 일봉 조회
            chart = stock.daily_chart(start=start_date)
            
            # DataFrame으로 변환
            df = chart.df()
            
            # 데이터를 딕셔너리 리스트로 변환
            result = []
            for idx, row in df.iterrows():
                result.append({
                    "date": str(row['time']) if 'time' in df.columns else str(idx),
                    "open": int(row['open']),
                    "high": int(row['high']),
                    "low": int(row['low']),
                    "close": int(row['close']),
                    "volume": int(row['volume'])
                })
            
            logger.debug(f"일봉 조회 성공 - {symbol}: {len(result)}개")
            return result
            
        except Exception as e:
            logger.error(f"일봉 조회 실패 ({symbol}): {e}")
            return None
    
    def get_daily_prices_df(self, symbol: str, count: int = 200):
        """
        일봉 데이터를 pandas DataFrame으로 반환합니다.
        Get daily OHLCV data as pandas DataFrame.
        
        Args:
            symbol: 종목 코드 (Stock code)
            count: 조회할 일수 (Number of days)
        
        Returns:
            pd.DataFrame: 일봉 DataFrame (date 인덱스) 또는 None
        """
        if not self._check_connection():
            return None
        
        try:
            from datetime import date, timedelta
            import pandas as pd
            
            # python-kis 2.x의 일봉 조회
            stock = self.kis.stock(symbol)
            
            # 시작일 계산
            start_date = date.today() - timedelta(days=count)
            
            # daily_chart로 데이터 조회
            chart = stock.daily_chart(start=start_date)
            df = chart.df()
            
            # time 컬럼을 인덱스로 설정
            if 'time' in df.columns:
                df['date'] = pd.to_datetime(df['time'])
                df.set_index('date', inplace=True)
                df.drop('time', axis=1, inplace=True, errors='ignore')
            
            df.sort_index(inplace=True)  # 날짜 오름차순 정렬
            
            logger.debug(f"일봉 DataFrame 조회 성공 - {symbol}: {len(df)}행")
            return df
            
        except Exception as e:
            logger.error(f"일봉 DataFrame 조회 실패 ({symbol}): {e}")
            return None
    
    # ========================================
    # 분봉 데이터 조회 메서드 (Minute Chart Methods)
    # ========================================
    
    def get_minute_chart_df(self, symbol: str, period: int = 1, max_retries: int = 3):
        """
        분봉 데이터를 pandas DataFrame으로 반환합니다.
        Get minute chart data as pandas DataFrame.
        
        Args:
            symbol: 종목 코드 (Stock code)
            period: 분봉 주기 (1, 3, 5, 10, 15, 30, 60분)
            max_retries: 최대 재시도 횟수
        
        Returns:
            pd.DataFrame: 분봉 DataFrame (date 인덱스) 또는 None
        """
        import time as time_module
        
        if not self._check_connection():
            return None
        
        for attempt in range(max_retries):
            try:
                import pandas as pd
                
                # python-kis 2.x의 분봉 조회
                stock = self.kis.stock(symbol)
                
                # chart 메서드로 분봉 조회 (period=1 for 1분봉)
                chart = stock.chart(period=period)
                df = chart.df()
                
                # time 컬럼을 인덱스로 설정
                if 'time' in df.columns:
                    df['date'] = pd.to_datetime(df['time'])
                    df.set_index('date', inplace=True)
                    df.drop('time', axis=1, inplace=True, errors='ignore')
                
                df.sort_index(inplace=True)  # 시간 오름차순 정렬
                
                logger.debug(f"분봉 DataFrame 조회 성공 - {symbol}: {len(df)}행 ({period}분봉)")
                return df
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 2초, 4초, 6초...
                    logger.warning(f"분봉 조회 재시도 ({symbol}): {attempt + 1}/{max_retries}, {wait_time}초 대기")
                    time_module.sleep(wait_time)
                else:
                    logger.error(f"분봉 DataFrame 조회 실패 ({symbol}): {e}")
                    return None
    
    # ========================================
    # 내부 헬퍼 메서드 (Internal Helper Methods)
    # ========================================
    
    def _check_connection(self) -> bool:
        """
        연결 상태를 확인합니다.
        Check connection status.
        """
        if not self._is_connected or self.kis is None:
            logger.warning("KIS API에 연결되어 있지 않습니다. connect()를 먼저 호출하세요.")
            return False
        return True


# 싱글톤 인스턴스 (선택적 사용)
# Singleton instance (optional use)
_client_instance: Optional[KISClient] = None


def get_kis_client() -> KISClient:
    """
    KISClient 싱글톤 인스턴스를 반환합니다.
    Returns KISClient singleton instance.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = KISClient()
    return _client_instance


if __name__ == "__main__":
    # 테스트 실행
    # Test run
    import sys
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_config.format,
        datefmt=log_config.date_format
    )
    
    print("=" * 50)
    print("KIS Client 테스트 (KIS Client Test)")
    print("=" * 50)
    
    client = KISClient()
    
    if client.connect():
        print("\n📈 삼성전자 현재가 조회 테스트...")
        price_info = client.get_current_price("005930")
        if price_info:
            print(f"   종목: {price_info['name']}")
            print(f"   현재가: {price_info['price']:,}원")
            print(f"   전일대비: {price_info['change']:+,}원 ({price_info['change_rate']:+.2f}%)")
            print(f"   전일종가: {price_info['prev_close']:,}원")
        
        print("\n💰 계좌 잔고 조회 테스트...")
        balance = client.get_balance()
        if balance:
            print(f"   총 평가금액: {balance['total_value']:,}원")
    else:
        print("❌ API 연결 실패. config.py에서 API 키를 확인하세요.")
        sys.exit(1)
