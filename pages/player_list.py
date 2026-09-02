import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
from dash import callback, no_update

from data import connection_pool, get_logo, get_team_name, search_players
from make_ui import make_player_table


dash.register_page(__name__, path="/player", name="Players")

def layout(**kwargs):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("Players", className="text-center my-4"),
                dbc.Input(id="player-search-input", placeholder="Search for a player...", type="text", debounce=True, className="mb-3", n_submit=0),
                dbc.Button("Search", id="player-search-btn", color="primary", className="mb-3 ms-2"),
                html.Div(id="player-search-results")
            ], width=12)
        ], className="common-text")
    ], fluid=True)

@callback(
    Output('player-search-results', 'children'),
    Input('player-search-btn', 'n_clicks'),
    Input('player-search-input', 'n_submit'),
    State('player-search-input', 'value'),
    prevent_initial_call=True
)
def search_players_page(n_clicks, n_submit, query):
    if not query or not query.strip():
        return ""
    query = query.strip().lower()
    players = search_players(query)
    player_links = []
    for _, row in players.iterrows():
        player_id = row['player_id']
        name = row['skaterFullName']
        player_links.append(
            dbc.Row([
                dbc.Col(dcc.Link(name, href=f"/NHLDashboard/player/{player_id}", className="h5"), width="auto")
            ], align="center", className="mb-2")
        )
    return html.Div(player_links)