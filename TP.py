# %%
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import calendar

# 1. Chargement
candidate = Path(r'C:/Users/eliot/Documents/M1/python_avancé/cours-m1-ecap/data.csv')
if candidate.exists():
    csv_path = candidate
else:
    csv_path = None
    for base in [Path.cwd()] + list(Path.cwd().parents):
        found = next(base.rglob('data.csv'), None)
        if found:
            csv_path = found
            break
if csv_path is None:
    raise FileNotFoundError("data.csv not found.")

df = pd.read_csv(csv_path)

# 2. Colonnes utiles
cols = ['CustomerID', 'Gender', 'Location', 'Product_Category',
        'Quantity', 'Avg_Price', 'Transaction_Date', 'Month', 'Discount_pct']
df = df[cols]

# 3. Nettoyage
df['CustomerID'] = df['CustomerID'].fillna(0).astype(int)
df['Transaction_Date'] = pd.to_datetime(df['Transaction_Date'])
df['Total_price'] = df['Quantity'] * df['Avg_Price'] * (1 - df['Discount_pct'] / 100)

# ── Fonctions graphiques ──────────────────────────────────────────────────────

def barplot_top_10_ventes(data):
    top_cats = (data.groupby('Product_Category')['Quantity']
                .sum().sort_values(ascending=False).head(10).index)
    df_top = data[data['Product_Category'].isin(top_cats)]
    df_plot = (df_top.groupby(['Product_Category', 'Gender'])['Quantity']
               .sum().reset_index())
    cat_order = (df_plot.groupby('Product_Category')['Quantity']
                 .sum().sort_values(ascending=False).index.tolist())  # descending pour highest at top
    fig = px.bar(
        df_plot, x='Quantity', y='Product_Category', color='Gender',
        title='Frequence des 10 meilleures ventes',
        barmode='group', orientation='h',
        category_orders={'Product_Category': cat_order},
        color_discrete_map={'F': '#4e79a7', 'M': '#e15759'},
        labels={'Quantity': 'Total vente', 'Product_Category': 'Catégorie du produit'}
    )
    fig.update_layout(
        legend_title_text='Sexe',
        margin=dict(l=10, r=10, t=50, b=10),
        height=320,
        font=dict(size=10)
    )
    return fig


def plot_evolution_chiffre_affaire(data):
    data_copy = data.copy()
    data_copy['Week'] = data_copy['Transaction_Date'].dt.to_period('W').apply(
        lambda r: r.start_time)
    evolution = data_copy.groupby('Week')['Total_price'].sum().reset_index()
    min_y = evolution['Total_price'].min()
    max_y = evolution['Total_price'].max()
    fig = px.area(
        evolution, x='Week', y='Total_price',
        title="Evolution du chiffre d'affaire par semaine",
        labels={'Week': 'Semaine', 'Total_price': "Chiffre d'affaire"}
    )
    fig.update_traces(line_color='#4e79a7')
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=200,
        yaxis=dict(
            range=[min_y - 1000, 120000],
            autorange=False,
            rangemode='normal'
        )
    )
    return fig

# ── Indicateurs du mois ───────────────────────────────────────────────────────

current_month = 12
prev_month = 11

def format_number(num):
    if abs(num) >= 1000:
        return f"{num/1000:.0f}k"
    return f"{num:.0f}"

revenue_current = df[df['Month'] == current_month]['Total_price'].sum()
revenue_prev    = df[df['Month'] == prev_month]['Total_price'].sum()
revenue_delta   = revenue_current - revenue_prev
revenue_color   = 'green' if revenue_delta >= 0 else 'red'
revenue_arrow   = '▲' if revenue_delta >= 0 else '▼'

orders_current  = len(df[df['Month'] == current_month])
orders_prev     = len(df[df['Month'] == prev_month])
orders_delta    = orders_current - orders_prev
orders_color    = 'green' if orders_delta >= 0 else 'red'
orders_arrow    = '▲' if orders_delta >= 0 else '▼'

month_name = calendar.month_name[current_month]  # "December"

# ── Table des 100 dernières ventes ────────────────────────────────────────────

last_100 = (df.sort_values('Transaction_Date', ascending=False)
            .head(100)
            [['Transaction_Date', 'Gender', 'Location',
              'Product_Category', 'Quantity', 'Avg_Price', 'Discount_pct']]
            .rename(columns={
                'Transaction_Date': 'Date',
                'Product_Category': 'Product Category',
                'Avg_Price':        'Avg Price',
                'Discount_pct':     'Discount Pct'
            }))
last_100['Date'] = last_100['Date'].dt.strftime('%Y-%m-%d')

# ── App Dash ──────────────────────────────────────────────────────────────────

import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

TEAL = '#5bc0be'

app.layout = dbc.Container(fluid=True, children=[

    # ── Titre + filtre ──────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.H4("ECAP Store", style={'fontWeight': 'bold', 'margin': '10px 0'}), width=6),
        dbc.Col([
            html.Label("Zone:", style={'fontSize': '12px', 'marginBottom': '5px'}),
            dcc.Dropdown(
                id='location-dropdown',
                options=[{'label': 'Toutes les zones', 'value': 'all'}] + 
                        [{'label': loc, 'value': loc} for loc in sorted(df['Location'].dropna().unique())],
                value='all',
                clearable=False,
            )
        ], width=6, className='ms-auto', style={'paddingTop': '8px'}),
    ], align='center', style={'backgroundColor': TEAL, 'padding': '0 15px'}),

    # ── Contenu principal ───────────────────────────────────────────────────
    dbc.Row([

        # Colonne gauche
        dbc.Col(width=5, children=[

            # KPI cards
            dbc.Row([
                dbc.Col([
                    html.Div(id='revenue-month', style={'fontSize': '14px', 'color': '#555'}),
                    html.Div(id='revenue-value', style={'fontSize': '42px', 'fontWeight': 'bold'}),
                    html.Div(id='revenue-delta')
                ], width=6, style={'padding': '20px'}),

                dbc.Col([
                    html.Div(id='orders-month', style={'fontSize': '14px', 'color': '#555'}),
                    html.Div(id='orders-value', style={'fontSize': '42px', 'fontWeight': 'bold'}),
                    html.Div(id='orders-delta')
                ], width=6, style={'padding': '20px'}),
            ]),

            # graphique en barres
            dcc.Graph(id='bar-chart', figure=barplot_top_10_ventes(df), config={'displayModeBar': False}),
        ]),

        # Colonne droite
        dbc.Col(width=7, children=[

            # graphique en aires
            dcc.Graph(id='area-chart', figure=plot_evolution_chiffre_affaire(df),
                      config={'displayModeBar': False}),

            # Titre table
            html.H6("Table des 100 dernières ventes",
                    ),

            # DataTable
            dash_table.DataTable(
                id='data-table',
                data=last_100.to_dict('records'),
                columns=[{"name": c, "id": c} for c in last_100.columns],
                page_size=10,
                filter_action='native',
                sort_action='native',
                style_table={'height': '180px', 'overflowY': 'auto', 'overflowX': 'auto'},
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'fontSize': '8px'
                },
                style_cell={
                    'fontSize': '8px',
                    'padding': '1px 3px',
                    'textAlign': 'left'
                },
                style_data_conditional=[{
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f9f9f9'
                }]
            )
        ])
    ])
], style={'padding': '0'})

@app.callback(
    Output('bar-chart', 'figure'),
    Output('area-chart', 'figure'),
    Output('data-table', 'data'),
    Output('revenue-month', 'children'),
    Output('revenue-value', 'children'),
    Output('revenue-delta', 'children'),
    Output('orders-month', 'children'),
    Output('orders-value', 'children'),
    Output('orders-delta', 'children'),
    Input('location-dropdown', 'value')
)
def update_charts(selected_location):
    selected_month = 12
    prev_month = 11
    if selected_location == 'all':
        kpi_df = df[df['Month'] == selected_month]
        kpi_prev_df = df[df['Month'] == prev_month]
        chart_df = df
    else:
        kpi_df = df[(df['Month'] == selected_month) & (df['Location'] == selected_location)]
        kpi_prev_df = df[(df['Month'] == prev_month) & (df['Location'] == selected_location)]
        chart_df = df[df['Location'] == selected_location]
    
    # Calcul des KPIs 
    revenue_current = kpi_df['Total_price'].sum()
    revenue_prev = kpi_prev_df['Total_price'].sum()
    revenue_delta = revenue_current - revenue_prev
    revenue_color = 'green' if revenue_delta >= 0 else 'red'
    revenue_arrow = '▲' if revenue_delta >= 0 else '▼'
    
    orders_current = len(kpi_df)
    orders_prev = len(kpi_prev_df)
    orders_delta = orders_current - orders_prev
    orders_color = 'green' if orders_delta >= 0 else 'red'
    orders_arrow = '▲' if orders_delta >= 0 else '▼'
    
    month_name = calendar.month_name[selected_month]
    
    # Formatage des KPIs
    revenue_month = month_name
    revenue_value = format_number(revenue_current)
    revenue_delta_div = html.Div([
        html.Span(revenue_arrow, style={'color': revenue_color}),
        html.Span(f" {format_number(abs(revenue_delta))}", style={'color': revenue_color, 'fontSize': '18px'})
    ])
    
    orders_month = month_name
    orders_value = f"{orders_current:,}"
    orders_delta_div = html.Div([
        html.Span(orders_arrow, style={'color': orders_color}),
        html.Span(f" {abs(orders_delta):,}", style={'color': orders_color, 'fontSize': '18px'})
    ])
    
    # Mise à jour des graphiques et de la table
    bar_fig = barplot_top_10_ventes(chart_df)
    area_fig = plot_evolution_chiffre_affaire(chart_df)
    
    last_100_filtered = (chart_df.sort_values('Transaction_Date', ascending=False)
                         .head(100)
                         [['Transaction_Date', 'Gender', 'Location',
                           'Product_Category', 'Quantity', 'Avg_Price', 'Discount_pct']]
                         .rename(columns={
                             'Transaction_Date': 'Date',
                             'Product_Category': 'Product Category',
                             'Avg_Price':        'Avg Price',
                             'Discount_pct':     'Discount Pct'
                         }))
    last_100_filtered['Date'] = last_100_filtered['Date'].dt.strftime('%Y-%m-%d')
    table_data = last_100_filtered.to_dict('records')
    
    return (bar_fig, area_fig, table_data,
            revenue_month, revenue_value, revenue_delta_div,
            orders_month, orders_value, orders_delta_div)

if __name__ == '__main__':
    app.run(debug=False, port=8099, jupyter_mode='external')


