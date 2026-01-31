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
    
    /* Hero Card Styling */
    .hero-card {
        background: linear-gradient(145deg, #1e2130, #161822);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        border: 1px solid #444;
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
        margin-bottom: 20px;
    }
    
    /* Typography */
    .player-name { color: white; margin: 5px 0; font-size: 1.6rem; font-weight: 700; }
    .value-label { color: #888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; margin-top: 15px; }
    .price-tag { color: #4CAF50; font-weight: 900; font-size: 2.2rem; line-height: 1; }
    .role-badge { background-color: #333; color: #ccc; padding: 5px 15px; border-radius: 15px; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 10px; display: inline-block; }
    
    /* Stat Box */
    .stat-box { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; }
    .stat-label { color: #888; font-size: 0.9rem; }
    .stat-val { color: #fff; font-size: 1.4rem; font-weight: bold; }
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

def get_img_as_base64(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        pass
    return None

def get_team_logo(team_code):
    local_logo = get_img_as_base64(f"assets/{team_code}.png")
    if local_logo: return local_logo
    return ONLINE_LOGOS.get(team_code, ONLINE_LOGOS['Free Agent'])

# 3. SMART FILE HUNTER
@st.cache_data
def load_data_smart():
    files_present = []
    for root, dirs, files in os.walk("."):
        for filename in files:
            files_present.append(os.path.join(root, filename))
    
    target_file = None
    file_type = None
    
    # Priority 1: Check for known zip names
    for f in files_present:
        if f.endswith("data.zip"):
            target_file = f
            file_type = 'zip'
            break
            
    # Priority 2: Check for known csv names
    if not target_file:
        for f in files_present:
            if "ipl_ball" in f and f.endswith(".csv"):
                target_file = f
                file_type = 'csv'
                break
    
    if not target_file:
        st.error(f"❌ CRITICAL ERROR: Could not find 'data.zip' or the CSV file anywhere.")
        return pd.DataFrame()

    try:
        if file_type == 'zip':
            df = pd.read_csv(target_file, compression='zip')
        else:
            df = pd.read_csv(target_file)
            
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['year'] = df['date'].dt.year
        return df
    except Exception as e:
        st.error(f"Error reading {target_file}: {e}")
        return pd.DataFrame()

# 4. VALUATION LOGIC
@st.cache_data
def calculate_vals(df, selected_year=None):
    if df.empty: return pd.DataFrame()

    if selected_year:
        df_subset = df[df['year'] == selected_year]
        latest_year = selected_year
    else:
        df_subset = df[df['year'] >= 2024]
        latest_year = 2025

    if df_subset.empty: return pd.DataFrame()

    df_sorted = df.sort_values('date')
    last_team_bat = df_sorted.groupby('batter')['batting_team'].last()
    last_team_bowl = df_sorted.groupby('bowler')['bowling_team'].last()
    last_team = pd.concat([last_team_bat, last_team_bowl]).groupby(level=0).last()
    
    last_active = pd.concat([
        df.groupby('batter')['year'].max(), 
        df.groupby('bowler')['year'].max()
    ]).groupby(level=0).max()

    matches = df_subset.groupby(['year', 'batter'])['match_id'].nunique().reset_index()
    max_matches = df_subset.groupby('year')['match_id'].nunique().max()
    availability = matches.groupby('batter')['match_id'].mean().reset_index()
    availability.columns = ['Player', 'avg_matches']
    availability['avail_score'] = (availability['avg_matches'] / max_matches).clip(upper=1.0)

    bat = df_subset.groupby('batter').agg(runs=('runs_off_bat', 'sum'), balls=('ball', 'count')).reset_index()
    bat.columns = ['Player', 'bat_runs', 'bat_balls'] 
    bat['sr'] = (bat['bat_runs'] / bat['bat_balls'].replace(0, 1)) * 100
    bat['bat_points'] = bat['bat_runs'] * ((bat['sr']/100)**2) / 1.25

    bowl = df_subset.groupby('bowler').agg(wkts=('is_wicket', 'sum'), runs=('total_runs', 'sum'), balls=('ball', 'count')).reset_index()
    bowl.columns = ['Player', 'bowl_wkts', 'bowl_runs', 'bowl_balls']
    bowl['eco'] = (bowl['bowl_runs'] / bowl['bowl_balls'].replace(0, 1)) * 6
    bowl['bowl_points'] = bowl.apply(lambda x: (x['bowl_wkts'] * ((9.0/max(4, x['eco']))**2) * 35) if x['bowl_wkts'] > 0 else 0, axis=1)

    merged = pd.merge(bat, bowl, on='Player', how='outer').fillna(0)
    merged = pd.merge(merged, availability, on='Player', how='left').fillna(0)
    merged['Team'] = merged['Player'].map(last_team).fillna("Free Agent")
    merged['last_active'] = merged['Player'].map(last_active).fillna(2008)
    
    if not selected_year:
        merged['avail_score'] = np.where(merged['last_active'] < latest_year, 0, merged['avail_score'])
    
    merged['perf_points'] = merged.apply(lambda x: max(x['bat_points'], x['bowl_points']) + (min(x['bat_points'], x['bowl_points']) * 0.4), axis=1)
    merged['adjusted_score'] = merged['perf_points'] * (1 + (merged['avail_score'] * 0.10))
    merged['rank'] = merged['adjusted_score'].rank(ascending=False)
    
    def get_price(rank):
        if rank <= 3: return 28.0 + (3-rank)
        price = 35.0 / (1 + 0.045 * rank)
        return min(35.0, price)
    
    merged['Market_Value'] = merged['rank'].apply(get_price)
    
    def get_role(row):
        if row['bat_points'] > 50 and row['bowl_points'] > 50: return "All-Rounder"
        if row['bat_points'] > row['bowl_points']: return "Batter"
        return "Bowler"
    merged['Role'] = merged.apply(get_role, axis=1)

    team_map = {
        'Chennai Super Kings': 'CSK', 'Mumbai Indians': 'MI', 'Royal Challengers Bangalore': 'RCB', 'Royal Challengers Bengaluru': 'RCB',
        'Kolkata Knight Riders': 'KKR', 'Sunrisers Hyderabad': 'SRH', 'Rajasthan Royals': 'RR',
        'Delhi Capitals': 'DC', 'Delhi Daredevils': 'DC', 'Punjab Kings': 'PBKS', 'Kings XI Punjab': 'PBKS',
        'Lucknow Super Giants': 'LSG', 'Gujarat Titans': 'GT'
    }
    merged['Team_Code'] = merged['Team'].map(team_map).fillna(merged['Team'])
    
    return merged.sort_values('Market_Value', ascending=False)

# 5. EXECUTION & SIDEBAR
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1018/1018663.png", width=60)
    st.title("CricValue")
    st.caption("v9.2 | Mega Hero")
    st.markdown("---")
    
    df_main = load_data_smart()
    
    mode = st.radio("📊 Analysis Mode", ["Projected Market Value", "Historical Season"])
    
    selected_year = None
    if mode == "Historical Season" and not df_main.empty:
        years = sorted(df_main['year'].dropna().unique().astype(int), reverse=True)
        selected_year = st.selectbox("Select Season", years)

    st.markdown("### 🔍 Filters")
    role_filter = st.multiselect("Role", ["Batter", "Bowler", "All-Rounder"], default=["Batter", "Bowler", "All-Rounder"])
    team_filter = st.multiselect("Team", sorted(list(ONLINE_LOGOS.keys())))

# 6. RUN ENGINE
if df_main.empty:
    st.stop()

vals = calculate_vals(df_main, selected_year)

vals = vals[vals['Role'].isin(role_filter)]
if team_filter:
    vals = vals[vals['Team_Code'].isin(team_filter)]

# 7. UI RENDER
if mode == "Projected Market Value":
    # --- FIXED HEADER ---
    st.subheader("Mega Hero") 
else:
    st.subheader(f"🗓️ Season Analysis: {selected_year}")

# HERO PODIUM
if not vals.empty:
    top_3 = vals.head(3).reset_index(drop=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    def render_card(col, p, medal, color):
        logo = get_team_logo(p['Team_Code'])
        
        # --- FIXED HTML FORMATTING (Removed extra indentations) ---
        html_code = f"""
<div class="hero-card" style="border-top: 5px solid {color};">
    <div style="font-size: 2.5rem;">{medal}</div>
    <div class="player-name">{p['Player']}</div>
    <div style="display:flex; justify-content:center; align-items:center; gap:8px;">
        <img src="{logo}" width="30" height="30" onerror="this.style.display='none'">
        <span style="color:#aaa;">{p['Team_Code']}</span>
    </div>
    <div class="value-label">Value</div>
    <div class="price-tag">₹ {p['Market_Value']:.2f} Cr</div>
    <div class="role-badge">{p['Role']}</div>
</div>
"""
        with col:
            st.markdown(html_code, unsafe_allow_html=True)

    if len(top_3) > 1: render_card(col1, top_3.iloc[1], "🥈", "#C0C0C0")
    if len(top_3) > 0: render_card(col2, top_3.iloc[0], "👑", "#FFD700")
    if len(top_3) > 2: render_card(col3, top_3.iloc[2], "🥉", "#CD7F32")

st.markdown("---")

# TABS
tab1, tab2, tab3 = st.tabs(["📋 Detailed Scouting", "📈 Performance Clusters", "🔎 Player Profile"])

with tab1:
    vals['Team_Logo'] = vals['Team_Code'].apply(get_team_logo)
    st.dataframe(
        vals.head(50),
        column_order=["Team_Logo", "Player", "Role", "Market_Value", "bat_points", "bowl_points", "sr", "eco"],
        column_config={
            "Team_Logo": st.column_config.ImageColumn("Team", width="small"),
            "Player": st.column_config.TextColumn("Name", width="medium"),
            "Market_Value": st.column_config.NumberColumn("Value", format="₹ %.2f Cr"),
            "bat_points": st.column_config.ProgressColumn("Batting", format="%.0f", min_value=0, max_value=vals['bat_points'].max()),
            "bowl_points": st.column_config.ProgressColumn("Bowling", format="%.0f", min_value=0, max_value=vals['bowl_points'].max()),
            "sr": st.column_config.NumberColumn("SR", format="%.1f"),
            "eco": st.column_config.NumberColumn("Eco", format="%.2f"),
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )

with tab2:
    c = alt.Chart(vals.head(50)).mark_circle(size=150).encode(
        x='bat_points', y='bowl_points', color='Role', tooltip=['Player', 'Market_Value']
    ).interactive()
    st.altair_chart(c, use_container_width=True)

with tab3:
    col_sel, col_blank = st.columns([1, 2])
    with col_sel:
        player_list = vals['Player'].unique()
        selected_player = st.selectbox("Select Player", player_list)
    
    if selected_player:
        p_data = vals[vals['Player'] == selected_player].iloc[0]
        st.markdown(f"## {p_data['Player']} <span style='color:#4CAF50; font-size:1.5rem'>₹ {p_data['Market_Value']:.2f} Cr</span>", unsafe_allow_html=True)
        st.caption(f"{p_data['Team_Code']} | {p_data['Role']}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='stat-box'><div class='stat-label'>Batting Pts</div><div class='stat-val'>{p_data['bat_points']:.0f}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><div class='stat-label'>Strike Rate</div><div class='stat-val'>{p_data['sr']:.1f}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box'><div class='stat-label'>Bowling Pts</div><div class='stat-val'>{p_data['bowl_points']:.0f}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat-box'><div class='stat-label'>Economy</div><div class='stat-val'>{p_data['eco']:.2f}</div></div>", unsafe_allow_html=True)
            
        st.markdown("### Raw Stats")
        col_raw1, col_raw2 = st.columns(2)
        col_raw1.info(f"**Runs:** {p_data['bat_runs']:.0f} ({p_data['bat_balls']:.0f} balls)")
        col_raw2.info(f"**Wickets:** {p_data['bowl_wkts']:.0f} (Avg Eco: {p_data['eco']:.2f})")
