import dash
from dash import html
import dash_bootstrap_components as dbc
from data import get_games_around_date, get_logo, get_current_season, make_schedule_grid

dash.register_page(__name__, path="/", name="Home")

def layout(**kwargs):
    todays_games = get_games_around_date(get_current_season(), days_before=0, days_after=0)
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("Welcome to the NHL Dashboard", className="text-center my-4"),
                html.P("Explore team rosters, schedules, and game statistics all in one place!", className="text-center"),
                html.Div([
                    html.A("Visit my Website", href="https://evanswitzer.ca/", target="_blank", className="d-block mb-2"),
                    html.A("View on GitHub", href="https://github.com/switzere/NHL-Data-Analysis", target="_blank", className="d-block")
                ], className="text-center")
            ], width=5),
            dbc.Col([
                html.H2("Today's Games", className="text-center"),
                make_schedule_grid(todays_games)
            ], width=7),
        ])
    ], fluid=True)