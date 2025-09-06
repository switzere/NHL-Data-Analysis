import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import available_seasons, get_season_end_standings_df, make_standings_table

dash.register_page(__name__, path="/", name="Standings")

layout = html.Div([
    dcc.Dropdown(
        id='season-dropdown',
        options=[{'label': s, 'value': s} for s in available_seasons],
        value=available_seasons[-1],
        clearable=False,
        style={'marginBottom': '1em'}
    ),
    html.Div(id='standings-content')
])

@dash.callback(
    Output('standings-content', 'children'),
    Input('season-dropdown', 'value')
)
def update_standings(selected_season):
    df = get_season_end_standings_df(selected_season)
    eastern = df[df['Conference'] == 'Eastern']
    western = df[df['Conference'] == 'Western']
    return dbc.Container([
        dbc.Row(dbc.Col(html.H1(f"NHL Standings {selected_season}-{int(selected_season)+1}", className="text-center my-4"), width=12)),
        dbc.Row([
            dbc.Col([html.H2("Eastern Conference", className="text-center"), make_standings_table(eastern)], width=6),
            dbc.Col([html.H2("Western Conference", className="text-center"), make_standings_table(western)], width=6)
        ])
    ], fluid=True)