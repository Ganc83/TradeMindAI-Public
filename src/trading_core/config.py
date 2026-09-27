from dataclasses import dataclass
from .validation import finite,percent,text
@dataclass(frozen=True,slots=True)
class StrategyConfig:
    sma_fast:int=20; sma_slow:int=50; rsi_period:int=14; entry_score_threshold:float=60.; atr_filter_enabled:bool=True; atr_period:int=14; atr_min_percent:float=.30; mtf_enabled:bool=True; mtf_timeframe:str="15m"; signal_cooldown_seconds:float=60.; trade_cooldown_seconds:float=180.
    def __post_init__(self):
        for n in ("sma_fast","sma_slow","rsi_period","atr_period"):
            v=getattr(self,n)
            if isinstance(v,bool) or not isinstance(v,int) or v<=0: raise ValueError(f"{n} must be a positive integer")
        if self.sma_fast>=self.sma_slow: raise ValueError("sma_fast must be smaller than sma_slow")
        percent("entry_score_threshold",self.entry_score_threshold); percent("atr_min_percent",self.atr_min_percent); text("mtf_timeframe",self.mtf_timeframe)
        finite("signal_cooldown_seconds",self.signal_cooldown_seconds,minimum=0); finite("trade_cooldown_seconds",self.trade_cooldown_seconds,minimum=0)
@dataclass(frozen=True,slots=True)
class RiskConfig:
    risk_percent:float=10.; fixed_amount:float=250.; max_notional_percent:float=100.; risk_mode:str="PERCENT"
    def __post_init__(self):
        percent("risk_percent",self.risk_percent,allow_zero=False); finite("fixed_amount",self.fixed_amount,positive=True); percent("max_notional_percent",self.max_notional_percent,allow_zero=False)
        if self.risk_mode not in ("PERCENT", "FIXED"): raise ValueError("risk_mode must be PERCENT or FIXED")
@dataclass(frozen=True,slots=True)
class PositionManagementConfig:
    take_profit_percent:float=2.; stop_loss_percent:float=1.; break_even_trigger_percent:float=1.; trailing_activation_percent:float=1.5; trailing_distance_percent:float=1.5; use_atr_stop:bool=False; atr_period:int=14; atr_stop_multiplier:float=1.5; atr_take_profit_multiplier:float=3.
    def __post_init__(self):
        for n in ("take_profit_percent","stop_loss_percent","break_even_trigger_percent","trailing_activation_percent","trailing_distance_percent"): percent(n,getattr(self,n),allow_zero=False)
        if not isinstance(self.use_atr_stop, bool): raise ValueError("use_atr_stop must be a boolean")
        if isinstance(self.atr_period,bool) or not isinstance(self.atr_period,int) or self.atr_period<=0: raise ValueError("atr_period must be a positive integer")
        finite("atr_stop_multiplier",self.atr_stop_multiplier,positive=True); finite("atr_take_profit_multiplier",self.atr_take_profit_multiplier,positive=True)
@dataclass(frozen=True,slots=True)
class ExecutionConfig:
    fee_rate:float=.001; trade_cooldown_seconds:float=180.; live_trading_enabled:bool=False
    def __post_init__(self):
        finite("fee_rate",self.fee_rate,minimum=0); finite("trade_cooldown_seconds",self.trade_cooldown_seconds,minimum=0)
        if self.fee_rate>1: raise ValueError("fee_rate must be in [0, 1]")
