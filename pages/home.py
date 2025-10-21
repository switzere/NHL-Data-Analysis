import dash
from dash import html
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/", name="Home")

layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H1("Welcome to the NHL Dashboard!", className="text-center my-4"), width=12)
    ),
    dbc.Row(
        dbc.Col(html.P("Use the navigation bar to explore Standings, Teams, Games, and Players."), width=12)
    )
], fluid=True)