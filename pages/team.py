import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_roster_players_df, available_seasons

dash.register_page(__name__, path_template="/team/<team_slug>/<season>", name="Team Page")

def layout(team_slug=None, season=None, **kwargs):
    df = get_roster_players_df(season, team_slug)
    if df.empty:
        return html.Div([
            dbc.Container([
                dbc.Row(dbc.Col(html.H1("Team Not Found", className="text-center my-4"), width=12)),
                dbc.Row(dbc.Col(html.P("The specified team could not be found. Please check the URL and try again.", className="text-center"), width=12))
            ], fluid=True)
        ])
    return html.Div([
        dbc.Container([
            dbc.Row(dbc.Col(html.H1(f"{team_slug} Roster ({season})", className="text-center my-4"), width=12)),
            dbc.Row([
                dbc.Col(html.Div([html.P(f"Player: {row['lastName']}") for _, row in df.iterrows()]), width=12)
            ])
        ], fluid=True)
    ])
