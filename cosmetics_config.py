"""
cosmetics_config.py - 화장품 추세추종 전략 설정
Cosmetics Trend-Following Strategy Configuration

47개 한국 화장품 관련 종목에 대한 골든크로스/데스크로스 전략
Golden Cross / Death Cross strategy for 47 Korean cosmetics stocks

전략 개요:
- 매수: 50일 SMA가 200일 SMA 상향 돌파 (골든크로스)
- 매도: 50일 SMA가 200일 SMA 하향 돌파 (데스크로스)
- 리스크 관리: 매수 후 최고가 대비 15% 하락 시 트레일링 스탑
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class CosmeticsStrategyConfig:
    """
    화장품 추세추종 전략 설정 클래스
    Cosmetics Trend-Following Strategy Configuration
    """
    
    # ========================================
    # 이동평균선 설정 (Moving Average Settings)
    # ========================================
    short_ma_period: int = 50      # 단기 이평선 (50일)
    long_ma_period: int = 200      # 장기 이평선 (200일)
    
    # ========================================
    # 트레일링 스탑 설정 (Trailing Stop Settings)
    # ========================================
    trailing_stop_pct: float = 15.0   # 트레일링 스탑 % (최고가 대비 하락률)
    use_trailing_stop: bool = True    # 트레일링 스탑 사용 여부
    
    # ========================================
    # 백테스트 설정 (Backtest Settings)
    # ========================================
    lookback_years: int = int(os.getenv("COSMETICS_LOOKBACK_YEARS", "10"))  # 백테스트 기간 (년)
    initial_capital: float = float(os.getenv("COSMETICS_INITIAL_CAPITAL", "100000000"))  # 초기 자본금 (1억원)
    
    # 거래 비용 설정 (Transaction Costs)
    commission_rate: float = 0.015    # 증권사 수수료 (0.015%)
    tax_rate: float = 0.23            # 거래세 (0.23%) - 매도 시에만
    slippage: float = 0.05            # 슬리피지 (0.05%)
    
    # ========================================
    # 포지션 관리 (Position Management)
    # ========================================
    position_sizing: str = "equal_weight"  # "equal_weight" 또는 "fixed_amount"
    max_positions: int = 47               # 최대 동시 보유 종목 수
    position_pct: float = float(os.getenv("COSMETICS_POSITION_PCT", "2.13"))  # 종목당 투자 비중 % (100/47)
    order_quantity: int = int(os.getenv("COSMETICS_ORDER_QTY", "1"))          # 기본 주문 수량
    
    # ========================================
    # 실행 설정 (Execution Settings)
    # ========================================
    signal_check_frequency: str = "daily"  # "daily" 또는 "weekly"
    run_time: str = os.getenv("COSMETICS_RUN_TIME", "15:20")  # 일별 실행 시간 (장 마감 10분 전)
    
    # ========================================
    # 데이터 조회 설정 (Data Fetch Settings)
    # ========================================
    min_data_days: int = 250  # 최소 필요 데이터 일수 (200일 MA + 여유)
    api_delay: float = 0.5    # API 호출 간 대기 시간 (초)
    batch_size: int = 10      # 배치당 종목 수
    batch_delay: float = 2.0  # 배치 간 대기 시간 (초)
    
    # 47개 화장품 관련 종목 딕셔너리
    # 47 Cosmetics-related stocks dictionary
    COSMETICS_STOCKS: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """화장품 종목 리스트 초기화"""
        if not self.COSMETICS_STOCKS:
            self.COSMETICS_STOCKS = {
                # ========================================
                # 대형 화장품 (Large-cap Cosmetics)
                # ========================================
                "090430": "아모레퍼시픽",           # 1. Amorepacific
                "051900": "LG생활건강",             # 2. LG H&H
                "090435": "아모레퍼시픽우",         # 45. Amorepacific Preferred
                "051905": "LG생활건강우",           # 46. LG H&H Preferred
                
                # ========================================
                # OEM/ODM 화장품 제조 (Cosmetics Manufacturing)
                # ========================================
                "192820": "코스맥스",               # 3. Cosmax
                "161890": "한국콜마",               # 4. Kolmar Korea
                "024720": "한국콜마홀딩스",         # 38. Kolmar Korea Holdings
                "200130": "콜마비앤에이치",         # 10. Kolmar BNH
                "241710": "코스메카코리아",         # 16. Cosmecca Korea
                "352480": "씨앤씨인터내셔널",       # 17. C&C International
                "265740": "엔에프씨",               # 19. NFC
                "260930": "씨티케이",               # 21. CTK
                "069110": "코스온",                 # 23. COSON
                "251970": "펌텍코리아",             # 32. Pumtech Korea
                
                # ========================================
                # 브랜드 화장품 (Brand Cosmetics)
                # ========================================
                "237880": "클리오",                 # 5. CLIO
                "078520": "에이블씨엔씨",           # 6. Able C&C (미샤)
                "226320": "잇츠한불",               # 7. It's Hanbul
                "018250": "애경산업",               # 8. Aekyung Industrial
                "214420": "토니모리",               # 11. Tony Moly
                "003350": "한국화장품제조",         # 12. Hankook Cosmetics Mfg
                "027050": "코리아나화장품",         # 13. Coreana Cosmetics
                "123690": "한국화장품",             # 14. Hankook Cosmetics
                "278470": "에이피알",               # 39. APR (메디큐브)
                "018290": "브이티",                 # 40. VT Cosmetics
                "451250": "삐아",                   # 44. PPIA
                
                # ========================================
                # 더마/기능성 화장품 (Derma/Functional Cosmetics)
                # ========================================
                "092730": "네오팜",                 # 9. Neopharm
                "950140": "잉글우드랩",             # 18. Inglewood Lab
                "114840": "아이패밀리에스씨",       # 20. iFamilySC
                "406820": "뷰티스킨",               # 22. Beauty Skin
                "159910": "스킨앤스킨",             # 24. Skin & Skin
                
                # ========================================
                # 바이오/미용 의료기기 (Bio/Medical Aesthetics)
                # ========================================
                "214450": "파마리서치",             # 25. Pharma Research
                "145020": "휴젤",                   # 34. Hugel (보톡스)
                "086900": "메디톡스",               # 35. Medytox (보톡스)
                "216080": "제테마",                 # 36. Jetema
                "048410": "현대바이오",             # 37. Hyundai Bio
                "005690": "파미셀",                 # 31. Pharmicell
                
                # ========================================
                # 원료/소재 (Raw Materials)
                # ========================================
                "134380": "미원상사",               # 26. Miwon Commercial
                "258830": "선진뷰티사이언스",       # 27. Sunjin Beauty Science
                "052260": "현대바이오랜드",         # 28. Hyundai Bioland
                "239610": "에이치엘사이언스",       # 29. HL Science
                "099430": "바이오플러스",           # 30. Bioplus
                "264660": "씨앤지하이테크",         # 33. C&G Hitech
                
                # ========================================
                # 유통/수출 플랫폼 (Distribution/Export)
                # ========================================
                "257720": "실리콘투",               # 15. Silicon2 (스타일코리안)
                "051780": "씨큐브",                 # 42. C-Cube
                "900300": "오가닉티코스메틱",       # 43. Organic Tea Cosmetic
                
                # ========================================
                # 추가 중소형주 (Additional Small/Mid-cap)
                # ========================================
                "950220": "제이준코스메틱",         # 47. JayJun Cosmetic
            }
    
    def get_stock_list(self) -> List[str]:
        """종목 코드 리스트 반환"""
        return list(self.COSMETICS_STOCKS.keys())
    
    def get_stock_name(self, code: str) -> str:
        """종목 코드로 종목명 조회"""
        return self.COSMETICS_STOCKS.get(code, code)
    
    def get_stock_count(self) -> int:
        """총 종목 수 반환"""
        return len(self.COSMETICS_STOCKS)
    
    def get_round_trip_cost(self) -> float:
        """
        왕복 거래 비용 계산 (%)
        매수: 수수료 + 슬리피지
        매도: 수수료 + 거래세 + 슬리피지
        """
        buy_cost = self.commission_rate + self.slippage
        sell_cost = self.commission_rate + self.tax_rate + self.slippage
        return buy_cost + sell_cost
    
    def calculate_position_size(self, capital: float, stock_price: float) -> int:
        """
        포지션 사이즈 계산 (주식 수량)
        
        Args:
            capital: 현재 가용 자본금
            stock_price: 주식 현재가
        
        Returns:
            int: 매수 수량
        """
        if self.position_sizing == "equal_weight":
            # 동일 비중: 자본금을 종목 수로 나눔
            position_value = capital * (self.position_pct / 100)
            return int(position_value / stock_price) if stock_price > 0 else 0
        else:
            # 고정 수량
            return self.order_quantity


@dataclass
class BacktestConfig:
    """
    백테스트 상세 설정
    Backtest Detailed Configuration
    """
    
    # 성과 분석 설정 (Performance Analysis)
    risk_free_rate: float = 3.5           # 무위험 수익률 (%)
    trading_days_per_year: int = 252      # 연간 거래일
    
    # 출력 설정 (Output Settings)
    output_dir: str = "backtest_results"  # 결과 저장 디렉토리
    save_trades: bool = True              # 거래 내역 저장
    save_equity_curve: bool = True        # 자산 곡선 저장
    plot_results: bool = True             # 차트 생성
    
    # 상세 로깅 (Detailed Logging)
    log_trades: bool = True               # 거래 로그
    log_signals: bool = True              # 신호 로그


# 전역 설정 인스턴스
# Global configuration instances
cosmetics_config = CosmeticsStrategyConfig()
backtest_config = BacktestConfig()


def print_cosmetics_config():
    """설정 출력"""
    print("\n" + "=" * 60)
    print("🧴 화장품 추세추종 전략 설정")
    print("   Cosmetics Trend-Following Strategy Configuration")
    print("=" * 60)
    
    print(f"\n📊 전략 파라미터:")
    print(f"   단기 MA: {cosmetics_config.short_ma_period}일")
    print(f"   장기 MA: {cosmetics_config.long_ma_period}일")
    print(f"   트레일링 스탑: {cosmetics_config.trailing_stop_pct}%")
    
    print(f"\n💰 포지션 관리:")
    print(f"   초기 자본금: {cosmetics_config.initial_capital:,.0f}원")
    print(f"   종목당 비중: {cosmetics_config.position_pct:.2f}%")
    print(f"   최대 포지션: {cosmetics_config.max_positions}개")
    
    print(f"\n📈 거래 비용:")
    print(f"   수수료: {cosmetics_config.commission_rate}%")
    print(f"   거래세: {cosmetics_config.tax_rate}%")
    print(f"   슬리피지: {cosmetics_config.slippage}%")
    print(f"   왕복 비용: {cosmetics_config.get_round_trip_cost():.3f}%")
    
    print(f"\n🧴 대상 종목: {cosmetics_config.get_stock_count()}개")
    for i, (code, name) in enumerate(cosmetics_config.COSMETICS_STOCKS.items(), 1):
        print(f"   {i:2d}. {name} ({code})")
    
    print("=" * 60)


if __name__ == "__main__":
    print_cosmetics_config()
