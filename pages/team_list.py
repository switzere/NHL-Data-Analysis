import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from data import get_teams_ordered, slug_to_name_and_id_and_abv, get_logo

dash.register_page(__name__, path="/team", name="Teams")

def layout(**kwargs):
    teams_df = get_teams_ordered()
    team_links = []
    for _, team in teams_df.iterrows():
        team_name = team['team_name']
        team_id = team['team_id']
        team_abv = team['team_abbreviation']
        slug = team_name.replace(' ', '-').lower()
        logo_src = get_logo(team_id=team_id)
        team_links.append(
            dcc.Link(
                html.Div([
                    html.Img(src=logo_src, alt=team_name, className="team-logo"),
                    html.Div(team_name, className="team-name")
                ], className="team-link-content"),
                href=f"/NHLDashboard/team/{slug}",
                className=f"team-link team-{team_abv}"
            )
        )
    return dbc.Container([
        dbc.Row(dbc.Col(html.H1("Select a Team", className="text-center my-4 common-text"), width=12)),
        dbc.Row(dbc.Col(html.Div(team_links, className="team-grid"), width=12))
    ], fluid=True)