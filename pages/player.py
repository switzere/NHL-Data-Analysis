import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from data import get_player, get_player_name, get_player_seasons
from make_ui import make_player_table

dash.register_page(__name__, path_template="/player/<player_id>", name="Player Page")

def layout(player_id=None, **kwargs):
    if not player_id:
        return html.P("No player selected.")
    
    # Fetch player info using player_id and render it

    player = get_player(player_id)
    player_name = get_player_name(player_id) 
    player_seasons = get_player_seasons(player_id)

    return dbc.Container([
        dbc.Row(
            dbc.Col(html.H1(f"{player_name} ({player_id})", className="text-center my-4"), width=12)
        ),
        dbc.Row(
            dbc.Col([make_player_table(player_id)], width=12)
        )
    ])



