import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# Initialize the Dash app with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# --- App Layout ---
app.layout = html.Div([
    # Header
    html.H1("Interactive Stock Visualization Dashboard", className='app-header'),

    # Input controls container
    html.Div([
        dcc.Input(
            id='stock-input',
            type='text',
            value='AAPL',  # Default value
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
            value='1y',
            clearable=False,
            className='timeframe-dropdown'
        )
    ], className='input-container'),

    # Main content area with two columns
    html.Div([
        # Left column for charts
        html.Div([
            dcc.Graph(id='stock-chart', className='chart'),
            dcc.Graph(id='financials-chart', className='chart')
        ], className='main-column'),

        # Right column for company info and dividends
        html.Div([
            html.Div(id='company-info', className='info-panel'),
            html.Div(id='dividend-table', className='info-panel')
        ], className='side-column')

    ], className='content-row'),

], className='app-container')


# --- Callback Function ---
@app.callback(
    [Output('stock-chart', 'figure'),
     Output('company-info', 'children'),
     Output('financials-chart', 'figure'),
     Output('dividend-table', 'children')],
    [Input('stock-input', 'value'),
     Input('timeframe-dropdown', 'value')]
)
def update_dashboard(ticker, timeframe):
    """
    This function updates the entire dashboard based on the user's selected
    stock ticker and timeframe.
    """
    # Return empty components if no ticker is provided
    if not ticker:
        empty_fig = go.Figure().update_layout(
            paper_bgcolor="#2E2E2E", plot_bgcolor="#2E2E2E",
            font={'color': 'white'},
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
        )
        no_ticker_msg = html.Div([
            html.H4("Enter a Ticker Symbol", style={'color': 'white'}),
            html.P("Please enter a stock ticker symbol in the box above to see the data.", style={'color': '#ccc'})
        ])
        return empty_fig, no_ticker_msg, empty_fig, ""

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=timeframe)
        info = stock.info

        # Handle cases where the ticker is invalid or has no data
        if hist.empty or not info.get('symbol'):
            raise ValueError(f"No data found for ticker '{ticker}'. It may be an invalid symbol.")

    except Exception as e:
        error_fig = go.Figure().update_layout(
            paper_bgcolor="#2E2E2E", plot_bgcolor="#2E2E2E",
            font={'color': 'white'},
            annotations=[dict(text=f"Could not load data for '{ticker}'", showarrow=False, font=dict(size=16))]
        )
        error_msg = html.Div([
            html.H4(f"Error loading data for {ticker.upper()}", style={'color': '#ff5e57'}),
            html.P(str(e), style={'color': '#ccc'})
        ])
        return error_fig, error_msg, error_fig, ""

    # --- 1. Stock Price Chart ---
    hist['MA10'] = hist['Close'].rolling(window=10).mean()
    hist['MA50'] = hist['Close'].rolling(window=50).mean()
    hist['MA200'] = hist['Close'].rolling(window=200).mean()

    stock_fig = go.Figure(data=[go.Candlestick(
        x=hist.index,
        open=hist['Open'],
        high=hist['High'],
        low=hist['Low'],
        close=hist['Close'],
        name='Price'
    )])
    stock_fig.add_trace(
        go.Scatter(x=hist.index, y=hist['MA10'], mode='lines', name='10-Day MA', line=dict(color='orange', width=1)))
    stock_fig.add_trace(
        go.Scatter(x=hist.index, y=hist['MA50'], mode='lines', name='50-Day MA', line=dict(color='cyan', width=1)))
    stock_fig.add_trace(
        go.Scatter(x=hist.index, y=hist['MA200'], mode='lines', name='200-Day MA', line=dict(color='magenta', width=1)))

    stock_fig.update_layout(
        title=f'Stock Price for {ticker.upper()}',
        yaxis_title='Price (USD)',
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template='plotly_dark'
    )

    # --- 2. Company Info Panel ---
    company_info_layout = html.Div([
        html.H4(info.get('shortName', 'N/A')),
        html.P(f"Sector: {info.get('sector', 'N/A')}", className='info-item'),
        html.P(f"Industry: {info.get('industry', 'N/A')}", className='info-item'),
        html.P(f"P/E Ratio: {info.get('trailingPE', 'N/A'):.2f}" if info.get('trailingPE') else "P/E Ratio: N/A",
               className='info-item'),
        html.P(f"Market Cap: ${info.get('marketCap', 0):,}", className='info-item'),
        html.P(f"Dividend Yield: {info.get('dividendYield', 0) * 100:.2f}%" if info.get(
            'dividendYield') else "Dividend Yield: N/A", className='info-item'),
        html.P(info.get('longBusinessSummary', 'No summary available.'), className='business-summary')
    ])

    # --- 3. Financials Chart ---
    financials_fig = go.Figure()
    try:
        # Use .financials which is often more reliable for annual data
        income_stmt = stock.financials
        if not income_stmt.empty and 'Total Revenue' in income_stmt.index and 'Net Income' in income_stmt.index:
            # Reverse the columns to have the oldest year first
            income_stmt = income_stmt.iloc[:, ::-1]

            revenue = income_stmt.loc['Total Revenue']
            net_income = income_stmt.loc['Net Income']
            periods = income_stmt.columns.strftime('%Y')

            financials_fig.add_trace(go.Bar(x=periods, y=revenue.values, name='Total Revenue'))
            financials_fig.add_trace(go.Bar(x=periods, y=net_income.values, name='Net Income'))
            financials_fig.update_layout(
                title=f'Annual Financials for {ticker.upper()}',
                yaxis_title='Amount (USD)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                template='plotly_dark'
            )
        else:
            financials_fig.update_layout(title=f'Financials for {ticker.upper()}',
                                         annotations=[dict(text="Financial data not available", showarrow=False)],
                                         template='plotly_dark')

    except Exception:
        financials_fig.update_layout(title=f'Financials for {ticker.upper()}',
                                     annotations=[dict(text="Could not load financial data", showarrow=False)],
                                     template='plotly_dark')

    # --- 4. Dividend Table ---
    dividends = stock.dividends
    if not dividends.empty:
        dividends_df = dividends.reset_index()
        # Ensure column names are consistent
        dividends_df.columns = ['Date', 'Dividend']
        dividends_df['Date'] = pd.to_datetime(dividends_df['Date']).dt.strftime('%Y-%m-%d')
        dividends_df['Dividend'] = dividends_df['Dividend'].apply(lambda x: f"${x:.2f}")

        dividend_table_component = html.Div([
            html.H4("Dividend History"),
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in dividends_df.columns],
                data=dividends_df.to_dict('records'),
                style_table={'height': '300px', 'overflowY': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'backgroundColor': '#343a40',
                    'color': 'white',
                    'border': '1px solid #454d55'
                },
                style_header={
                    'backgroundColor': '#007bff',
                    'fontWeight': 'bold',
                    'color': 'white',
                    'border': '1px solid #454d55'
                },
                sort_action='native',
                sort_by=[{'column_id': 'Date', 'direction': 'desc'}]
            )
        ])
    else:
        dividend_table_component = html.Div([
            html.H4("Dividend History"),
            html.P("No dividend data available for this stock.")
        ])

    return stock_fig, company_info_layout, financials_fig, dividend_table_component

if __name__ == '__main__':
    app.run(debug=True)
