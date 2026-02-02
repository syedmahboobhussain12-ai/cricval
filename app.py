import streamlit as st
import pandas as pd
import numpy as np
import os
import requests
from pathlib import Path

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="CricValue | Market Board",
    layout="wide",
    page_icon="🏏"
)

# -------------------------------------------------
# STYLES (UPDATED FOR SWIPE/SNAP)
# -------------------------------------------------
st.markdown("""
<style>
/* App Background */
.stApp { background-color: #0E1117; color: #EAEAEA; }

/* The "Swipe" Container */
.hero-scroll {
    display: flex;
    overflow-x: auto;
    gap: 20px;
    padding: 20px 0 40px 0;
    
    /* This creates the "Swipe/Snap" effect */
    scroll-snap-type: x mandatory; 
    scroll-behavior: smooth;
    
    /* Hide Scrollbar for cleaner UI */
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE/Edge */
}

/* Hide Scrollbar for Chrome/Safari */
.hero-scroll::-webkit-scrollbar {
    display: none;
}

/* Individual Card */
.hero-card {
    /* SNAP ALIGNMENT */
    scroll-snap-align: center;
    
    min-width: 85vw; /* On mobile, card takes 85% of width to show "peek" of next card */
    max-width: 85vw;
    
    background: linear-gradient(145deg, #1e2130, #141625);
    border-radius: 24px;
    padding: 24px;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    flex-shrink: 0;
    position: relative;
    transition: transform 0.3s;
}

/* Desktop override: Make cards smaller on big screens */
@media (min-width: 768px) {
    .hero-card {
        min-width: 320px;
        max-width: 320px;
    }
}

.player-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.player-name {
    font-size: 1.4rem;
    font-weight: 800;
    color: white;
    margin-top: 5px;
}

.price {
    color: #4CAF50;
    font-weight: 900;
    font-size: 1.8rem;
    margin-bottom: 5px;
}

.role-badge {
    background: rgba(255, 255, 255, 0.1);
    color: #ccc;
    padding: 5px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}

/* Stats Grid */
.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid rgba(255,255,255,0.08);
}

.stat-item {
    display: flex;
    flex-direction: column;
}

.stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-val { font-size: 1.1rem; font-weight: 700; color: #fff; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# ASSETS & LOGOS
# -------------------------------------------------
TEAM_LOGOS = {
    "CSK": "https://upload.wikimedia.org/wikipedia/en/thumb/2/2b/Chennai_Super_Kings_Logo.svg/1200px-Chennai_Super_Kings_Logo.svg.png",
    "MI": "https://upload.wikimedia.org/wikipedia/en/thumb/c/cd/Mumbai_Indians_Logo.svg/1200px-Mumbai_Indians_Logo.svg.png",
    "RCB": "https://upload.wikimedia.org/wikipedia/en/thumb/2/2a/Royal_Challengers_Bangalore_2020.svg/1200px-Royal_Challengers_Bangalore_2020.svg.png",
    "KKR": "https://upload.wikimedia.org/wikipedia/en/thumb/4/4c/Kolkata_Knight_Riders_Logo.svg/1200px-Kolkata_Knight_Riders_Logo.svg.png",
    "SRH": "https://upload.wikimedia.org/wikipedia/en/thumb/8/81/Sunrisers_Hyderabad.svg/300px-Sunrisers_Hyderabad.svg.png",
    "RR": "https://upload.wikimedia.org/wikipedia/en/thumb/6/60/Rajasthan_Royals_Logo.svg/1200px-Rajasthan_Royals_Logo.svg.png",
    "DC": "https://upload.wikimedia.org/wikipedia/en/thumb/2/2f/Delhi_Capitals.svg/1200px-Delhi_Capitals.svg.png",
    "PBKS": "https://upload.wikimedia.org/wikipedia/en/thumb/d/d4/Punjab_Kings_Logo.svg/1200px-Punjab_Kings_Logo.svg.png",
    "LSG": "https://upload.wikimedia.org/wikipedia/en/a/a9/Lucknow_Super_Giants_IPL_Logo.svg",
    "GT": "https://upload.wikimedia.org/wikipedia/en/thumb/0/09/Gujarat_Titans_Logo.svg/1200px-Gujarat_Titans_Logo.svg.png",
}

def get_team_logo(team_code):
    return TEAM_LOGOS.get(team_code, "https://cdn-icons-png.flaticon.com/512/103/103206.png")

# -------------------------------------------------
# SMART DATA LOADER
# -------------------------------------------------
@st.cache_data
def load_data():
    csv_file = 'ipl_ball_by_ball_2008_2025.csv'
    zip_file = 'data.zip'
    
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
    elif os.path.exists(zip_file):
        df = pd.read_csv(zip_file, compression='zip')
    else:
        st.error("❌ No data found! Please upload 'ipl_ball_by_ball_2008_2025.csv' or 'data.zip'.")
        return pd.DataFrame()

    df['date'] = pd.to_datetime(df.get('date'), errors='coerce')
    df['year'] = df['date'].dt.year
    return df

# -------------------------------------------------
# VALUATION ENGINE
# -------------------------------------------------
@st.cache_data
def calculate_valuation(df):
    # Determine Team
    df_sorted = df.sort_values('date')
    last_team = df_sorted.groupby('batter')['batting_team'].last().combine_first(
        df_sorted.groupby('bowler')['bowling_team'].last()
    )
    
    df_recent = df[df['year'] >= 2024]
    if df_recent.empty: return pd.DataFrame()

    # Batting
    bat = df_recent.groupby('batter').agg(
        Runs=('runs_off_bat', 'sum'),
        Balls=('ball', 'count'),
        Matches=('match_id', 'nunique')
    ).reset_index()
    bat['Strike Rate'] = (bat['Runs'] / bat['Balls']) * 100
    bat['bat_points'] = bat['Runs'] * ((bat['Strike Rate'] / 100) ** 2) / 1.25
    bat = bat[bat['Matches'] >= 3]

    # Bowling
    bowl = df_recent.groupby('bowler').agg(
        Wickets=('is_wicket', 'sum'),
        Runs_Conceded=('total_runs', 'sum'),
        Balls=('ball', 'count'),
        Matches=('match_id', 'nunique')
    ).reset_index()
    bowl['Economy'] = (bowl['Runs_Conceded'] / bowl['Balls']) * 6
    bowl['bowl_points'] = bowl.apply(
        lambda x: (x['Wickets'] * ((9.0 / max(4, x['Economy'])) ** 2) * 35)
        if x['Wickets'] > 0 else 0, axis=1
    )
    bowl = bowl[bowl['Matches'] >= 3]

    # Merge
    merged = pd.merge(bat.rename(columns={'batter':'Player'}), 
                      bowl.rename(columns={'bowler':'Player'}), 
                      on='Player', how='outer').fillna(0)
    
    merged['Team'] = merged['Player'].map(last_team).fillna("Free Agent")
    team_map = {
        'Chennai Super Kings': 'CSK', 'Mumbai Indians': 'MI', 'Royal Challengers Bangalore': 'RCB', 
        'Royal Challengers Bengaluru': 'RCB', 'Kolkata Knight Riders': 'KKR', 'Sunrisers Hyderabad': 'SRH', 
        'Rajasthan Royals': 'RR', 'Delhi Capitals': 'DC', 'Punjab Kings': 'PBKS', 'Lucknow Super Giants': 'LSG', 
        'Gujarat Titans': 'GT'
    }
    merged['Team_Code'] = merged['Team'].map(team_map).fillna("Free Agent")

    # Points & Price
    merged['Total_Points'] = merged[['bat_points', 'bowl_points']].max(axis=1) + (merged[['bat_points', 'bowl_points']].min(axis=1) * 0.3)
    merged['Rank'] = merged['Total_Points'].rank(ascending=False)

    def get_price(rank):
        if rank <= 1: return 30.0
        if rank <= 3: return 28.0 - rank * 0.5
        return min(30, 30 / (1 + 0.04 * (rank - 1)))

    merged['Market Value (Cr)'] = merged['Rank'].apply(get_price)
    merged['Role'] = np.where((merged['bat_points'] > 500) & (merged['bowl_points'] > 500), "All-Rounder",
                     np.where(merged['bat_points'] > merged['bowl_points'], "Batter", "Bowler"))

    return merged.sort_values("Market Value (Cr)", ascending=False)

# -------------------------------------------------
# APP UI
# -------------------------------------------------
df = load_data()
if df.empty: st.stop()

vals = calculate_valuation(df)

st.title("🏏 CricValue")

# --- CAROUSEL ---
st.subheader("🔥 Top 10 Market Movers")

cards_html = ""
for _, p in vals.head(10).iterrows():
    logo_url = get_team_logo(p['Team_Code'])
    cards_html += f"""
    <div class='hero-card'>
        <div class='player-header'>
            <div class='role-badge'>{p['Role']}</div>
            <img src='{logo_url}' width='40' height='40' style='object-fit: contain;'>
        </div>
        <div class='player-name'>{p['Player']}</div>
        <div style='font-size: 0.9rem; color: #888; margin-bottom: 5px;'>{p['Team_Code']}</div>
        <div class='price'>₹ {p['Market Value (Cr)']:.2f} Cr</div>
        
        <div class='stat-grid'>
            <div class='stat-item'>
                <span class='stat-label'>Runs</span>
                <span class='stat-val'>{int(p['Runs'])}</span>
            </div>
            <div class='stat-item'>
                <span class='stat-label'>SR</span>
                <span class='stat-val'>{p['Strike Rate']:.0f}</span>
            </div>
            <div class='stat-item'>
                <span class='stat-label'>Wkts</span>
                <span class='stat-val'>{int(p['Wickets'])}</span>
            </div>
            <div class='stat-item'>
                <span class='stat-label'>Eco</span>
                <span class='stat-val'>{p['Economy']:.2f}</span>
            </div>
        </div>
    </div>
    """

st.markdown(f"<div class='hero-scroll'>{cards_html}</div>", unsafe_allow_html=True)

# --- PROFILE ---
st.markdown("---")
st.subheader("🔎 Player Deep Dive")

player = st.selectbox("Select Player", vals['Player'].unique())

if player:
    p = vals[vals['Player'] == player].iloc[0]
    
    # Top Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Market Value", f"₹ {p['Market Value (Cr)']:.2f} Cr")
    c2.metric("Team", p['Team_Code'])
    c3.metric("Role", p['Role'])
    c4.metric("Impact Pts", f"{p['Total_Points']:.0f}")
    
    # Simple Stats
    st.caption("2024-2025 Performance")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Batting:** {int(p['Runs'])} Runs @ {p['Strike Rate']:.1f} SR")
    with col2:
        st.info(f"**Bowling:** {int(p['Wickets'])} Wkts @ {p['Economy']:.2f} Eco")
