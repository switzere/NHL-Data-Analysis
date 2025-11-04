import mysql.connector
import pandas as pd
from config import db_config, db_config_local, db_config_local_socket
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date
import plotly.express as px



# Connect and load data
connection = mysql.connector.connect(
    host=db_config_local["host"],
    port=db_config_local["port"],
    user=db_config_local["user"],
    password=db_config_local["password"],
    database=db_config_local["database"]
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

def slug_to_name_and_id_and_abv(slug):
    team = teams[teams['slug'] == slug]
    if not team.empty:
        return team['team_name'].values[0], int(team['team_id'].values[0]), team['team_abbreviation'].values[0]
    return None, None, None

def get_team_abv(team):
    # If team is an int, treat as team_id
    if isinstance(team, int):
        result = teams[teams['team_id'] == team]
    # If team is a string, treat as team_name
    elif isinstance(team, str):
        result = teams[teams['team_name'] == team]
    else:
        result = pd.DataFrame()
    if not result.empty and 'team_abbreviation' in result.columns:
        return result['team_abbreviation'].values[0]
    return str(team)  # fallback

def get_team_id(team):
    # Try name first, then abbreviation
    result = teams[teams['team_name'] == team]
    if result.empty and 'team_abbreviation' in teams.columns:
        result = teams[teams['team_abbreviation'] == team]

    if not result.empty:
        return int(result['team_id'].values[0])
    return None

def get_team_name(team):
    # Accepts team_id (int), team_name (str), or team_abbreviation (str)
    if isinstance(team, int):
        result = teams[teams['team_id'] == team]
    elif isinstance(team, str):
        # Try name first, then abbreviation
        result = teams[teams['team_name'] == team]
        if result.empty and 'team_abbreviation' in teams.columns:
            result = teams[teams['team_abbreviation'] == team]
    else:
        result = pd.DataFrame()
    if not result.empty:
        return result['team_name'].values[0]
    return None

def get_logo(team_slug):
    team = teams[teams['slug'] == team_slug]
    if not team.empty and 'team_abbreviation' in team.columns:
        abv = team['team_abbreviation'].values[0]
        return f"/assets/logos/{abv}_logo.svg"
    return None

def get_season_end_standings_df(season):
    return seasons_end_standings_df[seasons_end_standings_df['Season'] == season]

def get_roster_players_df(season, team_slug):
    team_id = slug_to_name_and_id_and_abv(team_slug)[1]
    season_id = int(season)
    return roster_players[(roster_players['season_id'] == season_id) & (roster_players['team_id'] == team_id)]

def get_team_schedule_df(season, team_slug):
    team_id = slug_to_name_and_id_and_abv(team_slug)[1]
    season_id = int(season)
    cursor.execute("""
        SELECT * FROM games
        WHERE season_id = %s AND (home_team_id = %s OR away_team_id = %s)
    """, (season_id, team_id, team_id))
    schedule_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    return schedule_df

def get_game_df(game_id):
    cursor.execute("""
        SELECT * FROM games
        WHERE game_id = %s
    """, (game_id,))
    game_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    return game_df

def get_game_events_df(game_id):
    cursor.execute("""
        SELECT * FROM events
        WHERE game_id = %s
    """, (game_id,))
    events_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    return events_df

def get_games_around_date(season, days_before=10, days_after=10):
    season_id = int(season)
    current_date = date.today()
    cursor.execute("""
        SELECT * FROM games
        WHERE season_id = %s
          AND date BETWEEN DATE_SUB(%s, INTERVAL %s DAY) 
                       AND DATE_ADD(%s, INTERVAL %s DAY)
        ORDER BY date
    """, (season_id, current_date, days_before, current_date, days_after))
    games_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    return games_df

def get_current_season():
    cursor.execute("""
        SELECT DISTINCT season_id FROM games
        ORDER BY season_id DESC
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def get_most_recent_game():
    cursor.execute("""
        SELECT * FROM games
        WHERE game_outcome != ''
        ORDER BY date DESC
        LIMIT 1
    """)
    game_df = pd.DataFrame([cursor.fetchone()], columns=[i[0] for i in cursor.description])
    return game_df










def make_standings_table(df):
    display_columns = ['Team', 'GP', 'W', 'L', 'OTL', 'PTS']
    rows = []
    for _, row in df.iterrows():
        team_link = dcc.Link(row['Team'], href=f"/NHLDashboard/team/{row['slug']}/{row['Season']}")
        cells = [html.Td(team_link)] + [html.Td(row[col]) for col in display_columns if col != 'Team']
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col) for col in display_columns]))] +
        [html.Tbody(rows)],
        striped=True, bordered=True, hover=True, responsive=True
    )

def make_team_table(df):
    display_columns = ['firstName','lastName', 'sweaterNumber', 'positionCode', 'heightInCentimeters', 'weightInKilograms', 'birthDate', 'birthCountry']
    rows = []
    for _, row in df.iterrows():
        cells = [html.Td(row[col]) for col in display_columns]
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col) for col in display_columns]))] +
        [html.Tbody(rows)],
        striped=True, bordered=True, hover=True, responsive=True
    )

def make_schedule_row(df):
    current_date = date.today()
 
    games = []
    for _, row in df.iterrows():
        home_abv = get_team_abv(row['home_team_id'])
        away_abv = get_team_abv(row['away_team_id'])
        game_id = row['game_id']  # Assuming you have a game_id column
        games.append(
            dcc.Link(
                html.Div([
                    html.H5(f"{row['date']}"),
                    html.P(f"{away_abv} @ {home_abv}"),
                    html.P(f"Score: {row['away_score']} - {row['home_score']}")
                ], className="game-card",
                    id=f"game-{game_id}"
                ),
                href=f"/NHLDashboard/game/{game_id}"
            )
        )
    return html.Div(games, className="schedule-container")

def make_game_card(df):
    if df.empty:
        return html.Div("Game not found.")#, className="game-card")
    
    row = df.iloc[0]
    home_abv = get_team_abv(row['home_team_id'])
    away_abv = get_team_abv(row['away_team_id'])
    
    return html.Div([
        html.H3(f"{away_abv} @ {home_abv}"),
        html.P(f"Date: {row['date']}"),
        html.P(f"Score: {row['away_score']} - {row['home_score']}"),
    ])#, className="game-card")

# game_id int PK 
# season_id int 
# game_type int 
# date date 
# home_team_id int 
# away_team_id int 
# home_score int 
# away_score int 
# game_outcome varchar(255) 
# winning_goalie_id int 
# winning_goal_scorer_id int 
# series_status_round int

def make_events_graphic(df):
    if df.empty:
        return html.Div("No events found for this game.")
    
    # Add hover_text column if missing
    if 'hover_text' not in df.columns:
        df = df.copy()
        df['hover_text'] = (
            "Type: " + df['type_desc_key'].astype(str) +
            "<br>Period: " + df['period_number'].astype(str) +
            "<br>Time: " + df['time_in_period'].astype(str)
        )

    fig = px.scatter(
        df,
        x='x_coord',
        y='y_coord',
        color='type_desc_key',
        hover_name='type_desc_key',  # Main hover label
        hover_data={'hover_text': True, 'x_coord': True, 'y_coord': True, 'type_desc_key': False},
        labels={'x_coord': 'X Coordinate', 'y_coord': 'Y Coordinate'},
        range_x=[-100, 100],   # Set x-axis range
        range_y=[42, -42],      # Set y-axis range and reverse
        title='Event Locations'
    )

    fig.update_layout(width=900, height=600)

    
    return dcc.Graph(figure=fig)