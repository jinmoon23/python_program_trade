import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || '';

interface Strategy {
  name: string;
  service: string;
  active: boolean;
  description: string;
  log_file: string;
}

interface Position {
  symbol: string;
  name: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl_pct: number;
  strategy: string;
  entry_date: string;
}

interface Trade {
  timestamp: string;
  raw: string;
  source: string;
}

function App() {
  const [strategies, setStrategies] = useState<Record<string, Strategy>>({});
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [logs, setLogs] = useState<string>('');
  const [selectedStrategy, setSelectedStrategy] = useState<string>('hybrid');
  const [marketOpen, setMarketOpen] = useState<boolean>(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  const fetchData = useCallback(async () => {
    try {
      setError('');
      
      // 상태 조회
      const statusRes = await fetch(`${API_BASE}/api/status`);
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setStrategies(statusData.strategies);
        setMarketOpen(statusData.market_open);
      }

      // 포지션 조회
      const posRes = await fetch(`${API_BASE}/api/positions`);
      if (posRes.ok) {
        const posData = await posRes.json();
        setPositions(posData.positions);
      }

      // 거래 내역 조회
      const tradesRes = await fetch(`${API_BASE}/api/trades?limit=20`);
      if (tradesRes.ok) {
        const tradesData = await tradesRes.json();
        setTrades(tradesData.trades);
      }

      // 로그 조회
      const logsRes = await fetch(`${API_BASE}/api/logs/${selectedStrategy}?lines=50`);
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setLogs(logsData.lines.join('\n'));
      }

      setLastUpdate(new Date().toLocaleTimeString('ko-KR'));
      setLoading(false);
    } catch (err) {
      setError('서버 연결 실패. API 서버가 실행 중인지 확인하세요.');
      setLoading(false);
    }
  }, [selectedStrategy]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // 10초마다 갱신
    return () => clearInterval(interval);
  }, [fetchData]);

  const getStatusColor = (active: boolean) => 
    active ? 'bg-green-500' : 'bg-red-500';

  const getPnlColor = (pnl: number) => 
    pnl > 0 ? 'text-green-400' : pnl < 0 ? 'text-red-400' : 'text-gray-400';

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 md:p-6">
      {/* Header */}
      <header className="mb-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white">
              📈 Trading Dashboard
            </h1>
            <p className="text-slate-400 text-sm mt-1">KIS 자동매매 모니터링</p>
          </div>
          <div className="flex items-center gap-4">
            <div className={`px-3 py-1 rounded-full text-sm ${marketOpen ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {marketOpen ? '🟢 장 운영중' : '🔴 장 마감'}
            </div>
            <span className="text-slate-500 text-sm">
              최근 업데이트: {lastUpdate}
            </span>
            <button 
              onClick={fetchData}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm transition"
            >
              🔄 새로고침
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="mb-4 p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-400">
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-xl text-slate-400">로딩 중...</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
          {/* 전략 상태 카드 */}
          <div className="lg:col-span-1">
            <div className="bg-slate-800 rounded-xl p-4 md:p-6 border border-slate-700">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                🤖 전략 상태
              </h2>
              <div className="space-y-4">
                {Object.entries(strategies).map(([key, strategy]) => (
                  <div 
                    key={key}
                    className={`p-4 rounded-lg border cursor-pointer transition ${
                      selectedStrategy === key 
                        ? 'border-blue-500 bg-blue-500/10' 
                        : 'border-slate-600 hover:border-slate-500'
                    }`}
                    onClick={() => setSelectedStrategy(key)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{strategy.name}</span>
                      <span className={`w-3 h-3 rounded-full ${getStatusColor(strategy.active)}`}></span>
                    </div>
                    <p className="text-xs text-slate-400">{strategy.description}</p>
                    <div className="mt-2 text-xs">
                      <span className={strategy.active ? 'text-green-400' : 'text-red-400'}>
                        {strategy.active ? '✅ 실행 중' : '❌ 중지됨'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 요약 통계 */}
            <div className="bg-slate-800 rounded-xl p-4 md:p-6 border border-slate-700 mt-4">
              <h2 className="text-lg font-semibold mb-4">📊 요약</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue-400">{positions.length}</div>
                  <div className="text-xs text-slate-400">보유 종목</div>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-purple-400">{trades.length}</div>
                  <div className="text-xs text-slate-400">최근 거래</div>
                </div>
              </div>
            </div>
          </div>

          {/* 포지션 및 거래 내역 */}
          <div className="lg:col-span-2 space-y-4 md:space-y-6">
            {/* 보유 포지션 */}
            <div className="bg-slate-800 rounded-xl p-4 md:p-6 border border-slate-700">
              <h2 className="text-lg font-semibold mb-4">💼 보유 포지션</h2>
              {positions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-slate-400 border-b border-slate-700">
                        <th className="text-left py-2 px-2">종목</th>
                        <th className="text-right py-2 px-2">수량</th>
                        <th className="text-right py-2 px-2">매수가</th>
                        <th className="text-right py-2 px-2">현재가</th>
                        <th className="text-right py-2 px-2">수익률</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos, idx) => (
                        <tr key={idx} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                          <td className="py-3 px-2">
                            <div className="font-medium">{pos.name}</div>
                            <div className="text-xs text-slate-500">{pos.symbol}</div>
                          </td>
                          <td className="text-right py-3 px-2">{pos.quantity?.toLocaleString()}</td>
                          <td className="text-right py-3 px-2">{pos.entry_price?.toLocaleString()}원</td>
                          <td className="text-right py-3 px-2">{pos.current_price?.toLocaleString()}원</td>
                          <td className={`text-right py-3 px-2 font-medium ${getPnlColor(pos.pnl_pct)}`}>
                            {pos.pnl_pct > 0 ? '+' : ''}{pos.pnl_pct?.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  현재 보유 중인 포지션이 없습니다
                </div>
              )}
            </div>

            {/* 실시간 로그 */}
            <div className="bg-slate-800 rounded-xl p-4 md:p-6 border border-slate-700">
              <h2 className="text-lg font-semibold mb-4">
                📋 실시간 로그 
                <span className="text-sm font-normal text-slate-400 ml-2">
                  ({selectedStrategy === 'hybrid' ? '단기 전략' : '중장기 전략'})
                </span>
              </h2>
              <div className="bg-slate-900 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs">
                {logs ? (
                  <pre className="whitespace-pre-wrap text-slate-300">{logs}</pre>
                ) : (
                  <div className="text-slate-500">로그를 불러오는 중...</div>
                )}
              </div>
            </div>

            {/* 최근 거래 */}
            <div className="bg-slate-800 rounded-xl p-4 md:p-6 border border-slate-700">
              <h2 className="text-lg font-semibold mb-4">📜 최근 거래 신호</h2>
              {trades.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {trades.map((trade, idx) => (
                    <div key={idx} className="bg-slate-700/30 rounded p-2 text-xs font-mono">
                      {trade.raw || JSON.stringify(trade)}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-slate-500">
                  최근 거래 내역이 없습니다
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-8 text-center text-slate-500 text-sm">
        KIS Trading Bot Dashboard © 2025
      </footer>
    </div>
  );
}

export default App;
