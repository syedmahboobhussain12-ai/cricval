import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np

# 1. PAGE CONFIG
st.set_page_config(page_title="CricValue | Corrected Economics", layout="wide", page_icon="⚖️")

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

# 3. VALUATION ENGINE (The Fix)
@st.cache_data
def calculate_valuation(df, selected_year=None):
    # Filter Data
    if selected_year:
        df_sub = df[df['year'] == selected_year]
    else:
        df_sub = df[df['year'] >= 2024] # Recency Bias
    
    if df_sub.empty: return pd.DataFrame()

    # --- BATTING PVI (0-1 Scale) ---
    bat = df_sub.groupby('batter').agg(
        runs=('runs_off_bat', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique'),
        fours=('runs_off_bat', lambda x: (x == 4).sum()),
        sixes=('runs_off_bat', lambda x: (x == 6).sum())
    ).reset_index()
    
    # Raw Metrics
    bat['sr'] = (bat['runs'] / bat['balls'].replace(0, 1)) * 100
    bat['rpm'] = bat['runs'] / bat['matches']
    bat['boundary_pct'] = ((bat['fours']*4 + bat['sixes']*6) / bat['runs'].replace(0, 1))
    
    # Normalization (Bounded 0 to 1)
    # We use "Elite Standards" as the denominator to scale players
    bat['norm_sr'] = (bat['sr'] / 180).clip(upper=1.0)        # Elite SR = 180
    bat['norm_rpm'] = (bat['rpm'] / 50).clip(upper=1.0)       # Elite RPM = 50
    bat['norm_bp'] = (bat['boundary_pct'] / 0.85).clip(upper=1.0) # Elite Boundary% = 85%
    
    # Batting PVI = 0.45(SR) + 0.35(RPM) + 0.20(BP)
    bat['pvi_bat'] = (0.45 * bat['norm_sr']) + (0.35 * bat['norm_rpm']) + (0.20 * bat['norm_bp'])
    
    # Filter: Remove noise (players with < 3 matches)
    bat = bat[bat['matches'] >= 3]

    # --- BOWLING PVI (0-1 Scale) ---
    # Smart "Pressure" Detection: Calculate Death Over usage naturally
    df_sub['over_num'] = df_sub['ball'].astype(int)
    death_overs = df_sub[df_sub['over_num'] >= 16]
    
    death_stats = death_overs.groupby('bowler')['ball'].count().reset_index().rename(columns={'ball':'death_balls'})
    
    bowl = df_sub.groupby('bowler').agg(
        wkts=('is_wicket', 'sum'),
        runs_con=('total_runs', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique'),
        dots=('total_runs', lambda x: (x == 0).sum())
    ).reset_index()
    
    bowl = pd.merge(bowl, death_stats, on='bowler', how='left').fillna(0)
    
    # Metrics
    bowl['wpm'] = bowl['wkts'] / bowl['matches']
    bowl['eco'] = (bowl['runs_con'] / bowl['balls'].replace(0, 1)) * 6
    bowl['dot_pct'] = bowl['dots'] / bowl['balls'].replace(0, 1)
    bowl['death_usage'] = bowl['death_balls'] / bowl['balls'].replace(0, 1)
    
    # Pressure Adjustment: For every 10% of balls bowled in death, allow Economy to be 0.5 higher
    # This removes the need for a "Role Multiplier" -> The data forgives their economy.
    bowl['adjusted_eco'] = bowl['eco'] - (bowl['death_usage'] * 5.0) 
    
    # Normalization
    bowl['norm_wpm'] = (bowl['wpm'] / 2.5).clip(upper=1.0) # Elite = 2.5 Wkts/Match
    bowl['norm_eco'] = ((12 - bowl['adjusted_eco']) / 7).clip(0, 1) # Elite Eco=5, Bad=12
    bowl['norm_dot'] = (bowl['dot_pct'] / 0.6).clip(upper=1.0) # Elite Dot% = 60%
    
    # Bowling PVI
    bowl['pvi_bowl'] = (0.4 * bowl['norm_wpm']) + (0.4 * bowl['norm_eco']) + (0.2 * bowl['norm_dot'])
    bowl = bowl[bowl['matches'] >= 3]

    # --- MERGE & PRICING ---
    bat = bat.rename(columns={'batter': 'Player'})
    bowl = bowl.rename(columns={'bowler': 'Player'})
    
    merged = pd.merge(bat[['Player', 'pvi_bat']], 
                      bowl[['Player', 'pvi_bowl']], 
                      on='Player', how='outer').fillna(0)
    
    # Total PVI: Primary Skill + 25% of Secondary Skill
    # This prevents linear stacking inflation
    merged['pvi_total'] = merged[['pvi_bat', 'pvi_bowl']].max(axis=1) + (merged[['pvi_bat', 'pvi_bowl']].min(axis=1) * 0.25)
    
    # Price Curve: Exponential (The "Hockey Stick" Curve)
    # Price = Base * e^(k * PVI)
    # Base = 0.5 Cr. At PVI=1.0 (Elite), Price ~18 Cr. 
    # Formula: 0.5 * exp(3.8 * PVI) -> 0.5 * 44 = ~22 Cr max
    merged['raw_price'] = 0.5 * np.exp(3.8 * merged['pvi_total'])
    
    # Role Logic & Hard Caps
    def apply_caps(row):
        is_ar = (row['pvi_bat'] > 0.4) and (row['pvi_bowl'] > 0.4)
        price = row['raw_price']
        
        # Caps
        if is_ar:
            return min(price, 22.0) # All-Rounder Cap
        else:
            return min(price, 18.0) # Specialist Cap
            
    merged['Market_Value'] = merged.apply(apply_caps, axis=1)
    merged['Role'] = merged.apply(lambda x: "All-Rounder" if (x['pvi_bat'] > 0.4 and x['pvi_bowl'] > 0.4) else ("Batter" if x['pvi_bat'] > x['pvi_bowl'] else "Bowler"), axis=1)

    return merged.sort_values('Market_Value', ascending=False)

# 4. APP UI
df_raw = load_data()
if df_raw.empty: st.error("Please upload data."); st.stop()

with st.sidebar:
    st.title("CricValue")
    st.caption("v9.0 | Corrected Economics")
    mode = st.radio("Mode", ["Projection", "Historical"])
    sel_year = st.selectbox("Season", sorted(df_raw['year'].unique(), reverse=True)) if mode == "Historical" else None

vals = calculate_valuation(df_raw, sel_year)

# UI RENDER
st.subheader("💰 Fair Value Estimates (Capped & Normalized)")

# Hero Section
if not vals.empty:
    top = vals.iloc[0]
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

# Tabs
t1, t2 = st.tabs(["📋 Valuation Table", "🔎 Logic Check"])

with t1:
    st.dataframe(
        vals[['Player', 'Role', 'Market_Value', 'pvi_total', 'pvi_bat', 'pvi_bowl']],
        column_config={
            "Market_Value": st.column_config.NumberColumn("Price", format="₹ %.2f Cr"),
            "pvi_total": st.column_config.ProgressColumn("PVI (Index)", min_value=0, max_value=1.5),
            "pvi_bat": st.column_config.NumberColumn("Bat Score", format="%.2f"),
            "pvi_bowl": st.column_config.NumberColumn("Bowl Score", format="%.2f"),
        },
        use_container_width=True,
        hide_index=True
    )

with t2:
    st.markdown("### 📊 Price Distribution")
    st.caption("Notice how most players are < 5 Cr (left), and only elites spike (right). This is the exponential curve working.")
    
    chart = alt.Chart(vals).mark_circle(size=60).encode(
        x=alt.X('pvi_total', title='Performance Index (0-1)'),
        y=alt.Y('Market_Value', title='Price (Cr)'),
        color='Role',
        tooltip=['Player', 'Market_Value', 'pvi_total']
    ).interactive()
    st.altair_chart(chart, use_container_width=True)
