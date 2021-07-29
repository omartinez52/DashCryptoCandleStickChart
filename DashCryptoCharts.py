import dash
import dash_core_components as dcc
import dash_html_components as html
import requests
import json
import pandas as pd
import datetime as dt
import plotly.graph_objects as go
from dash.dependencies import Input, Output

"""
    CryptoChart Class:
        - Objects created from class will store information for data frame.
        - Constructor():
            - Instantiates object instances with data that will be requested.
        - fillDataFrame():
            - Makes a call to Binance API to gather data from Bitcoin by default.
            - Creates Data Frame from data received from Binance.
            - Makes adjustments to Data Frame.
        - updateDataFrame(symbol):
            - Makes an update to the symbol passed in parameters.
            - Makes call to fillDataFrame() to create a data frame.
        - movingAverages(range):
            - Generate data using moving averages for plotting given range.
"""
class CryptoChart:
    def __init__(self):
        self.indicators = ["21MA", '50MA', '100MA', '200MA', "Bollinger Bands"]
        # Parameters for data that will be requested from URL. Symbol, interval, start time,
        # end time and limit of items.
        self.url = "https://api.binance.com/api/v3/klines"
        self.symbol = ''
        self.interval = '1d'
        self.startTime = str(int((dt.datetime.now() - dt.timedelta(days=1000)).timestamp()) * 1000)
        self.endTime = str(int(dt.datetime.now().timestamp()) * 1000)
        self.limit = '1000'
        self.req_params = ''
        self.fillDataFrame('BTCUSDT')

    def fillDataFrame(self,symbol):
        oldSymbol = self.symbol
        try:
            self.symbol = symbol
            # Creating dictionary for parameters that will be requested from API.
            self.req_params = {'symbol': self.symbol,
                               'interval': self.interval,
                               'startTime': self.startTime,
                               'endTime': self.endTime,
                               'limit': self.limit
                               }
            # Making request for data from Binance API. Passing generated parameters of data to receive.
            # Storing data into a data frame.
            self.df = pd.DataFrame(json.loads(requests.get(self.url, params=self.req_params).text))
            # Stripping first 6 columns from data frame. Not all data from Binance is required.
            self.df = self.df.iloc[:, 0:6]
            # Renaming columns to better access data.
            self.df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            self.df.index = [dt.date.fromtimestamp(x/1000) for x in self.df.Date]
            self.movingAverages()
        except ValueError:
            # symbol changed back to previous symbol
            self.symbol = oldSymbol
    def movingAverages(self):
        """
            Calculating 21 day, 50 day, 100 day, 200 day moving averages using closing price from data frame.
        """
        self.df['21MA'] = self.df['Close'].astype('float').rolling(window=21).mean()
        self.df['50MA'] = self.df['Close'].astype('float').rolling(window=50).mean()
        self.df['100MA'] = self.df['Close'].astype('float').rolling(window=100).mean()
        self.df['200MA'] = self.df['Close'].astype('float').rolling(window=200).mean()
        """
            Gathering data to create bollinger bands
            Formula:BOLU - Upper Bollinger Band = MA(TP, n) + m * std[TP, n]
                    BOLD - Lower Bollinger Band = MA(TP, n) - m * std[TP, n]
                    MA = Moving Average
                    TP - Typical Price = (High + Low + Close) / 3
                    n = Number of days in smoothing period (typically 20)
                    m = Number of standard deviations (typically 2)
                    std[TP,n] = Standard deviation over last n periods of TP
        """
        self.df['TP'] = (self.df['Close'].astype('float') + self.df['High'].astype('float') + self.df['Low'].astype('float')) / 3.0
        self.df['STD'] = self.df['TP'].astype('float').rolling(window=20).std(skipna=True)
        self.df['BOLU'] = self.df['TP'].astype('float').rolling(window=20).mean() + 2 * (self.df['STD'])
        self.df['BOLD'] = self.df['TP'].astype('float').rolling(window=20).mean() - 2 * (self.df['STD'])

# Crypto Chart Object Created
Chart = CryptoChart()
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.H2("Crypto Currency Daily Candle Stick Chart",
            id='main-title',
            style={'text-align':'center'}
            ),
    html.Div([
              html.Div([html.Div("Enter token to pair w/ USDT:"),
                        dcc.Input(id="crypto-token",
                                 type="text",
                                 placeholder="BTCUSDT",
                                 debounce=True,
                                 ),
                        ],style={'width' : '30%',
                                 'display' : 'inline-block',
                                 'text-align' : 'center',
                                 "position": "absolute",
                                 "top": "12%",
                                 "left": "-4%",
                                 },
                       ),
              html.Div([html.Div("Indicator List"),
                        dcc.Dropdown(id='indicator-list',
                                     multi=True,
                                     options=[{'label':x, 'value':x} for x in Chart.indicators],
                                     value=[]
                                     ),
                        ],style={'width' : '20%',
                                 'display' : 'inline-block',
                                 'text-align' : 'center',
                                 "position": "absolute",
                                 "top": "12%",
                                 "left": "70%",
                                 },
                       ),
              ],
    ),
    dcc.Graph(
        id='graph',
        style={'width': '180vh',
               'height': '75vh',
               "display": "inline-block",
               "border": "1px #5c5c5c solid",
               "overflow": "hidden",
               "position": "absolute",
               "top": "60%",
               "left": "50%",
               "transform": "translate(-50%, -50%)",
               },
    ),
])


@app.callback(
    Output(component_id='graph',component_property='figure'),
    Input(component_id='crypto-token',component_property='value'),
    Input(component_id='indicator-list', component_property='value'),

)
def displayCandleStick(value,list):
    # If user inputs new symbol to chart, update data frame
    if value != None:
        Chart.fillDataFrame(value.upper()+'USDT')
    fig = go.Figure(go.Candlestick(x=Chart.df['Date'],
                                   open=Chart.df['Open'],
                                   close=Chart.df['Close'],
                                   high=Chart.df['High'],
                                   low=Chart.df['Low'],
                                   showlegend=False,
                                   ),
                    )
    if len(list) > 0:
        for i in list:
            if i == 'Bollinger Bands':
                fig.add_trace(go.Scatter(x=Chart.df['Date'],
                                         y=Chart.df['BOLU'].astype('float'),
                                         mode='lines',
                                         opacity=0.1,
                                         name="Upper Bollinger Band",
                                         line=dict(color="rgba(186, 255, 235, 0.1)"),
                                         showlegend=False,
                                         ),
                              )
                fig.add_trace(go.Scatter(x=Chart.df['Date'],
                                         y=Chart.df['BOLD'].astype('float'),
                                         mode='lines',
                                         opacity=0.1,
                                         name='Lower Bollinger Band',
                                         fill='tonexty',
                                         line=dict(color="rgba(186, 255, 235, 0.1)"),
                                         showlegend=False,
                                         ),
                              )
            else:
                fig.add_trace(go.Scatter(x=Chart.df['Date'],
                                         y=Chart.df[i].astype('float'),
                                         mode='lines',
                                         opacity=0.5,
                                         name=i,
                                         ),
                              )
    fig.update_layout(legend=dict(orientation='h',
                                 yanchor='bottom',
                                 y=1.02,
                                 xanchor='right',
                                 x=.94
                                 )
                     )
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)