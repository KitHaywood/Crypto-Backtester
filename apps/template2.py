from dash import dcc 
from dash import html
from datetime import datetime


def app_layout():
    return html.Div(style = {
        'backgroundColor':'white'
    },children=[
        dcc.Store(id='iprices-data'),
        dcc.Store(id='posdf-data'),
        dcc.Store(id='outstrat-data'),
        html.H1(children='Zero-X Model',
        style={'textAlign':'center','color':'black'}),
        html.Div(className='row',children=[
            
            html.Div(className='six columns', children=[
                html.Label(['Select Instrument'],style={'text-align':'left','color':'black'}),
                    dcc.Dropdown(
                    id='crypto-selector',
                    options=['REP','XLM','BTC'],
                    value='REP'),
                html.Label(['Select In-Samp Backtest Depth'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='btd-input',
                    type='number',
                    placeholder="input an integer",
                    value=200)]),
            html.Div(className='six columns', children=[
                html.Label(['Select Model Duration (hrs)'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='md-input',
                    type='number',
                    placeholder="input an integer",
                    value=1000),
                html.Label(['Select Area'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='mdd-input',
                    value=250000,
                    type='number',
                    placeholder="input [0.0 -- 1.0]")
        ]),
            html.Div(className='six columns',children=[
                html.Label(['Select In-Samp BT Max-Trades'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='mt-input',
                    type='number',
                    placeholder="input an integer",
                    value=10),
                html.Label(['Select Consecutive Chop Depth'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='cdd-input',
                    type='number',
                    placeholder="input an integer")
                ]),
            html.Div(className='six columns',children=[
                html.Label(['Select Preceding Accs'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='pracc-input',
                    type='number',
                    placeholder="input an integer",
                    value=0),
                html.Label(['Select Post Chop wait length'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='pcw-input',
                    type='number',
                    placeholder="input an integer"),
                               
            ])
            ],style={'display':'flex','margin':'15px'}),
        html.Div(
             html.Button(id='go-button',n_clicks=0,children='Run Model')
        ),
        html.Div(
            className='six columns',
            children=[
            html.Div(),
            dcc.Loading(id='main-load',children=html.Div()),
            html.Div()
                ]
            ),
        html.Div(children=dcc.Graph(id='mygraph')),
        html.Button("Dump Price-Equity CSV",id='downlink'),
        html.Button("Dump Posdf CSV",id='posdf-downlink'),
        dcc.Download(id='dl-df'),
        dcc.Download(id='posdf-dl-df')
    ]
    )
