from time import time
from utils import *
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import pandas as pd
from datetime import datetime,timedelta
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.graph_objs.scatter import Line


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
    _f['rolling_max'] = [max(_f['equity'].loc[:i]) for i in list(_f.index)]
    _f['rolling_min'] = [min(_f['equity'].loc[:i]) for i in list(_f.index)]
    _f['mean_eq'] = [_f['equity'].loc[:i].mean() for i in list(_f.index)]
    _f['sma_eq'] = [_f['equity'].loc[:i].rolling(20).mean()[-1] for i in list(_f.index)]
    _f['ema_eq'] = [_f['equity'].loc[:i].ewm(span=15,adjust=False).mean()[-1] for i in list(_f.index)]
    return _f


def threshgrad_opstrat(p,inds,bstart,bend,btd,ranges,thresh_grads,eq):
    
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
            cash=eq,
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

    opst = {
        "rng":eval(str(btresult['bt_std']._strategy).split('(')[1].split(',')[0].split('=')[1]),
        "tg":btresult['bt_std']._strategy.tg
    }
    return opst

def populate_columns(p,inds,opst,eq,start,end):
    
    wp = p[start:end]
    tg = opst['tg']
    rng = opst['rng']
    data = wp.copy()
    data['tg'] = [tg for _ in range(wp.shape[0])]
    data['rng'] = [rng for _ in range(wp.shape[0])]
    data['ind'] = p['Close'].pct_change(periods=rng)[start:end]
    data['test_presignal'] = [None for _ in range(data.shape[0])]
    
    for i,x in data.iterrows():
        if i == min(data.index):
            x['test_presignal']=0
            data.loc[i] = x
        else:
            if abs(data.loc[i]['ind']) < tg:
                x['test_presignal'] = 0
            elif abs(data.loc[i]['ind']) > tg and data.loc[i]['ind']>0:
                x['test_presignal']=1
                data.loc[i] = x
            elif abs(data.loc[i]['ind']) > tg and data.loc[i]['ind']<0:
                x['test_presignal']=-1
                data.loc[i] = x
            else:
                print(i,x)

    data['presignal'] = [0 if x==0 else 1 if (data.iloc[x]['ind']>0 and abs((data.iloc[x]['ind']))>tg)
                         else -1 if  (data.iloc[x]['ind']<0 and abs((data.iloc[x]['ind']))>tg)
                         else 0 for x in range(data.shape[0])]
    
    
    posdf = data[data['presignal']!=0]
    data['signal'] = data['presignal'].replace(to_replace=0,method="ffill")
    data['test_signal'] = data['test_presignal'].replace(to_replace=0,method="ffill")
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


def tgmain(c,md,btd,mdd):

    eq = 100000
    ranges = list(range(100,400,20)) # make argparse
    thresh_grads = [round(x,4) for x in list(np.arange(0.01,0.05,0.0025))]

    M_end = datetime.today().replace(minute=0,second=0,microsecond=0) # Major End dt
    M_start = M_end-timedelta(hours=md+btd+max(ranges)) # Major start dt (md+btd+max_range)
    iend = M_start+timedelta(hours=(btd+max(ranges))) # BT End
    istart = M_start+timedelta(hours=max(ranges))  # BT Start
    
    p = get_prices(c,M_start,M_end)    
    inds = make_tg_inds(p,btd,istart,iend,ranges,thresh_grads)
    opst = threshgrad_opstrat(p,inds,istart,iend,btd,ranges,thresh_grads,eq)
    data,posdf = populate_columns(p,inds,opst,eq,iend,M_end)

    bigpos = pd.DataFrame()
    bigpos = pd.concat([bigpos,posdf])
    f = pd.DataFrame().reindex_like(data)
    outstrat = {}
    outstrat[iend] = opst
    total_area = 0
    maxeq = 0
    i = min(f.index)
    
    
    while i != max(f.index): 
        maxeq = max(maxeq,data.loc[i]['equity'])
        total_area = total_area + (maxeq - data.loc[i]['equity'])        
        if maxeq==data.loc[i]['rolling_min']==data.loc[i]['equity']:
            f.loc[i] = data.loc[i]
       
        if total_area > mdd:
          
            opst = threshgrad_opstrat(
                p,
                inds,
                i-timedelta(hours=btd),
                i,
                btd,
                ranges,
                thresh_grads,
                data.loc[i]['equity']
                )
            outstrat[i] = opst
            data,posdf = populate_columns(
                p,
                inds,
                opst,
                data.loc[i]['equity'],
                i,
                M_end,
                )
        
            bigpos = pd.concat([bigpos,posdf])
            f.loc[i:] = data.loc[i:]

            total_area = 0 # reset area to 0
            maxeq = 0

        else:
            f.loc[i] = data.loc[i]
            
        i = i+timedelta(hours=1)
        
    f = add_metrics(f)

    bigpos['colour'] = ['blue' if x==1 else 'yellow' if x==-1 else None for x in list(bigpos.presignal)]
    bigpos['symbol'] = ['triangle-up' if x==1 else 'triangle-down' if x==-1 else None for x in list(bigpos.presignal)]  
      
    cat = pd.Categorial(list(f.signal),cateogies=[-1,0,1])
    f['truesig'] = pd.factorize(cat)[0]
    
    return f,outstrat,bigpos


if __name__=="__main__":
    c = 'XLM'
    md = 2000
    btd = 200
    mdd = 500000
    data = tgmain(c,md,btd,mdd)

    

