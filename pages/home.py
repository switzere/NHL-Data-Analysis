import dash
from dash import html
import dash_bootstrap_components as dbc
from data import get_games_around_date, get_logo, get_current_season, make_schedule_grid

dash.register_page(__name__, path="/", name="Home")

def layout(**kwargs):


    #df_schedule = get_games_around_date(get_current_season(), days_before=10, days_after=10)
    #if I want to use this get_current_season() probably gets split out

    todays_games = get_games_around_date(get_current_season(), days_before=0, days_after=0)
    
    return dbc.Container([
        dbc.Row(  # Wrap the columns in a Row
            [
                dbc.Col(
                    html.H1("Welcome to the NHL Dashboard", className="text-center my-4"), width=6
                ),
                dbc.Col(
                    dbc.Col([html.H2(f"Today's Games"), make_schedule_grid(todays_games)]),
                    width=6
                ),
            ]
        ),
        dbc.Row(
            dbc.Col(html.P("Use the navigation bar to explore Standings, Teams, Games, and Players."), width=12)
        )
    ], fluid=True)