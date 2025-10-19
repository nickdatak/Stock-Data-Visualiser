import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import yfinance as yf
import plotly.graph_objects as go

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("Interactive Stock Visualisation Dashboard", style={"textAlign": "center", "margin": "15px"}),
    html.Div([
        dcc.Input(
            id='stock-input',
            type='text',
            value='META',
            debounce=True,
            placeholder='Enter stock ticker...',
            className='stock-input'
        ),
        dcc.Dropdown(
            id='timeframe-dropdown',
            options=[
                {'label': '1 Month', 'value': '1mo'},
                {'label': '3 Months', 'value': '3mo'},
                {'label': '6 Months', 'value': '6mo'},
                {'label': '1 Year', 'value': '1y'},
                {'label': '5 Years', 'value': '5y'},
                {'label': 'Max', 'value': 'max'}
            ],
            value='1y',  # default value
            clearable=False,
            style={'width': '150px', 'margin': '5px', 'display': 'inline-block', 'margin-left':'0px', 'color':'black'}
        )
    ], className='input-container'),
    html.Div(id='company-info', className='company-info'),
    html.Div([
        html.Div(dcc.Graph(id='stock-chart', className='stock-chart'), className='graph-column'),
        html.Div(dcc.Graph(id='financials-chart', className='financials-chart'), className='graph-column')
    ], className='graphs-row'),
], className='app-container')


@app.callback(
    [Output('stock-chart', 'figure'),
     Output('company-info', 'children'),
     Output('financials-chart', 'figure')],
    [Input('stock-input', 'value'),
     Input('timeframe-dropdown', 'value')]
)
def update_output(ticker, timeframe):
    if not ticker:
        return go.Figure(), html.Div("Please enter a ticker symbol."), go.Figure()

    stock = yf.Ticker(ticker)
    hist = stock.history(period=timeframe)

    if hist.empty:
        return go.Figure(), html.Div(f"No data found for ticker '{ticker}'."), go.Figure()

    info = stock.info

    company_name = info.get('shortName', 'N/A')
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')
    pe_ratio = info.get('trailingPE', 'N/A')
    market_cap = info.get('marketCap', 'N/A')
    dividend_yield = info.get('dividendYield', 'N/A')

    company_info_layout = html.Div([
        html.H4(company_name),
        html.P(f"Sector: {sector}"),
        html.P(f"Industry: {industry}"),
        html.P(f"P/E Ratio: {pe_ratio}"),
        html.P(f"Market Cap: {market_cap:,} $"),
        html.P(f"Dividend Yield: {dividend_yield} %")
    ])

    income_stmt = getattr(stock, "income_stmt", None)
    if income_stmt is None or income_stmt.empty:
        financials_fig = go.Figure()
    else:
        revenue = income_stmt.loc['Total Revenue'] if 'Total Revenue' in income_stmt.index else None
        net_income = income_stmt.loc['Net Income'] if 'Net Income' in income_stmt.index else None

        periods = income_stmt.columns.strftime('%Y-%m-%d') if hasattr(income_stmt.columns, 'strftime') else income_stmt.columns

        financials_fig = go.Figure()
        if revenue is not None:
            financials_fig.add_trace(
                go.Bar(x=periods, y=revenue.values, name='Total Revenue'))
        if net_income is not None:
            financials_fig.add_trace(
                go.Bar(x=periods, y=net_income.values, name='Net Income'))

        financials_fig.update_layout(
            title=f'Financials for {ticker.upper()}',
            yaxis_title='USD',
            barmode='group'
        )

    hist['MA10'] = hist['Close'].rolling(window=10).mean()
    hist['MA50'] = hist['Close'].rolling(window=50).mean()
    hist['MA200'] = hist['Close'].rolling(window=200).mean()

    fig = go.Figure(data=[go.Candlestick(
        x=hist.index,
        open=hist['Open'],
        high=hist['High'],
        low=hist['Low'],
        close=hist['Close'],
        name=ticker.upper()
    )])

    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA10'], mode='lines', name='MA 10', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA50'], mode='lines', name='MA 50', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'], mode='lines', name='MA 200', line=dict(color='red')))

    fig.update_layout(title=f'Stock Price for {ticker.upper()} ({timeframe})', xaxis_rangeslider_visible=True)

    return fig, company_info_layout, financials_fig


if __name__ == '__main__':
    app.run(debug=True)
