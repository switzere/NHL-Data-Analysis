import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_season_end_standings_df, make_standings_table
import pandas as pd

dash.register_page(__name__, path="/standings", name="Standings")

layout = html.Div(
    html.Div(id='standings-content')
)

@dash.callback(
    Output('standings-content', 'children'),
    Input('selected-season', 'data')
)
def update_standings(selected_season):
    df = get_season_end_standings_df(selected_season)

    if df['Conference'].isnull().all():
        return dbc.Container([
            dbc.Row(dbc.Col(html.H1(f"NHL Standings {selected_season}", className="text-center my-4"), width=12)),
            dbc.Row([
                dbc.Col([make_standings_table(df)], width=12),
            ])
        ], fluid=True)

    # Get unique conference names
    conferences = sorted([c for c in df['Conference'].unique() if pd.notnull(c)], reverse=True)

    # Split into conferences and divisions
    conference_tables = []
    for conf in conferences:
        conf_df = df[df['Conference'] == conf]
        if 'Division' in conf_df.columns and not conf_df['Division'].isnull().all():
            divisions = sorted([d for d in conf_df['Division'].unique() if pd.notnull(d)])
            division_tables = [
                html.Div([
                    html.H3(division, className="text-center"),
                    make_standings_table(conf_df[conf_df['Division'] == division])
                ]) for division in divisions
            ]
            conference_tables.append(
                dbc.Col([html.H2(conf, className="text-center"), *division_tables], width=6)
            )
        else:
            # No divisions, just show the conference table
            conference_tables.append(
                dbc.Col([html.H2(conf, className="text-center"), make_standings_table(conf_df)], width=6)
            )

    return dbc.Container([
        dbc.Row(dbc.Col(html.H1(f"NHL Standings {selected_season}", className="text-center my-4"), width=12)),
        dbc.Row(conference_tables)
    ], fluid=True)