import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np

# 1. PAGE CONFIG
st.set_page_config(page_title="CricValue | Direct Edition", layout="wide", page_icon="🏏")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .hero-card { background: linear-gradient(145deg, #1e2130, #161822); border-radius: 20px; padding: 20px; text-align: center; border: 1px solid #444; margin-bottom: 20px; }
    .price-tag { color: #4CAF50; font-weight: 900; font-size: 2.2rem; margin: 10px 0; }
    .stat-box { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; margin-bottom: 10px; }
    .stat-label { color: #888; font-size: 0.8rem; text-transform: uppercase; }
    .stat-val { color: #fff; font-size: 1.2rem; font-weight: bold; }
    .role-badge { background-color: #333; color: #ccc; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# 2. DATA LOADING
@st.cache_data
def load_data():
    csv_file, zip_file = 'ipl_ball_by_ball_2008_2025.csv', 'data.zip'
    try:
        if os.path.exists(csv_file): df = pd.read_csv(csv_file)
        elif os.path.exists(zip_file): df = pd.read_csv(zip_file, compression='zip')
        else: return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['year'] = df['date'].dt.year
        return df
    except: return pd.DataFrame()

# 3. VALUATION ENGINE (Direct Formula + 30Cr Cap)
@st.cache_data
def calculate_valuation(df, selected_year=None):
    # Filter Data
    if selected_year:
        df_sub = df[df['year'] == selected_year]
    else:
        df_sub = df[df['year'] >= 2024] # Recency Bias (Last 2 years)
    
    if df_sub.empty: return pd.DataFrame()

    # --- BATTING: Runs * (SR/100)^2 / 1.25 ---
    bat = df_sub.groupby('batter').agg(
        runs=('runs_off_bat', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique')
    ).reset_index()
    
    bat['sr'] = (bat['runs'] / bat['balls'].replace(0, 1)) * 100
    bat['bat_points'] = bat['runs'] * ((bat['sr']/100)**2) / 1.25
    bat = bat[bat['matches'] >= 3] # Filter noise

    # --- BOWLING: Wickets * (9.0/Eco)^2 * 35 ---
    bowl = df_sub.groupby('bowler').agg(
        wkts=('is_wicket', 'sum'),
        runs_con=('total_runs', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique')
    ).reset_index()
    
    bowl['eco'] = (bowl['runs_con'] / bowl['balls'].replace(0, 1)) * 6
    bowl['bowl_points'] = bowl.apply(lambda x: (x['wkts'] * ((9.0/max(4, x['eco']))**2) * 35) if x['wkts'] > 0 else 0, axis=1)
    bowl = bowl[bowl['matches'] >= 3]

    # --- MERGE ---
    bat = bat.rename(columns={'batter': 'Player'})
    bowl = bowl.rename(columns={'bowler': 'Player'})
    
    merged = pd.merge(bat[['Player', 'bat_points']], 
                      bowl[['Player', 'bowl_points']], 
                      on='Player', how='outer').fillna(0)
    
    # Total Impact Score
    merged['total_points'] = merged[['bat_points', 'bowl_points']].max(axis=1) + (merged[['bat_points', 'bowl_points']].min(axis=1) * 0.3)
    
    # --- PRICING LOGIC (Max 30 Cr) ---
    # We rank players. Rank 1 gets 30 Cr.
    # The price drops based on rank.
    merged['rank'] = merged['total_points'].rank(ascending=False)
    
    def get_price(rank):
        # Top 3 get special status
        if rank <= 1: return 30.0
        if rank <= 3: return 28.0 - (rank * 0.5)
        
        # Everyone else follows a standard decay curve
        # Rank 10 ~ 24 Cr, Rank 50 ~ 10 Cr
        price = 30.0 / (1 + 0.04 * (rank - 1))
        return min(30.0, price)

    merged['Market_Value'] = merged['rank'].apply(get_price)
    
    # Role Assignment
    merged['Role'] = merged.apply(lambda x: "All-Rounder" if (x['bat_points'] > 500 and x['bowl_points'] > 500) else ("Batter" if x['bat_points'] > x['bowl_points'] else "Bowler"), axis=1)

    return merged.sort_values('Market_Value', ascending=False)

# 4. APP UI
df_raw = load_data()
if df_raw.empty: st.error("No Data Found"); st.stop()

with st.sidebar:
    st.title("CricValue")
    st.caption("v11.0 | Direct Formula | 30Cr Cap")
    mode = st.radio("Mode", ["Projection", "Historical"])
    sel_year = st.selectbox("Season", sorted(df_raw['year'].unique(), reverse=True)) if mode == "Historical" else None

vals = calculate_valuation(df_raw, sel_year)

# HERO SECTION
if not vals.empty:
    top = vals.iloc[0]
    st.subheader(f"💰 Market Valuation ({'Projection' if not sel_year else sel_year})")
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown(f"""
        <div class='hero-card'>
            <div style='color:#888;'>Most Valuable Player</div>
            <div style='font-size:2rem; font-weight:bold; color:white;'>{top['Player']}</div>
            <div class='price-tag'>₹ {top['Market_Value']:.2f} Cr</div>
            <div class='role-badge'>{top['Role']}</div>
        </div>
        """, unsafe_allow_html=True)

# TABS
t1, t2 = st.tabs(["📋 Rankings", "🔎 Deep Career Profile"])

with t1:
    st.dataframe(
        vals[['Player', 'Role', 'Market_Value', 'bat_points', 'bowl_points']],
        column_config={
            "Market_Value": st.column_config.NumberColumn("Price", format="₹ %.2f Cr"),
            "bat_points": st.column_config.ProgressColumn("Bat Points", format="%.0f", max_value=2000),
            "bowl_points": st.column_config.ProgressColumn("Bowl Points", format="%.0f", max_value=2000),
        },
        use_container_width=True,
        hide_index=True
    )

with t2:
    # PLAYER SELECTION
    player_list = sorted(df_raw['batter'].unique().tolist() + df_raw['bowler'].unique().tolist())
    player_list = sorted(list(set(player_list)))
    p_name = st.selectbox("Select Player to view Full Career Stats", player_list)
    
    if p_name:
        st.markdown(f"## {p_name} - Career Analysis (2008-2025)")
        
        # 1. GET ALL CAREER DATA
        p_bat = df_raw[df_raw['batter'] == p_name]
        p_bowl = df_raw[df_raw['bowler'] == p_name]
        
        # Batting Totals
        total_runs = p_bat['runs_off_bat'].sum()
        total_balls = p_bat['ball'].count()
        avg_sr = (total_runs / total_balls * 100) if total_balls > 0 else 0
        matches_played = p_bat['match_id'].nunique()
        
        # Bowling Totals
        total_wkts = p_bowl['is_wicket'].sum()
        total_runs_con = p_bowl['total_runs'].sum()
        total_balls_bowled = p_bowl['ball'].count()
        career_eco = (total_runs_con / total_balls_bowled * 6) if total_balls_bowled > 0 else 0
        
        # Display Totals
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='stat-box'><div class='stat-label'>Total Runs</div><div class='stat-val'>{total_runs}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><div class='stat-label'>Career SR</div><div class='stat-val'>{avg_sr:.1f}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box'><div class='stat-label'>Total Wickets</div><div class='stat-val'>{total_wkts}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat-box'><div class='stat-label'>Career Eco</div><div class='stat-val'>{career_eco:.2f}</div></div>", unsafe_allow_html=True)
        
        # 2. SEASON BY SEASON BREAKDOWN
        st.markdown("### 📅 Season-by-Season Breakdown")
        
        # Batting by Year
        bat_yr = p_bat.groupby('year').agg(
            Runs=('runs_off_bat', 'sum'),
            Balls=('ball', 'count')
        ).reset_index()
        bat_yr['Strike Rate'] = (bat_yr['Runs'] / bat_yr['Balls'] * 100).round(1)
        
        # Bowling by Year
        bowl_yr = p_bowl.groupby('year').agg(
            Wickets=('is_wicket', 'sum'),
            Runs_Con=('total_runs', 'sum'),
            Balls=('ball', 'count')
        ).reset_index()
        bowl_yr['Economy'] = (bowl_yr['Runs_Con'] / bowl_yr['Balls'] * 6).round(2)
        
        # Merge
        season_stats = pd.merge(bat_yr, bowl_yr, on='year', how='outer').fillna(0)
        season_stats = season_stats.sort_values('year', ascending=False)
        
        # Clean Table for Display
        season_stats['year'] = season_stats['year'].astype(str)
        st.dataframe(
            season_stats[['year', 'Runs', 'Strike Rate', 'Wickets', 'Economy']],
            use_container_width=True,
            hide_index=True
        )
        
        # 3. CHART
        st.markdown("### Performance Trend")
        chart_data = season_stats[['year', 'Runs', 'Wickets']].melt('year', var_name='Metric', value_name='Value')
        c = alt.Chart(chart_data).mark_line(point=True).encode(
            x='year', 
            y='Value', 
            color='Metric',
            tooltip=['year', 'Metric', 'Value']
        ).interactive()
        st.altair_chart(c, use_container_width=True)
