from typing import Any,Iterable,Mapping,Sequence
from .models import Candle,ExitReason,PerformanceMetrics,ReplayResult,Signal,SignalSide,Trade
def candles_from_ccxt_ohlcv(rows:Iterable[Sequence[Any]])->tuple[Candle,...]:
    out=[]
    for i,row in enumerate(rows):
        if len(row)<6: raise ValueError(f"OHLCV row {i} must contain at least six values")
        if isinstance(row[0],bool) or not isinstance(row[0],int): raise ValueError("CCXT timestamp must be an integer")
        out.append(Candle(row[0],row[1],row[2],row[3],row[4],row[5]))
    stamps=[c.timestamp_ms for c in out]
    if stamps!=sorted(stamps) or len(stamps)!=len(set(stamps)): raise ValueError("OHLCV timestamps must be strictly increasing and unique")
    return tuple(out)
def candles_to_legacy_ohlcv(items): return [[c.timestamp_ms,c.open,c.high,c.low,c.close,c.volume] for c in items]
def trade_from_legacy(d:Mapping[str,Any])->Trade:
    known={"symbol","side","entry","exit","qty","pnl","why","reason","balance","hold_time_sec","open_time","close_time"}
    return Trade(d.get("symbol","UNKNOWN"),SignalSide(d["side"]),d["entry"],d["exit"],d.get("qty",1.),d["pnl"],ExitReason(d.get("why",d.get("reason","EOD"))),d.get("reason",""),d["balance"],d["open_time"],d["close_time"],d.get("hold_time_sec"),{k:v for k,v in d.items() if k not in known})
def trade_to_legacy(t):
    d=dict(t.metadata); d.update(symbol=t.symbol,side=t.side.value,entry=t.entry_price,exit=t.exit_price,qty=t.quantity,pnl=t.pnl,why=t.exit_reason.value,reason=t.entry_reason,balance=t.balance,hold_time_sec=t.hold_time_sec,open_time=t.opened_at,close_time=t.closed_at); return d
def signal_from_legacy(d:Mapping[str,Any],*,timestamp_ms:int,price=None)->Signal:
    known={"signal","signal_reason","signal_source","price","confidence","timestamp_ms"}
    return Signal(SignalSide(d["signal"]),d.get("timestamp_ms",timestamp_ms),d.get("price",price),d.get("signal_reason",""),d.get("signal_source"),d.get("confidence"),{k:v for k,v in d.items() if k not in known})
def signal_to_legacy(s):
    d=dict(s.metadata); d.update(signal=s.side.value,signal_reason=s.reason,signal_source=s.source)
    if s.price is not None: d["price"]=s.price
    if s.confidence is not None: d["confidence"]=s.confidence
    return d
_KEYS=("trades","end_balance","pnl","pnl_pct","winrate","profit_factor","max_drawdown")
def replay_result_from_legacy(d): return ReplayResult(PerformanceMetrics(**{k:d[k] for k in _KEYS}),metadata={k:v for k,v in d.items() if k not in _KEYS})
def replay_result_to_legacy(r):
    d=dict(r.metadata); d.update({k:getattr(r.metrics,k) for k in _KEYS}); return d


def position_to_legacy(position):
    from copy import deepcopy
    d = deepcopy(dict(position.metadata))
    d.update(symbol=position.symbol, timeframe=position.timeframe,
             position_id=position.position_id, entry_timestamp_ms=position.entry_timestamp_ms,
             side=position.side.value,
             entry=position.entry_price, qty=position.quantity,
             notional=position.notional, tp=position.take_profit,
             sl=position.stop_loss, reason=position.reason)
    return d


def position_from_legacy(d, *, timeframe="1m"):
    from copy import deepcopy
    from .models import Position
    opened_at = d.get("open_time", d.get("time"))
    data = deepcopy(dict(d))
    data.setdefault("open_time", opened_at)
    data.setdefault("time", opened_at)
    return Position(d.get("symbol", "UNKNOWN"), d.get("timeframe", timeframe),
                    d.get("entry_timestamp_ms", int(opened_at * 1000)), SignalSide(d.get("side", "LONG")),
                    d["entry"], d["qty"], d["tp"], d["sl"],
                    reason=d.get("reason", ""),
                    notional=d.get("notional", d["entry"] * d["qty"]), metadata=data)


def trade_to_legacy_backtest(trade):
    """Backtest uses reason for the exit and historically omits qty/symbol."""
    return dict(side=trade.side.value, entry=trade.entry_price,
                exit=trade.exit_price, pnl=trade.pnl,
                reason=trade.exit_reason.value, balance=trade.balance,
                open_time=trade.opened_at, close_time=trade.closed_at)
