import mysql.connector
from mysql.connector import pooling
import pandas as pd
from config import db_config, db_config_local, db_config_local_socket
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date, datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pytz


# Create a connection pool
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host=db_config["host"],
    port=db_config["port"],
    user=db_config["user"],
    password=db_config["password"],
    database=db_config["database"],
    use_pure=True,
    connection_timeout=10
)

# local connection
# connection_pool = mysql.connector.connect(
#     pool_name="mypool",
#     pool_size=5,
#     host=db_config_local["host"],
#     port=db_config_local["port"],
#     user=db_config_local["user"],
#     password=db_config_local["password"],
#     database=db_config_local["database"]
# )

#cursor = connection.cursor()

seasons = pd.DataFrame()
teams = pd.DataFrame()

connection = connection_pool.get_connection()
try:
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM seasons
    """)
    seasons = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])

    available_seasons = sorted(seasons['season_id'].unique())#was start_year so that it looks nice but season_id works for the current functionality

    cursor.execute("""
        SELECT * FROM teams
    """)
    teams = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
finally:
    cursor.close()
    connection.close()


def slug_to_name_and_id_and_abv(slug):
    team_name = slug.replace('-', ' ').lower()
    team = teams[teams['team_name'].str.lower() == team_name]
    if not team.empty:
        return team['team_name'].values[0], int(team['team_id'].values[0]), team['team_abbreviation'].values[0]
    return None, None, None

def get_team_abv(team):
    # If team is an int, treat as team_id
    result = None

    if isinstance(team, (int, np.integer)):
        result = teams[teams['team_id'] == team]
    # If team is a string, treat as team_name
    elif isinstance(team, str):
        result = teams[teams['team_name'] == team]

    if result is not None and not result.empty:
        return str(result['team_abbreviation'].values[0])

    return None

def get_team_id(team):
    # Try name first, then abbreviation
    result = teams[teams['team_name'] == team]
    if result.empty and 'team_abbreviation' in teams.columns:
        result = teams[teams['team_abbreviation'] == team]

    if not result.empty:
        return int(result['team_id'].values[0])
    return None

def get_team_name(team_id = None, team_abv = None):
    # Accepts team_id (int) or team_abbreviation (str)
    if team_id is not None:
        return teams[teams['team_id'] == team_id]['team_name'].values[0]
    
    if team_abv is not None:
        return teams[teams['team_abbreviation'] == team_abv]['team_name'].values[0]
    
    return None

def get_logo(team_slug = None, team_id = None):
    if team_slug is not None:
        team_id = slug_to_name_and_id_and_abv(team_slug)[1]

    if team_id is not None:
        team = teams[teams['team_id'] == team_id]
    else:
        return None

    if not team.empty and 'team_abbreviation' in team.columns:
        abv = team['team_abbreviation'].values[0]
        return f"/NHLDashboard/assets/logos/{abv}_logo.svg"
    return None

def get_season_end_standings_df(season):
    seasons_end_standings_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT *
            FROM seasons_end_standings
            WHERE season_id = %s
            AND games_played > 0
        """, (int(season),))

        seasons_end_standings_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

        # Data cleaning and merging
    # column_mapping = {
    #     'team_name': 'Team',
    #     'games_played': 'GP',
    #     'wins': 'W',
    #     'losses': 'L',
    #     'ot_losses': 'OTL',
    #     'points': 'PTS',
    #     'conference_name': 'Conference',
    #     'division_name': 'Division',
    #     'season_id': 'Season',
        
    #     'wildcard_rank': 'WC'
    # }
    seasons_end_standings_df = seasons_end_standings_df.merge(
        teams[['team_id', 'team_name']],
        left_on='team_id',
        right_on='team_id',
        how='left'
    )

    seasons_end_standings_df = attach_wildcard_standings(seasons_end_standings_df)

    #seasons_end_standings_df.rename(columns=column_mapping, inplace=True)
    seasons_end_standings_df = seasons_end_standings_df.sort_values(by='points', ascending=False)
    seasons_end_standings_df['slug'] = seasons_end_standings_df['team_name'].str.replace(' ', '-').str.lower()
    teams['slug'] = teams['team_name'].str.replace(' ', '-').str.lower()


    return seasons_end_standings_df[seasons_end_standings_df['season_id'] == season]

def get_roster_players_df(season, team_slug):
    roster_players = pd.DataFrame()

    team_id = slug_to_name_and_id_and_abv(team_slug)[1]
    season_id = int(season)

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT DISTINCT * FROM roster_players
                LEFT JOIN players_season
                ON (roster_players.player_id = players_season.player_id AND roster_players.season_id = players_season.season_id)
                WHERE roster_players.season_id = %s
                AND roster_players.team_id = %s
                AND players_season.games_played > 0
        """, (season_id, team_id))
        roster_players = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

    return roster_players

def get_team_schedule_df(season, team_slug):
    schedule_df = pd.DataFrame()

    team_id = slug_to_name_and_id_and_abv(team_slug)[1]
    season_id = int(season)

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE season_id = %s AND (home_team_id = %s OR away_team_id = %s)
        """, (season_id, team_id, team_id))
        schedule_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

    return schedule_df

def get_game_df(game_id):
    game_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE game_id = %s
        """, (game_id,))
        game_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return game_df

def get_game_events_df(game_id):
    events_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE game_id = %s
        """, (game_id,))
        events_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return events_df

def get_games_of_season(season = None):
    if season is None:
        season = get_current_season()

    games_df = pd.DataFrame()
    season_id = int(season)

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE season_id = %s
            ORDER BY date
        """, (season_id,))
        games_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return games_df

def get_games_around_date(season=None, days_before=10, days_after=10):
    games_df = pd.DataFrame()

    if season is None:
        season = get_current_season()

    season_id = int(season)
    current_date = date.today()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE season_id = %s
            AND date BETWEEN DATE_SUB(%s, INTERVAL %s DAY) 
                        AND DATE_ADD(%s, INTERVAL %s DAY)
            ORDER BY date
        """, (season_id, current_date, days_before, current_date, days_after))
        games_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return games_df

def get_current_season():
    result = None

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT DISTINCT season_id FROM games
            ORDER BY season_id DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if result:
        return result[0]
    return None

def get_most_recent_games(num = 1, team_id = None):
    games_df = pd.DataFrame()

    team_where = ""
    params = [num]

    if team_id is not None:
        team_where = "AND (home_team_id = %s OR away_team_id = %s)"
        params = [team_id, team_id, num]
    else:
        #every team in season
        team_where = ""
        params = [num]

    connection = connection_pool.get_connection()
    # try:
    #     cursor = connection.cursor()
    #     cursor.execute(f"""
    #         SELECT * FROM games
    #         WHERE game_outcome != ''
    #         {team_where}
    #         ORDER BY date DESC
    #         LIMIT %s
    #     """, tuple(params))
    try:
        cursor = connection.cursor()
        cursor.execute(f"""
            WITH Base AS (
                SELECT *
                FROM games
                WHERE game_outcome != ''
                {team_where}
            ),
            Expanded AS (
                SELECT 
                    game_id,
                    date,
                    home_team_id AS team_id,
                    away_team_id AS opponent_id,
                    game_outcome,
                    home_score AS team_score,
                    away_score AS opponent_score
                FROM Base

                UNION ALL

                SELECT
                    game_id,
                    date,
                    away_team_id AS team_id,
                    home_team_id AS opponent_id,
                    game_outcome,
                    away_score AS team_score,
                    home_score AS opponent_score
                FROM Base
            ),
            Ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY team_id
                        ORDER BY date DESC
                    ) AS game_rank
                FROM Expanded
            )
            SELECT *
            FROM Ranked
            WHERE game_rank <= %s;
        """, tuple(params))
        games_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return games_df

def get_player(player_id):
    player_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM players
            WHERE player_id = %s
        """, (player_id,))
        player_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return player_df

def get_player_name(player_id, default="Unknown"):
    try:
        if player_id is None:
            return default
        df = get_player(player_id)
        if df.empty:
            return default
        if 'skaterFullName' in df.columns and not pd.isnull(df['skaterFullName'].values[0]):
            return str(df['skaterFullName'].values[0])
        return default
    except Exception:
        return default

def get_player_seasons(player_id):
    player_seasons_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM players_season
            WHERE player_id = %s
            ORDER BY season_id DESC
        """, (player_id,))
        player_seasons_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return player_seasons_df

def get_teams_ordered():
    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT s.team_id, MAX(s.season_id) AS last_season, t.team_name
            FROM seasons_end_standings s
            JOIN teams t ON s.team_id = t.team_id
            WHERE s.games_played > 0
            GROUP BY s.team_id, t.team_name
        """)
        teams_last_season = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

    teams_last_season = teams_last_season.sort_values(by=['last_season', 'team_name'], ascending=[False, True])
    return teams_last_season

def get_teams_games_season(team_id, season_id=20252026):
    games_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT *
            FROM games
            WHERE season_id = %s
            AND (home_team_id = %s OR away_team_id = %s)
            AND game_outcome IS NOT NULL
            AND game_type = 2;
        ''', (season_id, team_id, team_id))
        games_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return games_df


#this should probably be changed once I fix the timestamps in the database
def UTC_to_EST(start_time_UTC):
    start_time = None

    eastern = pytz.timezone('US/Eastern')  # Define the EST timezone

    game_datetime_UTC = start_time_UTC
    game_datetime_UTC = game_datetime_UTC.replace(tzinfo=pytz.UTC)  # Declare it as UTC

    game_datetime_EST = game_datetime_UTC.astimezone(eastern)

    return game_datetime_EST

def attach_wildcard_standings(season_end_standings_df):
    # Get wildcard teams for each conference

    top_3_in_divisions = season_end_standings_df.sort_values(by=['conference_name', 'division_name', 'points', 'wins'],ascending=[True, True, False, False]).groupby(['conference_name', 'division_name']).head(3).reset_index(drop=True)
#    top_3_in_divisions = season_end_standings_df.groupby(['conference_name', 'division_name']).head(3).sort_values(by=['points', 'wins'], ascending=False)

    #for each set of 3 in a division give them "wildcard_rank" of 1, 2, or 3 based on points and wins
    top_3_in_divisions['wildcard_rank'] = top_3_in_divisions.groupby(['conference_name', 'division_name']).cumcount() + 1

    #everything that doesn't have a wildcard_rank goes into wildcard teams
    wildcard_teams = season_end_standings_df[~season_end_standings_df['team_id'].isin(top_3_in_divisions['team_id'])].copy()
    #sort wildcard_teams
    wildcard_teams = wildcard_teams.sort_values(by=['conference_name', 'points', 'wins'], ascending=[True, False, False])

    wildcard_teams['wildcard_rank'] = wildcard_teams.groupby('conference_name').cumcount() + 7

    season_end_standings_df = season_end_standings_df.merge(
        top_3_in_divisions[['team_id', 'wildcard_rank']],
        on='team_id',
        how='left'
    )

    season_end_standings_df = season_end_standings_df.merge(
        wildcard_teams[['team_id', 'wildcard_rank']],
        on='team_id',
        how='left'
    )

    season_end_standings_df['wildcard_rank'] = season_end_standings_df['wildcard_rank_x'].combine_first(season_end_standings_df['wildcard_rank_y'])

    season_end_standings_df = season_end_standings_df.drop(columns=['wildcard_rank_x', 'wildcard_rank_y'])

    return season_end_standings_df

def search_players(player_name):
    players_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM players
            WHERE LOWER(skaterFullName) LIKE %s
            LIMIT 25
        """, (f"%{player_name.lower()}%",))
        players_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return players_df














