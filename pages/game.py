import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_game_df, make_game_card, get_logo, make_game_card, get_game_events_df, make_events_graphic, make_game_page

dash.register_page(__name__, path_template="/game/<game_id>", name="Game Page")


def layout(game_id=None, **kwargs):
    return dbc.Container([
        dbc.Row(
            dbc.Col([make_game_page(game_id)], width=12)
        )
    ], fluid=True)
