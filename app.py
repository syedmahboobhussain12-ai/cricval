import streamlit as st
import pandas as pd
import altair as alt
import base64
import os
import numpy as np

# 1. PAGE CONFIG
st.set_page_config(page_title="CricValue | Pure Data Edition", layout="wide", page_icon="🏏")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .hero-card { background: linear-gradient(145deg, #1e2130, #161822); border-radius: 20px; padding: 20px; text-align: center; border: 1px solid #444; }
    .price-tag { color: #4CAF50; font-weight: 900; font-size: 2.2rem; margin: 10px 0; }
    .stat-box { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; margin-bottom: 10px; }
    .stat-label { color: #888; font-size: 0.8rem; text-transform: uppercase; }
    .stat-val { color: #fff; font-size: 1.2rem; font-weight: bold; }
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

# 3. PURE DATA VALUATION ENGINE (New Formula)
@st.cache_data
def calculate_pure_valuation(df, selected_year=None):
    # Filter by Year
    if selected_year:
        df_sub = df[df['year'] == selected_year]
    else:
        df_sub = df[df['year'] >= 2024]
    
    if df_sub.empty: return pd.DataFrame()

    # --- BATTING INDEX ---
    bat = df_sub.groupby('batter').agg(
        runs=('runs_off_bat', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique'),
        fours=('runs_off_bat', lambda x: (x == 4).sum()),
        sixes=('runs_off_bat', lambda x: (x == 6).sum())
    ).reset_index()
    
    bat['sr'] = (bat['runs'] / bat['balls'].replace(0, 1)) * 100
    bat['rpm'] = bat['runs'] / bat['matches']
    bat['boundary_pct'] = ((bat['fours']*4 + bat['sixes']*6) / bat['runs'].replace(0, 1))
    
    # Normalize for Index (0-100 scale)
    bat['sr_idx'] = (bat['sr'] / 200).clip(upper=1) * 100
    bat['rpm_idx'] = (bat['rpm'] / 60).clip(upper=1) * 100
    bat['b_pct_idx'] = (bat['boundary_pct'] / 0.8).clip(upper=1) * 100
    
    # Formula: 0.45(SR) + 0.35(RPM) + 0.20(B%)
    bat['perf_score'] = (0.45 * bat['sr_idx']) + (0.35 * bat['rpm_idx']) + (0.20 * bat['b_pct_idx'])

    # --- BOWLING INDEX ---
    bowl = df_sub.groupby('bowler').agg(
        wkts=('is_wicket', 'sum'),
        runs_con=('total_runs', 'sum'),
        balls_bowled=('ball', 'count'),
        matches=('match_id', 'nunique'),
        dots=('total_runs', lambda x: (x == 0).sum())
    ).reset_index()
    
    bowl['wpm'] = bowl['wkts'] / bowl['matches']
    bowl['eco'] = (bowl['runs_con'] / bowl['balls_bowled'].replace(0, 1)) * 6
    bowl['dot_pct'] = bowl['dots'] / bowl['balls_bowled'].replace(0, 1)
    
    # Normalize
    bowl['wpm_idx'] = (bowl['wpm'] / 3).clip(upper=1) * 100
    bowl['eco_inv_idx'] = (1 - (bowl['eco'] / 15)).clip(lower=0) * 100
    bowl['dot_idx'] = (bowl['dot_pct'] / 0.5).clip(upper=1) * 100
    
    # Formula: 0.4(WPM) + 0.4(Eco) + 0.2(Dot%)
    bowl['perf_score'] = (0.4 * bowl['wpm_idx']) + (0.4 * bowl['eco_inv_idx']) + (0.2 * bowl['dot_idx'])

    # --- ROLE MULTIPLIERS ---
    # Scarcity derived from overs
    df_sub['over_num'] = (df_sub['ball'].astype(int))
    
    death_bowlers = df_sub[df_sub['over_num'] >= 16]['bowler'].unique()
    pp_bowlers = df_sub[df_sub['over_num'] <= 6]['bowler'].unique()
    
    # --- MERGE & PRICING ---
    bat = bat.rename(columns={'batter': 'Player'})
    bowl = bowl.rename(columns={'bowler': 'Player'})
    
    merged = pd.merge(bat[['Player', 'perf_score', 'runs', 'sr']], 
                      bowl[['Player', 'perf_score', 'wkts', 'eco']], 
                      on='Player', how='outer', suffixes=('_bat', '_bowl')).fillna(0)
    
    # Final Multiplier Logic
    def calculate_price(row):
        base = 3.0 # Default Batter Base
        mult = 1.0
        
        # Scarcity Check
        if row['perf_score_bat'] > 10 and row['perf_score_bowl'] > 10: 
            base = 5.0; mult = 1.35 # All Rounder
        elif row['perf_score_bowl'] > row['perf_score_bat']:
            base = 3.5 # Bowler Base
            if row['Player'] in death_bowlers: mult = 1.25
            elif row['Player'] in pp_bowlers: mult = 1.15
        else:
            if row['sr'] > 160: mult = 1.3 # Finisher
        
        score = max(row['perf_score_bat'], row['perf_score_bowl'])
        val = base + (score * 0.25 * mult)
        return min(32.0, val)

    merged['Market_Value'] = merged.apply(calculate_price, axis=1)
    merged['Role'] = merged.apply(lambda x: "All-Rounder" if x['perf_score_bat'] > 20 and x['perf_score_bowl'] > 20 else ("Batter" if x['perf_score_bat'] > x['perf_score_bowl'] else "Bowler"), axis=1)
    
    return merged.sort_values('Market_Value', ascending=False)

# 4. APP RENDER
df_raw = load_data()
if df_raw.empty: st.error("No Data Found"); st.stop()

with st.sidebar:
    st.title("CricValue Pro")
    mode = st.radio("Valuation Mode", ["2025 Market Projection", "Historical Season"])
    sel_year = st.selectbox("Year", sorted(df_raw['year'].unique(), reverse=True)) if mode == "Historical Season" else None

vals = calculate_pure_valuation(df_raw, sel_year)

# TABS
t1, t2, t3 = st.tabs(["📋 Rankings", "📈 Clusters", "🔎 Profile Deep-Dive"])

with t1:
    st.dataframe(vals[['Player', 'Role', 'Market_Value', 'perf_score_bat', 'perf_score_bowl']], use_container_width=True, hide_index=True)

with t3:
    p_name = st.selectbox("Select Player", sorted(vals['Player'].unique()))
    if p_name:
        p_res = vals[vals['Player'] == p_name].iloc[0]
        st.markdown(f"## {p_name}")
        
        # KEY VALUATION
        st.markdown(f"<div class='hero-card'><div class='stat-label'>Data-Driven Valuation</div><div class='price-tag'>₹ {p_res['Market_Value']:.2f} Cr</div></div>", unsafe_allow_html=True)
        
        # CAREER BREAKDOWN
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='stat-box'><div class='stat-label'>Batting Index</div><div class='stat-val'>{p_res['perf_score_bat']:.1f}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><div class='stat-label'>Bowling Index</div><div class='stat-val'>{p_res['perf_score_bowl']:.1f}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box'><div class='stat-label'>Role</div><div class='stat-val'>{p_res['Role']}</div></div>", unsafe_allow_html=True)

        # Career History
        hist_bat = df_raw[df_raw['batter'] == p_name].groupby('year')['runs_off_bat'].sum().reset_index()
        hist_bowl = df_raw[df_raw['bowler'] == p_name].groupby('year')['is_wicket'].sum().reset_index()
        
        st.markdown("### Career Progression")
        hist_chart = alt.Chart(hist_bat).mark_line(point=True).encode(x='year:O', y='runs_off_bat:Q', tooltip=['year', 'runs_off_bat']).properties(height=250)
        st.altair_chart(hist_chart, use_container_width=True)
