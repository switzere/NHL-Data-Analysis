import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_game_df, make_game_card, get_logo, make_game_card, get_game_events_df, make_events_graphic

dash.register_page(__name__, path_template="/game/<game_id>", name="Game Page")


def layout(game_id=None, **kwargs):
    df_game = get_game_df(game_id)
    df_events = get_game_events_df(game_id)
    return dbc.Container([
        dbc.Row(
            dbc.Col([make_game_card(df_game)], width=12)
        ),
        dbc.Row(
            dbc.Col([make_events_graphic(df_events)], width=12)
        )
    ], fluid=True)
