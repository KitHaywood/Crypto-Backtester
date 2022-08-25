from dash.dependencies import Input, Output, State
from plotly.graph_objects import Scatter
import numpy as np
import plotly.express as px 
from apps.template2 import app_layout
import datetime as dt
from apps.app import dash_app
import pandas as pd
from utils import *
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from zero_sig import *
from tg_sig import *
from sma_sig import *
import json
from dash import dcc

dash_app = dash_app
dash_app.layout = app_layout()
app = dash_app.server

@dash_app.callback(
    [Output('0-iprices-data', 'data'),Output('0-posdf-data','data'),
     Output('0-outstrat-data','data'),Output('tg-iprices-data', 'data'),
     Output('tg-posdf-data','data'), Output('tg-outstrat-data','data'),
     Output('indix-iprices-data', 'data'), Output('indix-posdf-data','data'), 
     Output('indix-outstrat-data','data'),Output('main-load','children')],
    Input('go-button', 'n_clicks'),
    [State('crypto-selector','value'),State('btd-input','value'),
    State('md-input','value'),State('mdd-input','value'),State('mt-input','value'),
    State('pracc-input','value')],
    prevent_initial_call=True
)
def get_data(n,c,btd,md,mdd,mt,pracc):
    data0,opst,outstrat0,posdf0,ind = main(
        c=c,
        md=md,
        btd=btd,
        mt=mt,
        pracc=pracc,
        mdd=mdd
        )
    datatg,outstrattg,posdftg = tgmain(
        c=c,
        md=md,
        btd=btd,
        mdd=mdd
    )
    datai,opsti,outstrati,posdfi = indix_main(
        c=c,
        md=md,
        btd=btd,
        mt=mt,
        pracc=pracc,
        mdd=mdd,
        ind=ind
        )
    newout0 = {}
    newoutg = {}
    newouti = {}
    # deal with json -- datetime issue
    for k,v in outstrat0.items():
        newk = dt.datetime.strftime(k,"%Y-%m-%d %H:%M:%S")
        newout0[newk] = v
    for k,v in outstrattg.items():
        newk = dt.datetime.strftime(k,"%Y-%m-%d %H:%M:%S")
        newoutg[newk] = v
    for k,v in outstrati.items():
        newk = dt.datetime.strftime(k,"%Y-%m-%d %H:%M:%S")
        newouti[newk] = v
        
    # sort output formats into json    
    iprices0 = data0.to_json(date_format='iso', orient='split')
    posdf0 = posdf0.to_json(date_format='iso', orient='split')
    outstrat0 = json.dumps(newout0,default=str)
    ipricestg = datatg.to_json(date_format='iso', orient='split')
    posdftg = posdftg.to_json(date_format='iso', orient='split')
    outstrattg = json.dumps(newoutg,default=str)
    ipricesi = datai.to_json(date_format='iso', orient='split')
    posdfi = posdfi.to_json(date_format='iso', orient='split')
    outstrati = json.dumps(newouti,default=str)
    
    
    return iprices0,posdf0,outstrat0,ipricestg,posdftg,outstrattg,ipricesi,posdfi,outstrati,""



@dash_app.callback(
    [Output('mygraph1','figure'),Output('mygraph2','figure')],
    [Input('0-iprices-data','data'),Input('0-posdf-data','data'),Input('0-outstrat-data','data'),
    Input('tg-iprices-data','data'),Input('tg-posdf-data','data'),Input('tg-outstrat-data','data'),
    Input('indix-iprices-data','data'),Input('indix-posdf-data','data'),Input('indix-outstrat-data','data')],
    prevent_initial_call=True
)
def grapher(data0,posdf0,outstrat0,datatg,posdftg,outstratg,datai,posdfi,outstrati):
    
    data0 = pd.read_json(data0,orient='split')
    datatg = pd.read_json(datatg,orient='split')
    datai = pd.read_json(datai,orient='split')
    
    posdf0 = pd.read_json(posdf0,orient='split')
    posdftg = pd.read_json(posdftg,orient='split')
    posdfi = pd.read_json(posdfi,orient='split')
    
    posdf0['marker_size'] = [10 for _ in range(posdf0.shape[0])]
    
    posdf0 = data0[data0['presignal']!=0]
    posdf0 = posdf0.sort_index(ascending=True)
    posdf0['colour'] = ['green' if x==1 else 'red' if x==-1 else None for x in list(posdf0.presignal)]
    posdf0['symbol'] = ['triangle-up' if x==1 else 'triangle-down' if x==-1 else None for x in list(posdf0.presignal)]
    
    outstrat0 = json.loads(outstrat0)
    outstratg = json.loads(outstratg)
    outstrati = json.loads(outstrati)
    
    newstrat0 = {}
    newstratg = {}
    newstrati = {}
    
    for k,v in outstrat0.items():
        newk = dt.datetime.strptime(k,"%Y-%m-%d %H:%M:%S")
        newstrat0[newk] = v
    for k,v in outstratg.items():
        newk = dt.datetime.strptime(k,"%Y-%m-%d %H:%M:%S")
        newstratg[newk] = v
    for k,v in outstrati.items():
        newk = dt.datetime.strptime(k,"%Y-%m-%d %H:%M:%S")
        newstrati[newk] = v
    
    pricetc0 = go.Scatter(x=data0.index,y=data0['Close'],line = Line({'color': 'rgb(0, 0, 128)', 'width': 1}),name='Price')
    
    # breakpoint()
    
    if not all(posdf0['colour'].isna()):     
        sigtc0 = go.Scatter(
            x=posdf0.index,
            y=posdf0['Close'],
            mode='markers',
            marker = dict(size = 15, color = posdf0['colour'], symbol = posdf0['symbol'])
        )
    else:
        sigtc0 = go.Scatter()
    
    if not all(posdftg['colour'].isna()):
        sigtctg = go.Scatter(
            x=posdftg.index,
            y=posdftg['Close'],
            mode='markers',
            marker = dict(size = 15, color = posdftg['colour'], symbol = posdftg['symbol'])
        )
    else:
        sigtctg = go.Scatter()
        
    if not all(posdfi['colour'].isna()):
        sigtci = go.Scatter(
            x=posdfi.index,
            y=posdfi['Close'],
            mode='markers',
            marker = dict(size = 15, color = posdfi['colour'], symbol = posdfi['symbol'])
        )
    else:
        sigtci = go.Scatter()
        
    eqtc0 = go.Scatter(x=data0.index,y=data0['equity'],line = Line({'color': 'darkblue', 'width': 1}),name='0-equity')
    eqtctg = go.Scatter(x=datatg.index,y=datatg['equity'],line = Line({'color': 'darkgreen', 'width': 1}),name='tg-equity')
    eqtci = go.Scatter(x=datai.index,y=datai['equity'],line = Line({'color': 'orange', 'width': 1}),name='sma-equity')
    eqtc00 = go.Scatter(x=data0.index,y=data0['mean_eq'],line = Line({'color': 'purple', 'width': 1}),name="0-MEAN")
    eqtctgm = go.Scatter(x=datatg.index,y=datatg['mean_eq'],line = Line({'color': 'red', 'width': 1}),name="tg-MEAN")
    eqtcti = go.Scatter(x=datatg.index,y=datatg['mean_eq'],line = Line({'color': 'gold', 'width': 1}),name="tg-MEAN")
    acctc0 = go.Scatter(x=data0.index,y=data0['accs'],line=Line({'color': 'red', 'width': 1}),name='Acc')
    gradtc0 = go.Scatter(x=data0.index,y=data0['grads'],line=Line({'color': 'blue', 'width': 1}),name='Grad')
    acctc1 = go.Scatter(x=datai.index,y=datai['accs'],line=Line({'color': 'red', 'width': 1}),name='Acc')
    gradtc2 = go.Scatter(x=datai.index,y=datai['grads'],line=Line({'color': 'blue', 'width': 1}),name='Grad')
    
    data1 = [pricetc0,sigtc0,sigtctg,sigtci]
    data2 = [eqtc0,eqtctg,eqtc00,eqtctgm,eqtci,eqtcti]
    data4 = [acctc0,gradtc0]
    
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Price + Signal","Equity + Measures",f"Indicators"),
        vertical_spacing=0.1
        )
    fig.add_traces(data1, rows=1, cols=1)
    fig.add_traces(data2, rows=2, cols=1)
    fig.add_traces(data4,rows=3,cols=1)
    
    colours = ['aqua','darkred','aquamarine', 'azure',
                'beige', 'bisque', 'black', 'blanchedalmond', 'blue',
                'blueviolet', 'brown', 'burlywood', 'cadetblue',
                'chartreuse', 'chocolate', 'coral', 'cornflowerblue',
                'cornsilk', 'crimson', 'cyan', 'darkblue', 'darkcyan',
                'darkgoldenrod', 'darkgray', 'darkgrey', 'darkgreen',
                'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange',
                'darkorchid', 'darksalmon', 'darkseagreen',
                'darkslateblue', 'darkslategray', 'darkslategrey',
                'darkturquoise', 'darkviolet', 'deeppink', 'deepskyblue',
                'dimgray', 'dimgrey', 'dodgerblue', 'firebrick',
                'floralwhite', 'forestgreen', 'fuchsia', 'gainsboro',
                'ghostwhite', 'gold', 'goldenrod', 'gray', 'grey', 'green',
                'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo',
                'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen',
                'lemonchiffon', 'lightblue', 'lightcoral', 'lightcyan',
                'lightgoldenrodyellow', 'lightgray', 'lightgrey',
                'lightgreen', 'lightpink', 'lightsalmon', 'lightseagreen',
                'lightskyblue', 'lightslategray', 'lightslategrey',
                'lightsteelblue','lightyellow', 'lime', 'limegreen',
                'yellowgreen']
    ivls0 = list(newstrat0.keys()) # these are intervals
    ivls0.append(datetime.today().replace(minute=0,second=0,microsecond=0))
    # breakpoint()
    for i in range(1,len(ivls0)):
        try:
            fig.add_vrect(
                x0=ivls0[i-1].isoformat(sep=" "),
                x1=ivls0[i].isoformat(sep=" "),
                annotation_text='/'.join([str(newstrat0[ivls0[i-1]]['win']),str(newstrat0[ivls0[i-1]]['deg'])]),
                annotation_position='top left',
                fillcolor=colours[::-1][i-1],
                opacity=0.1,
                line_width=0
            )
        except IndexError:
            pass
    fig.update_layout(
        height=1000,
        width=1500,
        xaxis_showticklabels=True,
        xaxis2_showticklabels=True,
        xaxis3_showticklabels=True,
        hovermode='x unified'
        )
    
    ivlsi = list(newstrati.keys())
    ivlsi.append(datetime.today().replace(minute=0,second=0,microsecond=0))
    fig2 = make_subplots(
        rows=1,
        cols=1,
        subplot_titles=("INDIX Indicators"),
        vertical_spacing=0.1
        )
    idata = [acctc1,gradtc2]
    fig2.add_traces(idata,rows=1, cols=1)

    
    for i in range(1,len(ivlsi)):
        try:
            fig2.add_vrect(
                x0=ivlsi[i-1].isoformat(sep=" "),
                x1=ivlsi[i].isoformat(sep=" "),
                annotation_text='-'.join([
                    '/'.join(
                        [str(newstrati[ivlsi[i-1]]['win1']),str(newstrati[ivlsi[i-1]]['deg1'])]
                        ),
                    '/'.join(
                        [str(newstrati[ivlsi[i-1]]['win2']),str(newstrati[ivlsi[i-1]]['deg2'])]
                        )
                    ]),
                annotation_position='top left',
                fillcolor=colours[i-1],
                opacity=0.1,
                line_width=0
            )
        except IndexError:
            pass
    fig2.update_layout(        
        height=400,
        width=1400,
        xaxis_showticklabels=True,
        )
    return fig,fig2

if __name__=="__main__":
    dash_app.run_server(host='0.0.0.0',threaded=True, debug=True, port=7080)
