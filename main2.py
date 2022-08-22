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
import pdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from signaller2 import *
import json
import urllib
from dash import dcc

dash_app = dash_app
dash_app.layout = app_layout()
app = dash_app.server

@dash_app.callback(
    [Output('iprices-data', 'data'),Output('posdf-data','data'),Output('outstrat-data','data'),Output('main-load','children')],
    Input('go-button', 'n_clicks'),
    [State('crypto-selector','value'),State('btd-input','value'),
    State('md-input','value'),State('mdd-input','value'),State('mt-input','value'),
    State('pracc-input','value')],
    prevent_initial_call=True
)
def get_data(n,c,btd,md,mdd,mt,pracc):
    data,opst,outstrat,posdf = main(c=c,md=md,btd=btd,mt=mt,pracc=pracc,mdd=mdd)
    # print(data,posdf)
    newout = {}
    # deal with json -- datetime issue
    for k,v in outstrat.items():
        newk = dt.datetime.strftime(k,"%Y-%m-%d %H:%M:%S")
        newout[newk] = v
        
    return data.to_json(date_format='iso', orient='split'),posdf.to_json(date_format='iso', orient='split'),json.dumps(newout,default=str),""

@dash_app.callback(
    Output('mygraph','figure'),
    [Input('iprices-data','data'),Input('posdf-data','data'),Input('outstrat-data','data')],
    prevent_initial_call=True
)
def grapher(data,posdf,outstrat):
    data = pd.read_json(data,orient='split')
    posdf = pd.read_json(posdf,orient='split')
    posdf['marker_size'] = [10 for _ in range(posdf.shape[0])]
    posdf = data[data['presignal']!=0]
    posdf = posdf.sort_index(ascending=True)
    posdf['colour'] = ['green' if x==1 else 'red' if x==-1 else None for x in list(posdf.presignal)]
    posdf['symbol'] = ['triangle-up' if x==1 else 'triangle-down' if x==-1 else None for x in list(posdf.presignal)]
    outstrat = json.loads(outstrat)
    newstrat = {}
    for k,v in outstrat.items():
        newk = dt.datetime.strptime(k,"%Y-%m-%d %H:%M:%S")
        newstrat[newk] = v
    pricetc = go.Scatter(x=data.index,y=data['Close'],line = Line({'color': 'rgb(0, 0, 128)', 'width': 1}),name='Price')
    sigtc = go.Scatter(
        x=posdf.index,
        y=posdf['Close'],
        mode='markers',
        marker = dict(size = 20, color = posdf['colour'], symbol = posdf['symbol'])
    )
    eqtc = go.Scatter(x=data.index,y=data['equity'],line = Line({'color': 'darkblue', 'width': 1}),name='equity')
    eqtc2 = go.Scatter(x=data.index,y=data['ema_eq'],line = Line({'color': 'red', 'width': 1}),name='EMA')
    eqtc3 = go.Scatter(x=data.index,y=data['sma_eq'],line = Line({'color': 'blue', 'width': 1}),name='SMA')
    eqtc4 = go.Scatter(x=data.index,y=data['mean_eq'],line = Line({'color': 'green', 'width': 1}),name="MEAN")
    eqtc5 = go.Scatter(x=data.index,y=data['rolling_max'],line = Line({'color': 'orange', 'width': 1}),name='Roll Max')
    eqtc6 = go.Scatter(x=data.index,y=data['rolling_min'],line = Line({'color': 'magenta', 'width': 1}),name='Roll Min')
    acctc = go.Scatter(x=data.index,y=data['accs'],line=Line({'color': 'red', 'width': 1}),name='Acc')
    gradtc = go.Scatter(x=data.index,y=data['grads'],line=Line({'color': 'blue', 'width': 1}),name='Grad')
    data1 = [pricetc,sigtc]
    data2 = [eqtc,eqtc2,eqtc3,eqtc4,eqtc5,eqtc6]
    data4 = [acctc,gradtc]
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
    ivls = list(newstrat.keys()) # these are intervals
    ivls.append(datetime.today().replace(minute=0,second=0,microsecond=0))
    colours = ['aqua', 'aquamarine', 'azure',
                'beige', 'bisque', 'black', 'blanchedalmond', 'blue',
                'blueviolet', 'brown', 'burlywood', 'cadetblue',
                'chartreuse', 'chocolate', 'coral', 'cornflowerblue',
                'cornsilk', 'crimson', 'cyan', 'darkblue', 'darkcyan',
                'darkgoldenrod', 'darkgray', 'darkgrey', 'darkgreen',
                'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange',
                'darkorchid', 'darkred', 'darksalmon', 'darkseagreen',
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
    # breakpoint()
    for i in range(1,len(ivls)):
        try:
            fig.add_vrect(
                x0=ivls[i-1].isoformat(sep=" "),
                x1=ivls[i].isoformat(sep=" "),
                annotation_text='/'.join([str(newstrat[ivls[i-1]]['win']),str(newstrat[ivls[i-1]]['deg'])]),
                annotation_position='top left',
                fillcolor=colours[i-1],
                opacity=0.1,
                line_width=0
            )
        except IndexError:
            breakpoint()
    fig.update_layout(
        height=1000,
        width=1500,
        xaxis_showticklabels=True,
        xaxis2_showticklabels=True,
        xaxis3_showticklabels=True,
        hovermode='x unified'
        )
    return fig

@dash_app.callback(
    Output('dl-df','data'),
    [Input('downlink','n_clicks'),Input('iprices-data', 'data')],
    prevent_initial_call=True
)
def downloader(n_clicks,data):
    data = pd.read_json(data,orient='split')
    return dcc.send_data_frame(data.to_csv,f'price_{datetime.today().replace(second=0,microsecond=0).isoformat(sep="T")}.csv')

@dash_app.callback(
    Output('posdf-dl-df','data'),
    [Input('posdf-downlink','n_clicks'),Input('posdf-data', 'data')],
    prevent_initial_call=True
)
def downloader2(n_clicks,data):
    data = pd.read_json(data,orient='split')
    return dcc.send_data_frame(data.to_csv,f'posdf_{datetime.today().replace(second=0,microsecond=0).isoformat(sep="T")}.csv')

if __name__=="__main__":
    dash_app.run_server(host='0.0.0.0',threaded=True, debug=True, port=7080)
