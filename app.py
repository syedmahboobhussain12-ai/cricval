
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
    page_title="CricValue | Direct Edition",
    layout="wide",
    page_icon="🏏"
)

# -------------------------------------------------
# STYLES
# -------------------------------------------------
st.markdown("""
<style>
.stApp { background-color: #0E1117; color: #EAEAEA; }

.hero-scroll {
    display: flex;
    overflow-x: auto;
    gap: 16px;
    padding-bottom: 10px;
}

.hero-card {
    min-width: 260px;
    background: linear-gradient(160deg, #1f2437, #141625);
    border-radius: 22px;
    padding: 18px;
    border: 1px solid rgba(255,255,255,0.08);
}

.player-name {
    font-size: 1.1rem;
    font-weight: 800;
}

.price {
    color: #4CAF50;
    font-weight: 900;
    font-size: 1.4rem;
}

.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-top: 10px;
}

.stat {
    font-size: 0.8rem;
    color: #bbb;
}

.badge {
    background: rgba(255,255,255,0.08);
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.7rem;
    display: inline-block;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# TEAM LOGOS (WIKIMEDIA PRIMARY)
# -------------------------------------------------
TEAM_LOGOS = {
    "CSK": "https://upload.wikimedia.org/wikipedia/en/2/2b/Chennai_Super_Kings_Logo.svg",
    "MI": "https://upload.wikimedia.org/wikipedia/en/c/cd/Mumbai_Indians_Logo.svg",
    "RCB": "https://upload.wikimedia.org/wikipedia/en/9/9a/Royal_Challengers_Bangalore_Logo.svg",
    "KKR": "https://upload.wikimedia.org/wikipedia/en/4/4c/Kolkata_Knight_Riders_Logo.svg",
    "RR": "https://upload.wikimedia.org/wikipedia/en/6/60/Rajasthan_Royals_Logo.svg",
    "DC": "https://upload.wikimedia.org/wikipedia/en/2/2f/Delhi_Capitals_Logo.svg",
    "SRH": "https://upload.wikimedia.org/wikipedia/en/8/81/Sunrisers_Hyderabad.svg",
    "PBKS": "https://upload.wikimedia.org/wikipedia/en/d/d4/Punjab_Kings_Logo.svg",
    "LSG": "https://upload.wikimedia.org/wikipedia/en/6/6d/Lucknow_Super_Giants_Logo.svg",
    "GT": "https://upload.wikimedia.org/wikipedia/en/0/09/Gujarat_Titans_Logo.svg",
}

@st.cache_data
def get_team_logo(team):
    wiki = TEAM_LOGOS.get(team)
    local = Path(f"assets/{team}.png")

    if wiki:
        try:
            if requests.head(wiki, timeout=2).status_code == 200:
                return wiki
        except:
            pass

    if local.exists():
        return str(local)

    return None

# -------------------------------------------------
# DATA LOADER (FIXED FOR data.zip)
# -------------------------------------------------
@st.cache_data
def load_data():
    if not os.path.exists("data.zip"):
        st.error("data.zip not found in project root")
        return pd.DataFrame()

    df = pd.read_csv("data.zip", compression="zip")

    df['date'] = pd.to_datetime(df.get('date'), errors='coerce')
    df['year'] = df['date'].dt.year

    return df

# -------------------------------------------------
# VALUATION ENGINE (UNCHANGED)
# -------------------------------------------------
@st.cache_data
def calculate_valuation(df):
    df = df[df['year'] >= 2024]

    bat = df.groupby('batter').agg(
        Runs=('runs_off_bat', 'sum'),
        Balls=('ball', 'count'),
        Matches=('match_id', 'nunique')
    ).reset_index()

    bat['Strike Rate'] = (bat['Runs'] / bat['Balls']) * 100
    bat['bat_points'] = bat['Runs'] * ((bat['Strike Rate'] / 100) ** 2) / 1.25
    bat = bat[bat['Matches'] >= 3]

    bowl = df.groupby('bowler').agg(
        Wickets=('is_wicket', 'sum'),
        Runs_Conceded=('total_runs', 'sum'),
        Balls=('ball', 'count'),
        Matches=('match_id', 'nunique')
    ).reset_index()

    bowl['Economy'] = (bowl['Runs_Conceded'] / bowl['Balls']) * 6
    bowl['bowl_points'] = bowl.apply(
        lambda x: (x['Wickets'] * ((9.0 / max(4, x['Economy'])) ** 2) * 35)
        if x['Wickets'] > 0 else 0,
        axis=1
    )
    bowl = bowl[bowl['Matches'] >= 3]

    bat = bat.rename(columns={'batter': 'Player'})
    bowl = bowl.rename(columns={'bowler': 'Player'})

    merged = pd.merge(bat, bowl, on='Player', how='outer').fillna(0)

    merged['Total_Points'] = (
        merged[['bat_points', 'bowl_points']].max(axis=1)
        + merged[['bat_points', 'bowl_points']].min(axis=1) * 0.3
    )

    merged['Rank'] = merged['Total_Points'].rank(ascending=False)

    def get_price(rank):
        if rank <= 1: return 30.0
        if rank <= 3: return 28.0 - rank * 0.5
        return min(30, 30 / (1 + 0.04 * (rank - 1)))

    merged['Market Value (Cr)'] = merged['Rank'].apply(get_price)

    merged['Role'] = np.where(
        (merged['bat_points'] > 500) & (merged['bowl_points'] > 500),
        "All-Rounder",
        np.where(merged['bat_points'] > merged['bowl_points'], "Batter", "Bowler")
    )

    return merged.sort_values("Market Value (Cr)", ascending=False)

# -------------------------------------------------
# APP START
# -------------------------------------------------
df = load_data()
if df.empty:
    st.stop()

vals = calculate_valuation(df)

st.title("🏏 CricValue – Market Board")

# -------------------------------------------------
# TOP 10 SWIPE CARDS
# -------------------------------------------------
st.subheader("Top 10 Valued Players")

st.markdown("<div class='hero-scroll'>", unsafe_allow_html=True)

for _, p in vals.head(10).iterrows():
    team = "CSK"  # placeholder
    logo = get_team_logo(team)
    logo_html = f"<img src='{logo}' width='36'>" if logo else ""

    st.markdown(f"""
    <div class='hero-card'>
        {logo_html}
        <div class='player-name'>{p['Player']}</div>
        <div class='price'>₹ {p['Market Value (Cr)']:.1f} Cr</div>
        <div class='badge'>{p['Role']}</div>

        <div class='stat-grid'>
            <div class='stat'>Runs: {int(p['Runs'])}</div>
            <div class='stat'>SR: {p['Strike Rate']:.1f}</div>
            <div class='stat'>Wkts: {int(p['Wickets'])}</div>
            <div class='stat'>Eco: {p['Economy']:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# PLAYER PROFILE
# -------------------------------------------------
st.subheader("Player Profile")

player = st.selectbox("Select Player", vals['Player'].unique())
p = vals[vals['Player'] == player].iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Market Value", f"₹ {p['Market Value (Cr)']:.1f} Cr")
c2.metric("Role", p['Role'])
c3.metric("Runs", int(p['Runs']))
c4.metric("Strike Rate", f"{p['Strike Rate']:.1f}")
c5.metric("Wickets", int(p['Wickets']))