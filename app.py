import streamlit as st
import pandas as pd
import altair as alt
import base64
import os
import numpy as np

# 1. PAGE CONFIG & CSS
st.set_page_config(page_title="CricValue | Pro Edition", layout="wide", page_icon="🏏")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .hero-card { background: linear-gradient(145deg, #1e2130, #161822); border-radius: 20px; padding: 20px; text-align: center; border: 1px solid #444; box-shadow: 0 10px 20px rgba(0,0,0,0.4); margin-bottom: 20px; }
    .player-name { color: white; margin: 10px 0; font-size: 1.5rem; font-weight: 700; }
    .price-tag { color: #4CAF50; font-weight: 900; margin: 10px 0; font-size: 2rem; }
    .role-badge { background-color: #333; color: #ccc; padding: 5px 15px; border-radius: 15px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .stat-box { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; margin-bottom: 10px; }
    .stat-label { color: #888; font-size: 0.8rem; text-transform: uppercase; }
    .stat-val { color: #fff; font-size: 1.2rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 2. IMAGE ASSETS ENGINE
ONLINE_LOGOS = {
    'CSK': 'https://upload.wikimedia.org/wikipedia/en/thumb/2/2b/Chennai_Super_Kings_Logo.svg/1200px-Chennai_Super_Kings_Logo.svg.png',
    'MI': 'https://upload.wikimedia.org/wikipedia/en/thumb/c/cd/Mumbai_Indians_Logo.svg/1200px-Mumbai_Indians_Logo.svg.png',
    'RCB': 'https://upload.wikimedia.org/wikipedia/en/thumb/2/2a/Royal_Challengers_Bangalore_2020.svg/1200px-Royal_Challengers_Bangalore_2020.svg.png',
    'KKR': 'https://upload.wikimedia.org/wikipedia/en/thumb/4/4c/Kolkata_Knight_Riders_Logo.svg/1200px-Kolkata_Knight_Riders_Logo.svg.png',
    'SRH': 'https://upload.wikimedia.org/wikipedia/en/thumb/8/81/Sunrisers_Hyderabad.svg/300px-Sunrisers_Hyderabad.svg.png',
    'RR': 'https://upload.wikimedia.org/wikipedia/en/thumb/6/60/Rajasthan_Royals_Logo.svg/1200px-Rajasthan_Royals_Logo.svg.png',
    'DC': 'https://upload.wikimedia.org/wikipedia/en/thumb/2/2f/Delhi_Capitals.svg/1200px-Delhi_Capitals.svg.png',
    'PBKS': 'https://upload.wikimedia.org/wikipedia/en/thumb/d/d4/Punjab_Kings_Logo.svg/1200px-Punjab_Kings_Logo.svg.png',
    'LSG': 'https://upload.wikimedia.org/wikipedia/en/a/a9/Lucknow_Super_Giants_IPL_Logo.svg',
    'GT': 'https://upload.wikimedia.org/wikipedia/en/thumb/0/09/Gujarat_Titans_Logo.svg/1200px-Gujarat_Titans_Logo.svg.png',
    'Free Agent': 'https://cdn-icons-png.flaticon.com/512/103/103206.png'
}

def get_team_logo(team_code):
    return ONLINE_LOGOS.get(team_code, ONLINE_LOGOS['Free Agent'])

# 3. DATA LOADING
@st.cache_data
def load_raw_data():
    csv_file = 'ipl_ball_by_ball_2008_2025.csv'
    zip_file = 'data.zip'
    try:
        if os.path.exists(csv_file): df = pd.read_csv(csv_file)
        elif os.path.exists(zip_file): df = pd.read_csv(zip_file, compression='zip')
        else: return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['year'] = df['date'].dt.year
        return df
    except: return pd.DataFrame()

# 4. VALUATION LOGIC (Optimized for Profiles)
@st.cache_data
def get_season_stats(df, player_name):
    # Batting per season
    bat_s = df[df['batter'] == player_name].groupby('year').agg(
        runs=('runs_off_bat', 'sum'),
        balls=('ball', 'count')
    ).reset_index()
    bat_s['sr'] = (bat_s['runs'] / bat_s['balls'].replace(0, 1)) * 100
    bat_s['points'] = bat_s['runs'] * ((bat_s['sr']/100)**2) / 1.25
    
    # Bowling per season
    bowl_s = df[df['bowler'] == player_name].groupby('year').agg(
        wkts=('is_wicket', 'sum'),
        runs_conceded=('total_runs', 'sum'),
        balls_bowled=('ball', 'count')
    ).reset_index()
    bowl_s['eco'] = (bowl_s['runs_conceded'] / bowl_s['balls_bowled'].replace(0, 1)) * 6
    bowl_s['points'] = bowl_s.apply(lambda x: (x['wkts'] * ((9.0/max(4, x['eco']))**2) * 35) if x['wkts'] > 0 else 0, axis=1)
    
    return bat_s, bowl_s

@st.cache_data
def calculate_vals(df, selected_year=None):
    if selected_year:
        df_subset = df[df['year'] == selected_year]
        latest_year = selected_year
    else:
        df_subset = df[df['year'] >= 2024]
        latest_year = 2025

    # Core Logic
    df_sorted = df.sort_values('date')
    last_team = pd.concat([df_sorted.groupby('batter')['batting_team'].last(), df_sorted.groupby('bowler')['bowling_team'].last()]).groupby(level=0).last()
    
    bat = df_subset.groupby('batter').agg(runs=('runs_off_bat', 'sum'), balls=('ball', 'count')).reset_index()
    bat.columns = ['Player', 'bat_runs', 'bat_balls']; bat['sr'] = (bat['bat_runs'] / bat['bat_balls'].replace(0, 1)) * 100
    bat['bat_points'] = bat['bat_runs'] * ((bat['sr']/100)**2) / 1.25

    bowl = df_subset.groupby('bowler').agg(wkts=('is_wicket', 'sum'), runs=('total_runs', 'sum'), balls=('ball', 'count')).reset_index()
    bowl.columns = ['Player', 'bowl_wkts', 'bowl_runs', 'bowl_balls']; bowl['eco'] = (bowl['bowl_runs'] / bowl['bowl_balls'].replace(0, 1)) * 6
    bowl['bowl_points'] = bowl.apply(lambda x: (x['bowl_wkts'] * ((9.0/max(4, x['eco']))**2) * 35) if x['bowl_wkts'] > 0 else 0, axis=1)

    merged = pd.merge(bat, bowl, on='Player', how='outer').fillna(0)
    merged['Team_Code'] = merged['Player'].map(last_team).map({
        'Chennai Super Kings': 'CSK', 'Mumbai Indians': 'MI', 'Royal Challengers Bangalore': 'RCB', 'Royal Challengers Bengaluru': 'RCB',
        'Kolkata Knight Riders': 'KKR', 'Sunrisers Hyderabad': 'SRH', 'Rajasthan Royals': 'RR', 'Delhi Capitals': 'DC', 'Punjab Kings': 'PBKS',
        'Lucknow Super Giants': 'LSG', 'Gujarat Titans': 'GT'
    }).fillna("Free Agent")
    
    merged['perf_points'] = merged.apply(lambda x: max(x['bat_points'], x['bowl_points']) + (min(x['bat_points'], x['bowl_points']) * 0.4), axis=1)
    merged['rank'] = merged['perf_points'].rank(ascending=False)
    merged['Market_Value'] = merged['rank'].apply(lambda r: min(35.0, 35.0 / (1 + 0.045 * r)) if r > 3 else 30.0 + (3-r))
    merged['Role'] = merged.apply(lambda x: "All-Rounder" if x['bat_points'] > 50 and x['bowl_points'] > 50 else ("Batter" if x['bat_points'] > x['bowl_points'] else "Bowler"), axis=1)
    
    return merged.sort_values('Market_Value', ascending=False)

# 5. UI APP
df_raw = load_raw_data()
if df_raw.empty: st.stop()

with st.sidebar:
    st.title("CricValue Pro")
    mode = st.radio("Mode", ["Projected Value", "Historical Season"])
    selected_year = st.selectbox("Season", sorted(df_raw['year'].unique(), reverse=True)) if mode == "Historical Season" else None

vals = calculate_vals(df_raw, selected_year)

# TABS
tab1, tab2, tab3 = st.tabs(["📋 Scouting", "📈 Clusters", "🔎 Career Profile"])

with tab1:
    st.dataframe(vals.head(50), use_container_width=True, hide_index=True)

with tab3:
    col_sel, _ = st.columns([1, 2])
    p_name = col_sel.selectbox("Select Player", sorted(df_raw['batter'].unique()))
    
    if p_name:
        bat_s, bowl_s = get_season_stats(df_raw, p_name)
        
        # Profile Header
        st.markdown(f"## {p_name}")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='stat-box'><div class='stat-label'>Career Runs</div><div class='stat-val'>{bat_s['runs'].sum()}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><div class='stat-label'>Career Wickets</div><div class='stat-val'>{bowl_s['wkts'].sum()}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box'><div class='stat-label'>Avg SR</div><div class='stat-val'>{bat_s['sr'].mean():.1f}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat-box'><div class='stat-label'>Best Season</div><div class='stat-val'>{int(bat_s.loc[bat_s['points'].idxmax(), 'year']) if not bat_s.empty else 'N/A'}</div></div>", unsafe_allow_html=True)

        # Career Chart
        st.markdown("### Career Impact Trajectory")
        chart_data = pd.merge(bat_s[['year', 'points']], bowl_s[['year', 'points']], on='year', how='outer', suffixes=('_bat', '_bowl')).fillna(0)
        chart_data['Total Impact'] = chart_data['points_bat'] + chart_data['points_bowl']
        
        line_chart = alt.Chart(chart_data).mark_line(point=True, color='#4CAF50').encode(
            x=alt.X('year:O', title='Season'),
            y=alt.Y('Total Impact:Q', title='Impact Points'),
            tooltip=['year', 'Total Impact']
        ).properties(height=300)
        st.altair_chart(line_chart, use_container_width=True)
        
        # Season Breakdown Table
        st.markdown("### Season-by-Season Breakdown")
        breakdown = pd.merge(
            bat_s.rename(columns={'runs': 'Runs', 'sr': 'S/R'}),
            bowl_s.rename(columns={'wkts': 'Wickets', 'eco': 'Economy'}),
            on='year', how='outer'
        ).fillna(0)[['year', 'Runs', 'S/R', 'Wickets', 'Economy']].sort_values('year', ascending=False)
        st.table(breakdown)
