import dash
from dash import html
import dash_bootstrap_components as dbc
from data import get_games_around_date, make_schedule_row, get_logo, get_current_season

dash.register_page(__name__, path="/", name="Home")

def layout(**kwargs):

    df_schedule = get_games_around_date(get_current_season(), days_before=10, days_after=10)
    
    return dbc.Container([
        dbc.Row(
            dbc.Col(html.H1("Welcome to the NHL Dashboard!", className="text-center my-4"), width=12)
        ),
        dbc.Row(
            dbc.Col([html.H2(f"Schedule"), make_schedule_row(df_schedule)], width=12)
        ),
        dbc.Row(
            dbc.Col(html.P("Use the navigation bar to explore Standings, Teams, Games, and Players."), width=12)
        )
    ], fluid=True)