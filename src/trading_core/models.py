"""GUI- and exchange-independent domain models."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from .identity import position_id_from_entry
from .validation import finite, percent, text

class SignalSide(str, Enum): LONG="LONG"; SHORT="SHORT"; HOLD="HOLD"
class ExitReason(str, Enum):
    TAKE_PROFIT="TP"; STOP_LOSS="SL"; BREAK_EVEN="BREAK EVEN"; TRAILING_STOP="TRAILING STOP"; END_OF_DATA="EOD"; MANUAL="MANUAL"; MANUAL_CLOSE="MANUAL CLOSE"; PREVIEW_CLOSE="PREVIEW CLOSE"; REVERSE="REVERSE CLOSE"
class PositionStatus(str, Enum): OPEN="OPEN"; CLOSED="CLOSED"
class EngineEventType(str, Enum):
    CANDLE="CANDLE"; SIGNAL="SIGNAL"; SIGNAL_REJECTED="SIGNAL_REJECTED"; POSITION_OPENED="POSITION_OPENED"; POSITION_UPDATED="POSITION_UPDATED"; POSITION_CLOSED="POSITION_CLOSED"; PORTFOLIO_UPDATED="PORTFOLIO_UPDATED"; STOP_UPDATED="STOP_UPDATED"; BREAK_EVEN_ACTIVATED="BREAK_EVEN_ACTIVATED"; TRAILING_ACTIVATED="TRAILING_ACTIVATED"; EQUITY_UPDATED="EQUITY_UPDATED"
def _ts(name,value):
    if isinstance(value,bool) or not isinstance(value,int) or value<0: raise ValueError(f"{name} must be a non-negative integer")

@dataclass(frozen=True,slots=True)
class Candle:
    timestamp_ms:int; open:float; high:float; low:float; close:float; volume:float
    def __post_init__(self):
        _ts("timestamp_ms",self.timestamp_ms)
        for n in ("open","high","low","close"): finite(n,getattr(self,n),positive=True)
        finite("volume",self.volume,minimum=0)
        if self.high<max(self.open,self.close) or self.low>min(self.open,self.close) or self.high<self.low: raise ValueError("invalid OHLC relationship")
@dataclass(frozen=True,slots=True)
class MarketContext:
    symbol:str; timeframe:str; candles:tuple[Candle,...]
    def __post_init__(self):
        text("symbol",self.symbol); text("timeframe",self.timeframe); stamps=[c.timestamp_ms for c in self.candles]
        if stamps!=sorted(stamps) or len(stamps)!=len(set(stamps)): raise ValueError("candle timestamps must be strictly increasing and unique")
    @property
    def timestamp_ms(self): return self.candles[-1].timestamp_ms if self.candles else None
@dataclass(frozen=True,slots=True)
class Signal:
    side:SignalSide; timestamp_ms:int; price:float|None=None; reason:str=""; source:str|None=None; confidence:float|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        _ts("timestamp_ms",self.timestamp_ms)
        if self.price is not None: finite("price",self.price,positive=True)
        if self.confidence is not None: percent("confidence",self.confidence)
    @property
    def timestamp(self): return self.timestamp_ms
    @property
    def reference_price(self): return self.price
    @property
    def symbol(self): return self.metadata.get("symbol")
    @property
    def timeframe(self): return self.metadata.get("timeframe")
    @property
    def score(self): return self.metadata.get("score")
    @property
    def reasons(self): return self.metadata.get("reasons", ())
    @property
    def rsi(self): return self.metadata.get("rsi")
    @property
    def rsi_zone(self): return self.metadata.get("rsi_zone")
    @property
    def sma20(self): return self.metadata.get("sma20")
    @property
    def sma50(self): return self.metadata.get("sma50")
    @property
    def atr(self): return self.metadata.get("atr")
    @property
    def atr_percent(self): return self.metadata.get("atr_pct")
    @property
    def filter_states(self):
        keys=("atr_ok","mtf_ok","signal_cooldown_blocked","trade_cooldown_blocked","position_blocked","countertrend_allowed")
        return {key:self.metadata.get(key) for key in keys}
@dataclass(frozen=True,slots=True)
class StrategyState:
    last_rsi_zone:str="NEUTRAL"; rsi_history:tuple[float,...]=(); last_rsi_signal_timestamp_ms:int|None=None; last_trade_close_timestamp_ms:int|None=None; position_open:bool=False; mtf_trend:str="NEUTRAL"
    def __post_init__(self):
        for v in self.rsi_history: finite("rsi_history item",v)
        for n in ("last_rsi_signal_timestamp_ms","last_trade_close_timestamp_ms"):
            if getattr(self,n) is not None: _ts(n,getattr(self,n))
    @property
    def last_signal_timestamp(self): return self.last_rsi_signal_timestamp_ms
    @property
    def last_trade_close_timestamp(self): return self.last_trade_close_timestamp_ms
@dataclass(frozen=True,slots=True)
class Position:
    symbol:str; timeframe:str; entry_timestamp_ms:int; side:SignalSide; entry_price:float; quantity:float; take_profit:float; stop_loss:float; reason:str=""; status:PositionStatus=PositionStatus.OPEN; notional:float|None=None; metadata:Mapping[str,Any]=field(default_factory=dict); position_id:str=field(init=False)
    def __post_init__(self):
        text("symbol",self.symbol); text("timeframe",self.timeframe); _ts("entry_timestamp_ms",self.entry_timestamp_ms)
        if self.side is SignalSide.HOLD: raise ValueError("position side cannot be HOLD")
        for n in ("entry_price","quantity","take_profit","stop_loss"): finite(n,getattr(self,n),positive=True)
        if self.notional is not None: finite("notional",self.notional,positive=True)
        object.__setattr__(self,"position_id",position_id_from_entry(self.symbol,self.timeframe,self.entry_timestamp_ms))
@dataclass(frozen=True,slots=True)
class Trade:
    symbol:str; side:SignalSide; entry_price:float; exit_price:float; quantity:float; pnl:float; exit_reason:ExitReason; entry_reason:str; balance:float; opened_at:float; closed_at:float; hold_time_sec:float|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        text("symbol",self.symbol)
        if self.side is SignalSide.HOLD: raise ValueError("trade side cannot be HOLD")
        for n in ("entry_price","exit_price","quantity"): finite(n,getattr(self,n),positive=True)
        for n in ("pnl","balance","opened_at","closed_at"): finite(n,getattr(self,n))
        if self.opened_at<0 or self.closed_at<self.opened_at: raise ValueError("trade timestamps must be non-negative and ordered")
        if self.hold_time_sec is not None: finite("hold_time_sec",self.hold_time_sec,minimum=0)
@dataclass(frozen=True,slots=True)
class PortfolioSnapshot:
    timestamp:float; balance:float; equity:float
    def __post_init__(self):
        for n in ("timestamp","balance","equity"): finite(n,getattr(self,n))
        if self.timestamp<0: raise ValueError("timestamp must be non-negative")
@dataclass(frozen=True,slots=True)
class PerformanceMetrics:
    trades:int; end_balance:float; pnl:float; pnl_pct:float; winrate:float; profit_factor:float; max_drawdown:float
    def __post_init__(self):
        if isinstance(self.trades,bool) or not isinstance(self.trades,int) or self.trades<0: raise ValueError("trades must be a non-negative integer")
        for n in ("end_balance","pnl","pnl_pct","winrate","profit_factor","max_drawdown"): finite(n,getattr(self,n))
        if not 0<=self.winrate<=100 or self.profit_factor<0 or not -100<=self.max_drawdown<=0: raise ValueError("invalid metric range")
@dataclass(frozen=True,slots=True)
class EngineEvent:
    event_type:EngineEventType; timestamp_ms:int; payload:Any=None
    def __post_init__(self): _ts("timestamp_ms",self.timestamp_ms)
@dataclass(frozen=True,slots=True)
class ReplayResult:
    metrics:PerformanceMetrics; trades:tuple[Trade,...]=(); equity_curve:tuple[PortfolioSnapshot,...]=(); metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if self.trades and self.metrics.trades!=len(self.trades): raise ValueError("metrics.trades must match supplied trades")
        stamps=[p.timestamp for p in self.equity_curve]
        if stamps!=sorted(stamps) or len(stamps)!=len(set(stamps)): raise ValueError("equity timestamps must be increasing and unique")
