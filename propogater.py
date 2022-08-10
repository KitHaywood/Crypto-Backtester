#!/usr/bin/python3
from doctest import DocFileTest
from multiprocessing.reduction import DupFd
from re import M
from utils import *
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
from sqlalchemy import Table,MetaData,Column,String, Integer, Float,DateTime,ARRAY,NUMERIC,TEXT
import sys
import pdb
import pandas as pd
from datetime import datetime,timedelta
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.graph_objs.scatter import Line


def get_all_prices(crypto,start,end):
    if crypto=='BTC':
        res = con.execute(f"""
        SELECT DISTINCT * from "test_price_BTC2" WHERE datetimes>='{start}' AND datetimes<='{end}' ORDER BY datetimes DESC;
        """)
    else:
        res = con.execute(f"""
        SELECT DISTINCT * from "test_price_{crypto}" WHERE datetimes>='{start}' AND datetimes<='{end}' ORDER BY datetimes DESC;
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def get_all_inidicators(crypto,start,end):
    if crypto=='BTC':
        res = con.execute(f"""
        SELECT DISTINCT accs[1],grads[1],mdates[1],win,deg,start,"stop" from "acc_grad_test_btc_3" WHERE "stop">='{start}' AND "stop"<='{end}' ORDER BY "stop" DESC; 
        """)
    else:
        res = con.execute(f"""
        SELECT DISTINCT accs[1],grads[1],mdates[1],win,deg,start,"stop" from "test_accgrad_{crypto}" WHERE "stop">='{start}' AND "stop"<='{end}' ORDER BY "stop" DESC; 
        """)  
    df = pd.DataFrame.from_dict(res.mappings().all())
    df = df.astype({'accs':float,'grads':float})
    indics = {}
    wins = list(set(list(df['win'])))
    degs = list(set(list(df['deg'])))
    combs = [(x,y) for x in wins for y in degs]

    for w in wins:
        indics[w] = {}
        for d in degs:
            indics[w][d] = None

    for x,y in combs:
        indics[x][y] = df[(df['win']==x) & (df['deg']==y)].sort_values('stop',ascending=False).set_index('stop',drop=False)

    return indics,wins,degs

def indicator(values):
    return values

def get_coefs_at(win,deg,crypto,end,start):
    if crypto=='BTC':
        res = con.execute(f"""
        SELECT * FROM "testing_coef_BTC5" WHERE "window"={win} AND deg={deg} AND "end">='{start}' AND "end"<='{end}';
        """)
    else:
        res = con.execute(f"""
        SELECT * FROM "test_coef_{crypto}" WHERE "window"={win} AND deg={deg} AND "end">='{start}' AND "end"<='{end}';
        """)    
    df = pd.DataFrame.from_dict(res.mappings().all())
    df['coefs'] = df['coefs'].apply(lambda x: [float(y) for y in x.split('{')[1].split('}')[0].split(',')])
    return df


def get_initial_opter_strat(indics,prices,wins,degs,istart,iend):
    prices = prices.set_index('datetimes',drop=False)[istart:iend]
    pricedata = prices.rename(columns={
    "low":"Low",
    "high":"High",
    "close":"Close",
    "open":"Open",
    "datetimes":"datetime"
    }).set_index("datetime")
    for k,v in indics.items():
        for x,y in v.items():
            indics[k][x] = y[istart:iend].drop_duplicates(subset=['start','stop','win','deg'])

    class FourierTimStandard(Strategy):
        """
        Strategy Class - Value of Derivatives 1 & 2 vs 0

        Optimal Strat Shape - [w , d]        
        """
        allindics = indics
        wind = 800
        deg = 4

        def init(self):
            self.grad = self.I(
                    indicator, 
                    self.allindics[self.wind][self.deg].grads
                    )
            self.acc = self.I(
                indicator,
                self.allindics[self.wind][self.deg].accs
                ) 
            self.zeros = self.I(
                indicator,
                np.zeros(len(self.data.Close))
                )

        def next(self):
            if crossover(self.grad,self.zeros) & all(self.acc > 0): 
                self.position.close()
                self.buy()

            elif crossover(self.zeros, self.grad) & all(self.acc < 0): 
                self.position.close()
                self.sell()

    bt_std = Backtest(
            pricedata,
            FourierTimStandard,
            cash=1_000_000,
            commission=0.002
            )
    def maximiser(series):
        """takes series result of bt and returns a 
        float which maximises return and minimises num of trades"""
        return series['Equity Final [$]'] if 0 <= series['# Trades'] <= 7 else 0
    
    btresult = {}
    btresult['bt_std'] = bt_std.optimize(
            wind=wins,
            deg=degs,
            maximize=maximiser,
            method="grid",
            constraint=lambda param: param
        )
    opstrat = {
        "win":btresult['bt_std']._strategy.wind,
        "deg":btresult['bt_std']._strategy.deg
    }
    return btresult,opstrat

def initial_evaluator(crypto,prices,iopstr,end,md):
    origeq = 100000
    if crypto=='BTC':
        res = con.execute(f"""
        SELECT DISTINCT ON (accs,grads,start,"stop") accs[1],grads[1],start,"stop" FROM "acc_grad_test_btc_3" WHERE deg={iopstr['deg']} AND "win"={iopstr['win']} AND "stop">='{(end-timedelta(hours=md)).isoformat(sep=" ")}' ORDER BY "stop" DESC;
        """)
    else:
        res = con.execute(f"""
        SELECT DISTINCT ON (accs,grads,start,"stop") accs[1],grads[1],start,"stop" FROM "test_accgrad_{crypto}" WHERE deg={iopstr['deg']} AND "win"={iopstr['win']} AND "stop">='{(end-timedelta(hours=md)).isoformat(sep=" ")}' ORDER BY "stop" DESC;
        """)
    df = pd.DataFrame.from_dict(res.mappings().all()) # accgrad data
    df = df.astype({'accs':float,'grads':float})
    df = df.set_index("stop",drop=False).sort_index(ascending=True)

    # Signals & Equity from initial bt optimisation

    df['signal'] = [1 if (df.iloc[x]['accs']>0 and df.iloc[x-1]['grads']<0 and df.iloc[x]['grads']>0)
                    else -1 if (df.iloc[x]['accs']<0 and df.iloc[x-1]['grads']>0 and df.iloc[x]['grads']<0)
                    else 0 for x in range(df.shape[0])]
    
    pos = df[df['signal']!=0]
    posdf = pd.DataFrame()
    posdf = posdf.append(pos[['signal','stop']])
    posdf = posdf.reset_index(drop=True)
    prices = prices.merge(
        posdf,
        how='left',
        left_on='datetimes',
        right_on='stop').set_index('datetimes',drop=False).sort_index(ascending=True)
    prices = prices.fillna(0)
    prices['signal'] = prices['signal'].replace(to_replace=0,method="ffill")
    prices['equity'] = [0 for _ in range(prices.shape[0])]
    prices['group'] = prices['signal'].diff().abs().cumsum().fillna(0).astype(int) + 1   
    all_coefs = get_coefs_at(
        iopstr['win'],
        iopstr['deg'],
        crypto,
        end.isoformat(sep=" "),
        (end-timedelta(hours=md)).isoformat(sep=" ")
        )
    all_coefs = all_coefs[['coefs','end']][~all_coefs['end'].duplicated()==True].sort_values('end')
    prices = prices.reset_index(drop=True)
    prices = prices.merge(all_coefs,how='left',left_on='datetimes',right_on='end')
    prices = prices.fillna(0)
    prices['model_price'] = [fourier(
        prices.iloc[x]['mdates'],
        *prices.iloc[x]['coefs']
        ) if isinstance(prices.iloc[x]['coefs'],list) else 0 for x in range(prices.shape[0])]
    prices = prices.set_index('datetimes',drop=False).sort_index(ascending=True)
    prices['sl'] = prices['close']
    iprices = prices.copy()
    iprices['pct_ch'] = iprices['close'].pct_change()
    newprices = iprices.drop(columns=['coefs'])
    newprices = newprices.drop_duplicates(subset=['close','datetimes'])
    final = pd.DataFrame().reindex_like(newprices)
    
    for i,x in newprices.iterrows():
        if i == min(newprices.index):
            x['equity'] = 100000
            final.loc[i] = x
        else:
            lasteq = final.loc[i-timedelta(hours=1)]['equity']
            if x['signal']==0:
                cureq = lasteq
            elif x['signal']==1:
                cureq = lasteq * (1 + x['pct_ch'])
            elif x['signal']==-1:
                cureq = lasteq * (1 + (x['pct_ch']*-1.0))
            x['equity'] = cureq 
            try:
                final.loc[i] = x
            except:
                print(cureq,i)
                pdb.set_trace()
            
    return iprices,df,final

def forward_evaluator(iprices):

    iprices['3_eq_pct_ch'] = iprices['equity'].pct_change(periods=3)
    iprices['eq_pct_ch'] = iprices['equity'].pct_change()
    iprices['sl_2'] = [0 for _ in range(iprices.shape[0])]
    iprices = iprices.fillna(0)
    final = pd.DataFrame().reindex_like(iprices)
    
    for i,x in iprices.iterrows():
        if i==min(iprices.index):
            x['sl_2'] = x['close']
            final.loc[i] = x
            
        elif x['signal']==0:
            x['sl_2'] = x['close']
            final.loc[i] = x
        if x['eq_pct_ch']<0.03 and x['signal']==1:
            x['sl_2'] = final.loc[i-timedelta(hours=1)]['sl_2']*(0.97)
            final.loc[i] = x 
        elif x['eq_pct_ch']<0.03 and x['signal']==-1:
            x['sl_2'] = final.loc[i-timedelta(hours=1)]['sl_2']*(1.03)
            final.loc[i] = x 
        elif (x['eq_pct_ch'] >= 0.04) and (x['model_price'] > x['close']) and x['signal']==1:
            x['sl_2'] = final.loc[i-timedelta(hours=1)]['sl_2']*(1.02)
            final.loc[i] = x 
        elif (x['eq_pct_ch'] >= 0.025) and (x['model_price'] < x['close']) and x['signal']==1:
            x['sl_2'] = final.loc[i-timedelta(hours=1)]['sl_2']*(1.025)
            final.loc[i] = x 
        elif (x['eq_pct_ch'] >= 0.04) and (x['model_price'] > x['close']) and x['signal']==-1:
            x['sl_2'] = final.loc[i-timedelta(hours=1)]['sl_2']*(0.98) # Need to change
            final.loc[i] = x 
        elif (x['eq_pct_ch'] >= 0.025) and (x['model_price'] > x['close']) and x['signal']==-1:
            x['sl_2'] = final.loc[i-timedelta(hours=1)]['sl_2']*(0.975) # Need to change
            final.loc[i] = x 
        else:
            final.loc[i] = x
            print(i)

    pdb.set_trace()    
    return iprices

def maingetter(crypto,md):
    btd = 200
    end = datetime.today().replace(minute=0,second=0,microsecond=0)
    start = end - timedelta(hours=md+btd)
    prices = get_all_prices(crypto,start,end)
    indics,wins,degs = get_all_inidicators(crypto,start,end)
    ibtres,iopstr = get_initial_opter_strat(
        indics,
        prices,
        wins,
        degs,
        (end-timedelta(hours=md)),
        (end-timedelta(hours=md+btd))
        )
    iprices,df,eqdf = initial_evaluator(crypto,prices,iopstr,end,md)
    # final = forward_evaluator(eqdf)
    
    return iprices,df,indics,iopstr,eqdf

def plot(crypto,data,df,indics,iopst,eqdf,md):
    
    df = df[df['signal']!=0]
    
    def get_full_indics(crypto,iopst,data):
        if crypto=='BTC':
            res = con.execute(f"""
            SELECT DISTINCT ON (win,deg,start,stop) accs[1],grads[1],stop FROM "acc_grad_test_btc_3" WHERE "win"={iopst['win']} AND deg={iopst['deg']} AND "stop">='{min(data.index)}' AND "stop"<='{max(data.index)}';                 
            """)
        else:
            res = con.execute(f"""
            SELECT DISTINCT ON (win,deg,start,stop) accs[1],grads[1],stop FROM "test_accgrad_{crypto}" WHERE "win"={iopst['win']} AND deg={iopst['deg']} AND "stop">='{min(data.index)}' AND "stop"<='{max(data.index)}';                 
            """)
        return pd.DataFrame.from_dict(res.mappings().all())
    
    accgrad = get_full_indics(crypto,iopst,data)
    pricetc = go.Scatter(x=data['datetimes'],y=data['close'],line = Line({'color': 'rgb(0, 0, 128)', 'width': 1}))
    eqtc = go.Scatter(x=eqdf.index,y=eqdf['equity'],line = Line({'color': 'rgb(0, 0, 128)', 'width': 1}))
    sigtc = go.Scatter(x=df.index,y=df['signal'])
    acctc = go.Scatter(x=accgrad['stop'],y=accgrad['accs'],line=Line({'color': 'red', 'width': 1}))
    gradtc = go.Scatter(x=accgrad['stop'],y=accgrad['grads'],line=Line({'color': 'blue', 'width': 1}))
    data1 = [pricetc]
    data2 = [eqtc]
    data3 = [sigtc]
    data4 = [acctc,gradtc]
    fig = make_subplots(rows=4, cols=1,shared_xaxes=True,subplot_titles=("Price","Equity","Signal",f"Indicator {iopstr['win']} & {iopstr['deg']}"))
    fig.add_traces(data1, rows=1, cols=1)
    fig.add_traces(data2, rows=2, cols=1)
    fig.add_traces(data3, rows=3, cols=1)
    fig.add_traces(data4,rows=4,cols=1)
    fig.update_layout(title_text=f'{c} - Out-of-Sample 1-Opter Backtest - depth {md} hrs')    
    fig.show()
    
    return fig

if __name__=="__main__":
    c = "BTC"
    d = 500
    data,df,indics,iopstr,eqdf = maingetter(c,d)
    fig = plot(c,data,df,indics,iopstr,eqdf,d)