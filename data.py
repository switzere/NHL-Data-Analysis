import mysql.connector
import pandas as pd
from config import db_config
from dash import dcc, html
import dash_bootstrap_components as dbc

# Connect and load data
connection = mysql.connector.connect(
    host=db_config["host"],
    user=db_config["user"],
    password=db_config["password"],
    database=db_config["database"]
)
cursor = connection.cursor()

cursor.execute("""
    SELECT *
    FROM seasons_end_standings
    WHERE games_played > 0
""")
seasons_end_standings_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])

cursor.execute("""
    SELECT * FROM teams
""")
teams = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])

cursor.execute("""
    SELECT * FROM roster_players
""")
roster_players = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])

# Data cleaning and merging
column_mapping = {
    'team_name': 'Team',
    'games_played': 'GP',
    'wins': 'W',
    'losses': 'L',
    'ot_losses': 'OTL',
    'points': 'PTS',
    'conference_name': 'Conference',
    'season_id': 'Season'
}
seasons_end_standings_df = seasons_end_standings_df.merge(
    teams[['team_id', 'team_name']],
    left_on='team_id',
    right_on='team_id',
    how='left'
)
seasons_end_standings_df.rename(columns=column_mapping, inplace=True)
seasons_end_standings_df = seasons_end_standings_df.sort_values(by='PTS', ascending=False)
seasons_end_standings_df['slug'] = seasons_end_standings_df['Team'].str.replace(' ', '-').str.lower()
teams['slug'] = teams['team_name'].str.replace(' ', '-').str.lower()
available_seasons = sorted(seasons_end_standings_df['Season'].unique())

def get_season_end_standings_df(season):
    return seasons_end_standings_df[seasons_end_standings_df['Season'] == season]

def get_roster_players_df(season, team_slug):
    team_id = teams[teams['slug'] == team_slug]['team_id'].iloc[0]
    season_id = int(season)
    return roster_players[(roster_players['season_id'] == season_id) & (roster_players['team_id'] == team_id)]

def make_table(df):
    display_columns = ['Team', 'GP', 'W', 'L', 'OTL', 'PTS']
    rows = []
    for _, row in df.iterrows():
        team_link = dcc.Link(row['Team'], href=f"/team/{row['slug']}/{row['Season']}")
        cells = [html.Td(team_link)] + [html.Td(row[col]) for col in display_columns if col != 'Team']
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col) for col in display_columns]))] +
        [html.Tbody(rows)],
        striped=True, bordered=True, hover=True, responsive=True
    )