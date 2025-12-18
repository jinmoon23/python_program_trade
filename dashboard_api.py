#!/usr/bin/env python3
"""
Trading Dashboard API Server
트레이딩 대시보드 백엔드 API
"""

import os
import json
import glob
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 경로 설정
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
POSITIONS_FILE = BASE_DIR / "positions.json"
TRADES_FILE = BASE_DIR / "trades.json"
BACKTEST_DIR = BASE_DIR / "backtest_results"


def load_json_file(filepath, default=None):
    """JSON 파일 로드"""
    if default is None:
        default = {}
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"JSON 로드 오류 ({filepath}): {e}")
    return default


def get_service_status(service_name):
    """systemd 서비스 상태 조회"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == 'active'
    except:
        return False


def get_recent_logs(log_file, lines=50):
    """최근 로그 조회"""
    try:
        log_path = LOGS_DIR / log_file
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
    except Exception as e:
        print(f"로그 조회 오류: {e}")
    return []


def parse_trade_log(log_lines):
    """거래 로그 파싱"""
    trades = []
    for line in log_lines:
        if '매수' in line or '매도' in line or 'BUY' in line or 'SELL' in line:
            trades.append(line.strip())
    return trades[-20:]  # 최근 20건


@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'server': 'trading-dashboard-api'
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """전체 시스템 상태"""
    strategies = {
        'hybrid': {
            'name': '단기 전략 (Hybrid)',
            'service': 'trading-bot-ma',
            'active': get_service_status('trading-bot-ma'),
            'description': 'WebSocket 실시간 + 10분 폴링 (20/60 MA)',
            'log_file': 'bot_ma.log'
        },
        'cosmetics': {
            'name': '중장기 전략 (Cosmetics)',
            'service': 'trading-bot-cosmetics',
            'active': get_service_status('trading-bot-cosmetics'),
            'description': '화장품주 추세추종 (50/200 SMA)',
            'log_file': 'bot_cosmetics.log'
        }
    }
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'strategies': strategies,
        'market_open': is_market_open()
    })


def is_market_open():
    """장 운영 시간 체크"""
    now = datetime.now()
    # 주말 체크
    if now.weekday() >= 5:
        return False
    # 시간 체크 (09:00 ~ 15:30)
    market_open = now.replace(hour=9, minute=0, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    return market_open <= now <= market_close


@app.route('/api/positions', methods=['GET'])
def get_positions():
    """현재 보유 포지션"""
    # 여러 소스에서 포지션 데이터 수집
    positions = []
    
    # 1. positions.json에서 로드
    pos_data = load_json_file(POSITIONS_FILE, {})
    if isinstance(pos_data, dict):
        for symbol, data in pos_data.items():
            positions.append({
                'symbol': symbol,
                'name': data.get('name', symbol),
                'quantity': data.get('quantity', 0),
                'entry_price': data.get('entry_price', 0),
                'current_price': data.get('current_price', 0),
                'pnl_pct': data.get('pnl_pct', 0),
                'strategy': data.get('strategy', 'unknown'),
                'entry_date': data.get('entry_date', '')
            })
    
    # 2. 전략별 포지션 파일 체크
    for pattern in ['*_positions.json', 'hybrid_*.json', 'cosmetics_*.json']:
        for file in glob.glob(str(BASE_DIR / pattern)):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        positions.extend(data)
                    elif isinstance(data, dict) and 'positions' in data:
                        positions.extend(data['positions'])
            except:
                pass
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'count': len(positions),
        'positions': positions
    })


@app.route('/api/trades', methods=['GET'])
def get_trades():
    """거래 내역"""
    limit = request.args.get('limit', 50, type=int)
    strategy = request.args.get('strategy', None)
    
    trades = []
    
    # trades.json에서 로드
    trades_data = load_json_file(TRADES_FILE, [])
    if isinstance(trades_data, list):
        trades.extend(trades_data)
    
    # 로그에서 거래 내역 파싱
    log_files = ['bot_ma.log', 'bot_cosmetics.log', 'bot.log']
    for log_file in log_files:
        log_lines = get_recent_logs(log_file, 200)
        parsed = parse_trade_log(log_lines)
        for line in parsed:
            trades.append({
                'timestamp': '',
                'raw': line,
                'source': log_file
            })
    
    # 필터링
    if strategy:
        trades = [t for t in trades if t.get('strategy') == strategy]
    
    # 최신순 정렬 및 제한
    trades = trades[-limit:]
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'count': len(trades),
        'trades': trades
    })


@app.route('/api/logs/<strategy>', methods=['GET'])
def get_strategy_logs(strategy):
    """전략별 로그 조회"""
    lines = request.args.get('lines', 100, type=int)
    
    log_map = {
        'hybrid': 'bot_ma.log',
        'cosmetics': 'bot_cosmetics.log',
        'ma': 'bot_ma.log',
        'dmv': 'bot.log'
    }
    
    log_file = log_map.get(strategy, f'bot_{strategy}.log')
    log_lines = get_recent_logs(log_file, lines)
    
    # 에러 로그도 함께 조회
    error_log_file = log_file.replace('.log', '_error.log')
    error_lines = get_recent_logs(error_log_file, 50)
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'strategy': strategy,
        'log_file': log_file,
        'lines': [''.join(log_lines)],
        'errors': [''.join(error_lines)] if error_lines else []
    })


@app.route('/api/performance', methods=['GET'])
def get_performance():
    """성과 요약"""
    # 백테스트 결과에서 최신 데이터 로드
    performance = {
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0,
        'total_pnl': 0,
        'avg_pnl_pct': 0,
        'max_drawdown': 0
    }
    
    # 최신 백테스트 결과 찾기
    if BACKTEST_DIR.exists():
        result_files = sorted(BACKTEST_DIR.glob('*.json'), reverse=True)
        if result_files:
            try:
                with open(result_files[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'performance' in data:
                        performance.update(data['performance'])
            except:
                pass
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'performance': performance
    })


@app.route('/api/stocks', methods=['GET'])
def get_monitored_stocks():
    """모니터링 중인 종목 목록"""
    stocks = {
        'hybrid': {
            'realtime': [],
            'polling': []
        },
        'cosmetics': []
    }
    
    # config에서 종목 로드 시도
    try:
        from config import ma_config
        stocks['hybrid']['realtime'] = list(ma_config.realtime_stocks.items())[:10]
        stocks['hybrid']['polling'] = list(ma_config.polling_stocks.items())[:10]
    except:
        pass
    
    try:
        from cosmetics_config import COSMETICS_STOCKS
        stocks['cosmetics'] = list(COSMETICS_STOCKS.items())[:10]
    except:
        pass
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'stocks': stocks
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Trading Dashboard API Server")
    print("=" * 60)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Logs Directory: {LOGS_DIR}")
    print("=" * 60)
    
    # 개발 모드로 실행
    app.run(host='0.0.0.0', port=5001, debug=True)
