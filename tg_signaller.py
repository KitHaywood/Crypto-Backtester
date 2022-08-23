from time import time
from utils import *
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import pandas as pd
from datetime import datetime,timedelta
import argparse
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.graph_objs.scatter import Line
import json
import warnings
warnings.filterwarnings("ignore")

def get_prices(c,start,end):
    if c=='BTC':
        res = con.execute(f"""
        SELECT DISTINCT * from "test_price_BTC2" 
        WHERE datetimes>='{start}' 
        AND datetimes<='{end}' ORDER BY datetimes DESC;
        """)
    else:
        res = con.execute(f"""
        SELECT DISTINCT * from "test_price_{c}" 
        WHERE datetimes>='{start}' 
        AND datetimes<='{end}' ORDER BY datetimes DESC;
        """)
    prices = pd.DataFrame.from_dict(res.mappings().all())
    prices = prices.set_index('datetimes',drop=False).sort_index(ascending=True)[start:end]
    pricedata = prices.rename(columns={
    "low":"Low",
    "high":"High",
    "close":"Close",
    "open":"Open",
    "datetimes":"datetime"
    })
    return pricedata

def make_tg_inds(p,btd,start,end,ranges,thresh_grads):
    # wp = p[start:end] # working prices
    allindics = {}
    for x in ranges:  
        for y in thresh_grads:
            allindics[(x,y)] = (list(p['Close'].pct_change(periods=x)[start:end]),y)
            
        
    return allindics

def indicator(values):
    return values

def add_metrics(_f): 
    _f['1_eq_ch'] = _f['equity'].pct_change() # pct ch with t-1
    # _f['long_ch'] = _f['equity'].pct_change(periods=5) #pct diff with t-5
    _f['rolling_max'] = [max(_f['equity'].loc[:i]) for i in list(_f.index)]
    _f['rolling_min'] = [min(_f['equity'].loc[:i]) for i in list(_f.index)]
    
    # Here need plan for overall 'equity-ness' of the model
    _f['mean_eq'] = [_f['equity'].loc[:i].mean() for i in list(_f.index)]
    _f['sma_eq'] = [_f['equity'].loc[:i].rolling(20).mean()[-1] for i in list(_f.index)]
    _f['ema_eq'] = [_f['equity'].loc[:i].ewm(span=15,adjust=False).mean()[-1] for i in list(_f.index)]
    return _f


def threshgrad_opstrat(p,c,inds,bstart,bend,btd,ranges,thresh_grads):
    
    p = p[bstart:bend]

    class GradientModel(Strategy):

        allindics = inds
        rng = min(ranges)
        tg = min(thresh_grads)

        def init(self):
            self.rng = self.I(
                    indicator, 
                    self.allindics[(self.rng,self.tg)][0]
                    )

        def next(self):
            if (self.rng < 0) & (abs(self.rng)>=self.tg): 

                if self.position.is_short:
                    pass
                elif self.position.is_long:
                    self.position.close()
                    self.sell()
                else:
                    self.position.close()
                    self.sell()
            elif (self.rng > 0) & (abs(self.rng)>=self.tg): 
                
                if self.position.is_long:
                    pass
                elif self.position.is_short:
                    self.position.close()
                    self.buy()
                elif not self.position:
                    self.position.close()
                    self.buy()      
            else:
                pass
        
    def maximiser(series):
        return series['Equity Final [$]'] if 0 <= series['# Trades'] <= 100 else 0
    
    bt_std = Backtest(
            p,
            GradientModel,
            cash=1_000_000,
            commission=0.002
            )
    btresult = {}
    # OPTIMIZED BACKTEST 
    btresult['bt_std'] = bt_std.optimize(
            rng=ranges,
            tg=thresh_grads,
            maximize=maximiser,
            method="grid",
            constraint=lambda param: param
        )
    # breakpoint()
    opst = {
        "rng":eval(str(btresult['bt_std']._strategy).split('(')[1].split(',')[0].split('=')[1]),
        "tg":btresult['bt_std']._strategy.tg
    }
    return opst

def populate_columns(p,inds,opst,eq,start,end):
    wp = p[start:end]
    print('wp',wp.shape)
    tg = opst['tg']
    rng = opst['rng']
    data = wp.copy()
    print('data',data.shape)
    data['tg'] = [tg for _ in range(wp.shape[0])]
    data['rng'] = [rng for _ in range(wp.shape[0])]
    # breakpoint()
    data['ind'] = p['Close'].pct_change(periods=rng)[start:end]
    breakpoint()

    data['presignal'] = [0 if x==0 else 1 if (data.iloc[x]['ind']>0 and abs((data.iloc[x]['ind'])>tg))
                         else -1 if  (data.iloc[x]['ind']<0 and abs((data.iloc[x]['ind'])>tg))
                         else 0 for x in range(data.shape[0])]
        
    posdf = data[data['presignal']!=0]
    data['signal'] = data['presignal'].replace(to_replace=0,method="ffill")
    data['equity'] =  [None for _ in range(wp.shape[0])]
    data['pct_ch'] = data['Close'].pct_change()
    
    _f = pd.DataFrame().reindex_like(data)
    
    for i,x in data.iterrows():
        if i == min(data.index):
            x['equity'] = eq
            _f.loc[i] = x
        else:
            lasteq = _f.loc[i-timedelta(hours=1)]['equity']
            if x['signal']==0:
                cureq = lasteq
            elif x['signal']==1:
                cureq = lasteq * (1 + x['pct_ch'])
            elif x['signal']==-1:
                cureq = lasteq * (1 + (x['pct_ch']*-1.0))
            x['equity'] = cureq
            try:
                _f.loc[i] = x
            except ValueError as e:
                print(e)
                
    _f = add_metrics(_f)
    
    return _f,posdf


def main(c,md,btd,eq):

    
    ranges = list(range(100,400,20)) # make argparse
    thresh_grads = [round(x,4) for x in list(np.arange(0.01,0.05,0.0025))]

    M_end = datetime.today().replace(minute=0,second=0,microsecond=0) # Major End dt
    M_start = M_end-timedelta(hours=md+btd+max(ranges)) # Major start dt (md+btd+max_range)
    bend = M_start+timedelta(hours=(btd+max(ranges))) # BT End
    bstart = M_start+timedelta(hours=max(ranges))  # BT Start

    
    p = get_prices(c,M_start,M_end)    
    inds = make_tg_inds(p,btd,bstart,bend,ranges,thresh_grads)
    opst = threshgrad_opstrat(p,c,inds,bstart,bend,btd,ranges,thresh_grads)
    data,posdf = populate_columns(p,inds,opst,eq,bend,M_end)

    return data


if __name__=="__main__":
    c = 'XLM'
    md = 2000
    btd = 500
    eq = 1000000
    data = main(c,md,btd,eq)

    

