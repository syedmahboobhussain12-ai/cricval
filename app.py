import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np

# 1. PAGE CONFIG
st.set_page_config(page_title="CricValue | Pro Edition", layout="wide", page_icon="🏏")

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

# 3. VALUATION ENGINE (Squared Formula + Economic Caps)
@st.cache_data
def calculate_valuation(df, selected_year=None):
    # Filter Data
    if selected_year:
        df_sub = df[df['year'] == selected_year]
    else:
        df_sub = df[df['year'] >= 2024] # Recency
    
    if df_sub.empty: return pd.DataFrame()

    # --- BATTING: YOUR PREVIOUS FORMULA ---
    # Formula: Runs * (SR/100)^2 / 1.25
    bat = df_sub.groupby('batter').agg(
        runs=('runs_off_bat', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique')
    ).reset_index()
    
    bat['sr'] = (bat['runs'] / bat['balls'].replace(0, 1)) * 100
    bat['bat_points'] = bat['runs'] * ((bat['sr']/100)**2) / 1.25
    
    # Filter noise
    bat = bat[bat['matches'] >= 3]

    # --- BOWLING: YOUR PREVIOUS FORMULA ---
    # Formula: Wickets * (9.0/Eco)^2 * 35
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
    
    merged = pd.merge(bat[['Player', 'bat_points', 'runs', 'sr']], 
                      bowl[['Player', 'bowl_points', 'wkts', 'eco']], 
                      on='Player', how='outer').fillna(0)
    
    # --- NORMALIZATION (Crucial Step) ---
    # We convert raw points (e.g., 1200) into an Index (0.0 to 1.2)
    # This allows us to use the "Hockey Stick" price curve.
    
    # Benchmarks (approx elite season values)
    ELITE_BAT_PTS = 1200.0 
    ELITE_BOWL_PTS = 1200.0
    
    merged['idx_bat'] = merged['bat_points'] / ELITE_BAT_PTS
    merged['idx_bowl'] = merged['bowl_points'] / ELITE_BOWL_PTS
    
    # Combined Index: Max of Skill A + 30% of Skill B
    merged['pvi_index'] = merged[['idx_bat', 'idx_bowl']].max(axis=1) + (merged[['idx_bat', 'idx_bowl']].min(axis=1) * 0.3)
    
    # --- PRICING CURVE (Corrected Economics) ---
    # Exponential Curve: Base * exp(k * Index)
    # At Index 0.5 (Average) -> Price ~ 3 Cr
    # At Index 1.0 (Elite)   -> Price ~ 16 Cr
    # At Index 1.3 (God)     -> Price ~ 22 Cr
    
    merged['raw_price'] = 0.8 * np.exp(3.0 * merged['pvi_index'])
    
    # Hard Caps (League Reality)
    def apply_caps(row):
        price = row['raw_price']
        is_ar = (row['idx_bat'] > 0.35) and (row['idx_bowl'] > 0.35)
        
        if is_ar:
            return min(price, 24.0) # All-Rounder Premium Cap
        elif row['idx_bat'] > row['idx_bowl']:
            return min(price, 19.0) # Batter Cap
        else:
            return min(price, 19.0) # Bowler Cap
            
    merged['Market_Value'] = merged.apply(apply_caps, axis=1)
    merged['Role'] = merged.apply(lambda x: "All-Rounder" if (x['idx_bat'] > 0.35 and x['idx_bowl'] > 0.35) else ("Batter" if x['idx_bat'] > x['idx_bowl'] else "Bowler"), axis=1)

    return merged.sort_values('Market_Value', ascending=False)

# 4. APP UI
df_raw = load_data()
if df_raw.empty: st.error("No Data Found"); st.stop()

with st.sidebar:
    st.title("CricValue")
    st.caption("v10.0 | Squared Formula + Smart Caps")
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
            <div style='color:#888;'>Top Valuation</div>
            <div style='font-size:2rem; font-weight:bold; color:white;'>{top['Player']}</div>
            <div class='price-tag'>₹ {top['Market_Value']:.2f} Cr</div>
            <div class='role-badge'>{top['Role']}</div>
        </div>
        """, unsafe_allow_html=True)

# TABS
t1, t2, t3 = st.tabs(["📋 Rankings", "🔎 Profile", "📈 Distribution"])

with t1:
    st.dataframe(
        vals[['Player', 'Role', 'Market_Value', 'bat_points', 'bowl_points']],
        column_config={
            "Market_Value": st.column_config.NumberColumn("Price", format="₹ %.2f Cr"),
            "bat_points": st.column_config.ProgressColumn("Bat Points", format="%.0f", max_value=1500),
            "bowl_points": st.column_config.ProgressColumn("Bowl Points", format="%.0f", max_value=1500),
        },
        use_container_width=True,
        hide_index=True
    )

with t2:
    p_name = st.selectbox("Select Player for Deep Dive", sorted(vals['Player'].unique()))
    if p_name:
        p_res = vals[vals['Player'] == p_name].iloc[0]
        
        # Historical Data for Profile Chart
        hist_bat = df_raw[df_raw['batter'] == p_name].groupby('year')['runs_off_bat'].sum().reset_index()
        hist_bowl = df_raw[df_raw['bowler'] == p_name].groupby('year')['is_wicket'].sum().reset_index()
        
        st.markdown(f"## {p_name}")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='stat-box'><div class='stat-label'>Batting Score</div><div class='stat-val'>{p_res['bat_points']:.0f}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><div class='stat-label'>Bowling Score</div><div class='stat-val'>{p_res['bowl_points']:.0f}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box'><div class='stat-label'>Actual Runs</div><div class='stat-val'>{p_res['runs']:.0f}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat-box'><div class='stat-label'>Actual Wickets</div><div class='stat-val'>{p_res['wkts']:.0f}</div></div>", unsafe_allow_html=True)

        if not hist_bat.empty:
            st.markdown("### Career Trajectory (Runs)")
            chart = alt.Chart(hist_bat).mark_line(point=True, color='#4CAF50').encode(x='year:O', y='runs_off_bat:Q', tooltip=['year', 'runs_off_bat']).properties(height=250)
            st.altair_chart(chart, use_container_width=True)

with t3:
    st.markdown("### 📊 Price Curve Reality Check")
    chart = alt.Chart(vals).mark_circle(size=60).encode(
        x=alt.X('pvi_index', title='Impact Index (0-1.5)'),
        y=alt.Y('Market_Value', title='Valuation (Cr)'),
        color='Role',
        tooltip=['Player', 'Market_Value']
    ).interactive()
    st.altair_chart(chart, use_container_width=True)
