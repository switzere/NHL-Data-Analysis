import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_roster_players_df, available_seasons, make_team_table

dash.register_page(__name__, path_template="/team/<team_slug>/<season>", name="Team Page")

def layout(team_slug=None, season=None, **kwargs):
    df = get_roster_players_df(season, team_slug)

    return dbc.Container([
        dbc.Row(dbc.Col(html.H1(f"{team_slug} Roster ({season})", className="text-center my-4"), width=12)),
        dbc.Row([
            dbc.Col([html.H2("Roster", className="text-center"), make_team_table(df)], width=12)
        ])
    ], fluid=True)