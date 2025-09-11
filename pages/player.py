import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_roster_players_df, make_team_table, get_team_schedule_df, make_schedule_row, get_logo

dash.register_page(__name__, path_template="/player/<player_id>", name="Player Page")

def layout(**kwargs):
    return dbc.Container([
        dbc.Row(
            dbc.Col(html.H2("This page is under construction.", className="text-center my-4"), width=12)
        )
    ], fluid=True)

def layout1(player_id=None, **kwargs):
    df_roster = get_roster_players_df(season, team_slug)
    df_schedule = get_team_schedule_df(season, team_slug)

    img_src = get_logo(team_slug)

    return dbc.Container([
        dbc.Row(
            dbc.Col([
                html.Img(src=img_src, alt=f"{team_slug} logo", style={"height": "60px", "marginRight": "1em"}),
                html.H1(f"{team_slug} Roster ({season})", className="text-center my-4")
            ], width=12)
        ),
        dbc.Row(
            dbc.Col([html.H2(f"Schedule"), make_schedule_row(df_schedule)], width=12)
        ),
        dbc.Row([
            dbc.Col([html.H2("Roster", className="text-center"), make_team_table(df_roster)], width=12)
        ])
    ], fluid=True)
