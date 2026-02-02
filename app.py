import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="CricValue | Direct Edition",
    layout="wide",
    page_icon="🏏"
)

# -------------------------------------------------
# STYLES (UI ONLY)
# -------------------------------------------------
st.markdown("""
<style>
.stApp {
    background-color: #0E1117;
    color: #EAEAEA;
}

h1, h2, h3 {
    font-weight: 800;
    letter-spacing: -0.02em;
}

.hero-card {
    background: linear-gradient(160deg, #1f2437, #141625);
    border-radius: 24px;
    padding: 28px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
}

.price-tag {
    color: #4CAF50;
    font-weight: 900;
    font-size: 2.4rem;
    margin: 12px 0;
}

.role-badge {
    background: rgba(255,255,255,0.08);
    color: #ddd;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 0.8rem;
    display: inline-block;
}

.player-card {
    background: #161a2b;
    border-radius: 18px;
    padding: 16px;
    border: 1px solid rgba(255,255,255,0.06);
}

.stat-label {
    color: #9aa0b4;
    font-size: 0.7rem;
    text-transform: uppercase;
}

.stat-val {
    font-size: 1.1rem;
    font-weight: 700;
}

.divider {
    margin: 30px 0;
    border-top: 1px solid rgba(255,255,255,0.08);
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# DATA LOADING (UNCHANGED)
# -------------------------------------------------
@st.cache_data
def load_data():
    csv_file, zip_file = 'ipl_ball_by_ball_2008_2025.csv', 'data.zip'
    try:
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
        elif os.path.exists(zip_file):
            df = pd.read_csv(zip_file, compression='zip')
        else:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['year'] = df['date'].dt.year
        return df
    except:
        return pd.DataFrame()

# -------------------------------------------------
# VALUATION ENGINE (DO NOT TOUCH)
# -------------------------------------------------
@st.cache_data
def calculate_valuation(df, selected_year=None):
    if selected_year:
        df_sub = df[df['year'] == selected_year]
    else:
        df_sub = df[df['year'] >= 2024]

    if df_sub.empty:
        return pd.DataFrame()

    bat = df_sub.groupby('batter').agg(
        runs=('runs_off_bat', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique')
    ).reset_index()

    bat['sr'] = (bat['runs'] / bat['balls'].replace(0, 1)) * 100
    bat['bat_points'] = bat['runs'] * ((bat['sr'] / 100) ** 2) / 1.25
    bat = bat[bat['matches'] >= 3]

    bowl = df_sub.groupby('bowler').agg(
        wkts=('is_wicket', 'sum'),
        runs_con=('total_runs', 'sum'),
        balls=('ball', 'count'),
        matches=('match_id', 'nunique')
    ).reset_index()

    bowl['eco'] = (bowl['runs_con'] / bowl['balls'].replace(0, 1)) * 6
    bowl['bowl_points'] = bowl.apply(
        lambda x: (x['wkts'] * ((9.0 / max(4, x['eco'])) ** 2) * 35) if x['wkts'] > 0 else 0,
        axis=1
    )
    bowl = bowl[bowl['matches'] >= 3]

    bat = bat.rename(columns={'batter': 'Player'})
    bowl = bowl.rename(columns={'bowler': 'Player'})

    merged = pd.merge(
        bat[['Player', 'bat_points']],
        bowl[['Player', 'bowl_points']],
        on='Player',
        how='outer'
    ).fillna(0)

    merged['total_points'] = (
        merged[['bat_points', 'bowl_points']].max(axis=1) +
        (merged[['bat_points', 'bowl_points']].min(axis=1) * 0.3)
    )

    merged['rank'] = merged['total_points'].rank(ascending=False)

    def get_price(rank):
        if rank <= 1:
            return 30.0
        if rank <= 3:
            return 28.0 - (rank * 0.5)
        price = 30.0 / (1 + 0.04 * (rank - 1))
        return min(30.0, price)

    merged['Market_Value'] = merged['rank'].apply(get_price)

    merged['Role'] = merged.apply(
        lambda x: "All-Rounder" if (x['bat_points'] > 500 and x['bowl_points'] > 500)
        else ("Batter" if x['bat_points'] > x['bowl_points'] else "Bowler"),
        axis=1
    )

    return merged.sort_values('Market_Value', ascending=False)

# -------------------------------------------------
# APP START
# -------------------------------------------------
df_raw = load_data()
if df_raw.empty:
    st.error("No Data Found")
    st.stop()

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
with st.sidebar:
    st.title("🏏 CricValue")
    st.caption("Direct valuation from ball-by-ball data")

    mode = st.radio("Mode", ["Projection", "Historical"])
    sel_year = (
        st.selectbox("Season", sorted(df_raw['year'].unique(), reverse=True))
        if mode == "Historical" else None
    )

    show_table = st.checkbox("Show table view", value=False)

# -------------------------------------------------
# VALUATION
# -------------------------------------------------
vals = calculate_valuation(df_raw, sel_year)
top = vals.iloc[0]

# -------------------------------------------------
# HERO
# -------------------------------------------------
st.subheader(f"Market Valuation ({'Projection' if not sel_year else sel_year})")

c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    st.markdown(f"""
    <div class='hero-card'>
        <div style='color:#9aa0b4;'>Most Valuable Player</div>
        <div style='font-size:2rem;font-weight:800;'>{top['Player']}</div>
        <div class='price-tag'>₹ {top['Market_Value']:.2f} Cr</div>
        <div class='role-badge'>{top['Role']}</div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# FILTERS
# -------------------------------------------------
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

f1, f2 = st.columns([2, 1])
search = f1.text_input("Search player")
role_filter = f2.selectbox("Role", ["All", "Batter", "Bowler", "All-Rounder"])

filtered = vals.copy()
if search:
    filtered = filtered[filtered['Player'].str.contains(search, case=False)]
if role_filter != "All":
    filtered = filtered[filtered['Role'] == role_filter]

# -------------------------------------------------
# CARD VIEW (DEFAULT)
# -------------------------------------------------
if not show_table:
    cols = st.columns(4)
    for i, (_, row) in enumerate(filtered.head(40).iterrows()):
        with cols[i % 4]:
            st.markdown(f"""
            <div class='player-card'>
                <div style='font-weight:700;'>{row['Player']}</div>
                <div class='stat-label'>{row['Role']}</div>
                <div class='stat-val'>₹ {row['Market_Value']:.1f} Cr</div>
            </div>
            """, unsafe_allow_html=True)

# -------------------------------------------------
# TABLE VIEW (OPTIONAL)
# -------------------------------------------------
else:
    st.dataframe(
        filtered[['Player', 'Role', 'Market_Value', 'bat_points', 'bowl_points']],
        use_container_width=True,
        hide_index=True
    )