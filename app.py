import random
import streamlit as st

st.set_page_config(
    page_title="Box Office 100: The Ultimate Indian Cinema Challenge",
    page_icon="🎬",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {background: radial-gradient(circle at top, #1f2538 0%, #0f111a 45%, #090b12 100%);} 
    .hero {
        border: 1px solid #3b435d; border-radius: 16px; padding: 1rem 1.25rem;
        background: linear-gradient(145deg, rgba(48,58,91,0.35), rgba(24,27,40,0.8));
    }
    .slot {
        border: 2px dashed #5b6074; border-radius: 12px; padding: 0.85rem; margin-bottom: 0.6rem;
        background: rgba(255,255,255,0.03);
    }
    .slot.locked {border-style: solid; border-color: #2ea043; background: rgba(46,160,67,0.1);} 
    .slot-role {font-size: 0.9rem; color: #99a2be; text-transform: uppercase; letter-spacing: 0.08em;}
    .slot-name {font-weight: 700; color: #f4f7ff; margin-top: 0.2rem;}
    .slot-origin {font-size: 0.8rem; color: #a9b4d0;}
    .scorebox {
        border-radius: 12px; padding: 0.8rem; text-align: center; background: rgba(255,255,255,0.05);
        border: 1px solid #40475e;
    }
    .verdict {
        border-left: 5px solid #f2c94c; border-radius: 10px; padding: 0.8rem 1rem;
        background: rgba(242,201,76,0.12); font-weight: 600;
    }
    .ott-banner {
        margin-top: 0.8rem; border-radius: 12px; padding: 0.85rem 1rem;
        border: 1px solid #4e5b80; background: linear-gradient(120deg, rgba(78,91,128,0.45), rgba(35,41,59,0.85));
    }
    </style>
    """,
    unsafe_allow_html=True,
)

MOVIES = [
    {
        "title": "Sholay",
        "year": 1975,
        "roles": {
            "Director": "Ramesh Sippy",
            "Lead Male": "Amitabh Bachchan",
            "Lead Female": "Hema Malini",
            "Music Director": "R.D. Burman",
            "Writer": "Salim-Javed",
        },
    },
    {
        "title": "Dilwale Dulhania Le Jayenge",
        "year": 1995,
        "roles": {
            "Director": "Aditya Chopra",
            "Lead Male": "Shah Rukh Khan",
            "Lead Female": "Kajol",
            "Music Director": "Jatin-Lalit",
            "Writer": "Aditya Chopra",
        },
    },
    {
        "title": "Lagaan",
        "year": 2001,
        "roles": {
            "Director": "Ashutosh Gowariker",
            "Lead Male": "Aamir Khan",
            "Lead Female": "Gracy Singh",
            "Music Director": "A.R. Rahman",
            "Writer": "Ashutosh Gowariker",
        },
    },
    {
        "title": "3 Idiots",
        "year": 2009,
        "roles": {
            "Director": "Rajkumar Hirani",
            "Lead Male": "Aamir Khan",
            "Lead Female": "Kareena Kapoor",
            "Music Director": "Shantanu Moitra",
            "Writer": "Abhijat Joshi",
        },
    },
    {
        "title": "Rockstar",
        "year": 2011,
        "roles": {
            "Director": "Imtiaz Ali",
            "Lead Male": "Ranbir Kapoor",
            "Lead Female": "Nargis Fakhri",
            "Music Director": "A.R. Rahman",
            "Writer": "Imtiaz Ali",
        },
    },
    {
        "title": "Baahubali: The Conclusion",
        "year": 2017,
        "roles": {
            "Director": "S.S. Rajamouli",
            "Lead Male": "Prabhas",
            "Lead Female": "Anushka Shetty",
            "Music Director": "M.M. Keeravani",
            "Writer": "K.V. Vijayendra Prasad",
        },
    },
    {
        "title": "Dangal",
        "year": 2016,
        "roles": {
            "Director": "Nitesh Tiwari",
            "Lead Male": "Aamir Khan",
            "Lead Female": "Fatima Sana Shaikh",
            "Music Director": "Pritam",
            "Writer": "Nitesh Tiwari",
        },
    },
    {
        "title": "RRR",
        "year": 2022,
        "roles": {
            "Director": "S.S. Rajamouli",
            "Lead Male": "Jr. NTR & Ram Charan",
            "Lead Female": "Alia Bhatt",
            "Music Director": "M.M. Keeravani",
            "Writer": "K.V. Vijayendra Prasad",
        },
    },
    {
        "title": "Jawan",
        "year": 2023,
        "roles": {
            "Director": "Atlee",
            "Lead Male": "Shah Rukh Khan",
            "Lead Female": "Nayanthara",
            "Music Director": "Anirudh Ravichander",
            "Writer": "Atlee",
        },
    },
    {
        "title": "Gangubai Kathiawadi",
        "year": 2022,
        "roles": {
            "Director": "Sanjay Leela Bhansali",
            "Lead Male": "Shantanu Maheshwari",
            "Lead Female": "Alia Bhatt",
            "Music Director": "Sanjay Leela Bhansali",
            "Writer": "Utkarshini Vashishtha",
        },
    },
    {
        "title": "KGF: Chapter 2",
        "year": 2022,
        "roles": {
            "Director": "Prashanth Neel",
            "Lead Male": "Yash",
            "Lead Female": "Srinidhi Shetty",
            "Music Director": "Ravi Basrur",
            "Writer": "Prashanth Neel",
        },
    },
]

ROLE_WEIGHTS = {
    "Director": {
        "S.S. Rajamouli": (25, 23),
        "Aditya Chopra": (20, 19),
        "Rajkumar Hirani": (23, 18),
        "Ramesh Sippy": (22, 17),
        "Ashutosh Gowariker": (21, 17),
        "Nitesh Tiwari": (20, 17),
        "Atlee": (16, 22),
        "Sanjay Leela Bhansali": (21, 15),
        "Prashanth Neel": (15, 22),
        "Imtiaz Ali": (18, 14),
    },
    "Lead Male": {
        "Aamir Khan": (21, 19),
        "Shah Rukh Khan": (19, 23),
        "Amitabh Bachchan": (20, 18),
        "Prabhas": (15, 21),
        "Jr. NTR & Ram Charan": (18, 21),
        "Ranbir Kapoor": (17, 14),
        "Yash": (14, 21),
        "Shantanu Maheshwari": (12, 11),
    },
    "Lead Female": {
        "Alia Bhatt": (20, 18),
        "Kajol": (19, 17),
        "Kareena Kapoor": (17, 15),
        "Anushka Shetty": (16, 18),
        "Hema Malini": (18, 16),
        "Nayanthara": (15, 18),
        "Fatima Sana Shaikh": (14, 14),
        "Gracy Singh": (13, 12),
        "Srinidhi Shetty": (12, 15),
        "Nargis Fakhri": (11, 11),
    },
    "Music Director": {
        "A.R. Rahman": (20, 21),
        "M.M. Keeravani": (17, 20),
        "R.D. Burman": (20, 16),
        "Anirudh Ravichander": (15, 19),
        "Pritam": (14, 18),
        "Jatin-Lalit": (14, 16),
        "Sanjay Leela Bhansali": (15, 13),
        "Ravi Basrur": (12, 17),
        "Shantanu Moitra": (15, 13),
    },
    "Writer": {
        "K.V. Vijayendra Prasad": (22, 19),
        "Salim-Javed": (22, 17),
        "Aditya Chopra": (17, 15),
        "Ashutosh Gowariker": (18, 14),
        "Abhijat Joshi": (17, 14),
        "Imtiaz Ali": (16, 12),
        "Nitesh Tiwari": (18, 14),
        "Atlee": (13, 17),
        "Utkarshini Vashishtha": (15, 12),
        "Prashanth Neel": (13, 18),
    },
}

ROLES = ["Director", "Lead Male", "Lead Female", "Music Director", "Writer"]
SYNERGY_BONUS = 15
RANDOM_VARIANCE_MIN = -5
RANDOM_VARIANCE_MAX = 5
VERDICT_HISTORIC = 95
VERDICT_HIGH = 80
VERDICT_MID = 65
VERDICT_LOW = 50
SYNERGY_RULES = [
    (("Lead Male", "Shah Rukh Khan"), ("Director", "Aditya Chopra")),
    (("Director", "S.S. Rajamouli"), ("Writer", "K.V. Vijayendra Prasad")),
]


def random_movie():
    return random.choice(MOVIES)


def init_state():
    if "roster" not in st.session_state:
        st.session_state.roster = {role: None for role in ROLES}
    if "current_movie" not in st.session_state:
        st.session_state.current_movie = random_movie()
    if "result" not in st.session_state:
        st.session_state.result = None


def draft(role: str):
    if st.session_state.roster[role] is not None:
        return
    movie = st.session_state.current_movie
    st.session_state.roster[role] = {
        "name": movie["roles"][role],
        "movie": movie["title"],
        "year": movie["year"],
    }
    st.session_state.current_movie = random_movie()
    st.session_state.result = None


def compute_scores(roster: dict):
    critical = 0
    box_office = 0

    for role in ROLES:
        pick = roster.get(role)
        if not pick:
            continue
        person = pick["name"]
        c_score, b_score = ROLE_WEIGHTS.get(role, {}).get(person, (10, 10))
        critical += c_score
        box_office += b_score

    for (role_a, person_a), (role_b, person_b) in SYNERGY_RULES:
        current_a = roster.get(role_a, {}).get("name", "")
        current_b = roster.get(role_b, {}).get("name", "")
        if current_a == person_a and current_b == person_b:
            critical += SYNERGY_BONUS
            box_office += SYNERGY_BONUS

    critical += random.randint(RANDOM_VARIANCE_MIN, RANDOM_VARIANCE_MAX)
    box_office += random.randint(RANDOM_VARIANCE_MIN, RANDOM_VARIANCE_MAX)

    critical = max(0, min(100, critical))
    box_office = max(0, min(100, box_office))

    if critical >= VERDICT_HISTORIC and box_office >= VERDICT_HISTORIC:
        verdict = "All-Time Historic Blockbuster 🏆"
    elif critical >= VERDICT_HIGH and box_office < VERDICT_MID:
        verdict = "Cult Classic Masterpiece 🎬"
    elif critical < VERDICT_MID and box_office >= VERDICT_HIGH:
        verdict = "Commercial Masala Hit 💥"
    elif critical < VERDICT_LOW and box_office < VERDICT_LOW:
        verdict = "Disastrous Box Office Dud 📉"
    else:
        verdict = "Strong Theatrical Performer 🍿"

    roster_names = {roster.get(role, {}).get("name", "") for role in ROLES}

    if box_office < 50:
        opening_day = 2 + (box_office / 50) * 3
    elif box_office < 80:
        opening_day = 5 + ((box_office - 50) / 30) * 20
    elif box_office < 95:
        opening_day = 25 + ((box_office - 80) / 15) * 25
    else:
        opening_day = 50 + ((box_office - 95) / 5) * 22

    if critical < 40:
        legs_multiplier = 1.35 + (critical / 40) * 0.35
    elif critical < 60:
        legs_multiplier = 1.7 + ((critical - 40) / 20) * 0.8
    elif critical < 80:
        legs_multiplier = 2.5 + ((critical - 60) / 20) * 1.5
    else:
        legs_multiplier = 4.0 + ((critical - 80) / 20) * 2.0

    lifetime_domestic = opening_day * legs_multiplier

    global_icon_count = sum(
        name in roster_names for name in {"Shah Rukh Khan", "Prabhas", "S.S. Rajamouli"}
    )
    international_push_count = sum(
        name in roster_names for name in {"Prashanth Neel", "Jr. NTR & Ram Charan", "A.R. Rahman"}
    )
    overseas_multiplier = (
        1.15
        + (box_office / 100) * 0.25
        + global_icon_count * 0.32
        + international_push_count * 0.12
    )
    worldwide_gross = lifetime_domestic * overseas_multiplier

    if verdict == "Disastrous Box Office Dud 📉":
        ott_platform = "CineNow+"
        ott_note = "Picked up cheaply by a tier-3 streaming app to fill their late-night catalog gap."
    elif any(name in roster_names for name in {"S.S. Rajamouli", "Prashanth Neel", "Prabhas"}):
        ott_platform = "Netflix" if worldwide_gross >= 180 else "Prime Video"
        ott_note = "Record-breaking multi-lingual streaming deal locked after theatrical frenzy."
    elif critical >= VERDICT_HIGH and any(
        name in roster_names for name in {"Imtiaz Ali", "Sanjay Leela Bhansali"}
    ):
        ott_platform = "Netflix"
        ott_note = "Topping the global non-English viewing charts within days of release."
    elif box_office >= VERDICT_HIGH and critical < VERDICT_HIGH:
        ott_platform = "Prime Video" if box_office >= 90 else "Zee5"
        ott_note = "Set to premiere on a festive weekend with major family-audience push."
    else:
        ott_platform = "Hotstar"
        ott_note = "Secured a solid post-theatrical window with broad regional outreach."

    return {
        "critical": critical,
        "box_office": box_office,
        "verdict": verdict,
        "opening_day_cr": opening_day,
        "lifetime_domestic_cr": lifetime_domestic,
        "worldwide_cr": worldwide_gross,
        "ott_platform": ott_platform,
        "ott_note": ott_note,
    }


def format_currency_cr(value: float) -> str:
    return f"₹{value:,.1f} Cr"


def reset_game():
    st.session_state.roster = {role: None for role in ROLES}
    st.session_state.current_movie = random_movie()
    st.session_state.result = None


init_state()

st.markdown(
    """
    <div class='hero'>
        <h1 style='margin-bottom:0.2rem;'>Box Office 100</h1>
        <p style='margin-top:0;color:#b8c2dd;'>Draft a 5-member film crew to hit a perfect 100/100 in Critical Acclaim and Box Office Collection.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.1, 1.6], gap="large")

with left:
    st.subheader("Your Crew Roster")
    for role in ROLES:
        pick = st.session_state.roster[role]
        if pick is None:
            st.markdown(
                f"""
                <div class='slot'>
                    <div class='slot-role'>{role}</div>
                    <div class='slot-name' style='color:#7e879f;'>[EMPTY]</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class='slot locked'>
                    <div class='slot-role'>{role}</div>
                    <div class='slot-name'>{pick['name']}</div>
                    <div class='slot-origin'>Locked from {pick['movie']} ({pick['year']})</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    all_filled = all(st.session_state.roster[r] is not None for r in ROLES)

    release_locked = st.session_state.result is not None
    if st.button(
        "🎞️ Release Movie",
        use_container_width=True,
        disabled=(not all_filled) or release_locked,
        type="primary",
    ):
        st.session_state.result = compute_scores(st.session_state.roster)

    if st.session_state.result:
        result = st.session_state.result
        a, b = st.columns(2)
        a.markdown(
            f"<div class='scorebox'><div style='color:#9fa8c6;'>Critical Acclaim</div><div style='font-size:2rem;font-weight:800;'>{result['critical']}/100</div></div>",
            unsafe_allow_html=True,
        )
        b.markdown(
            f"<div class='scorebox'><div style='color:#9fa8c6;'>Box Office Collection</div><div style='font-size:2rem;font-weight:800;'>{result['box_office']}/100</div></div>",
            unsafe_allow_html=True,
        )
        f1, f2, f3 = st.columns(3)
        f1.markdown(
            f"<div class='scorebox'><div style='color:#9fa8c6;'>Opening Day (Domestic)</div><div style='font-size:1.2rem;font-weight:800;'>{format_currency_cr(result['opening_day_cr'])}</div></div>",
            unsafe_allow_html=True,
        )
        f2.markdown(
            f"<div class='scorebox'><div style='color:#9fa8c6;'>Lifetime Domestic</div><div style='font-size:1.2rem;font-weight:800;'>{format_currency_cr(result['lifetime_domestic_cr'])}</div></div>",
            unsafe_allow_html=True,
        )
        f3.markdown(
            f"<div class='scorebox'><div style='color:#9fa8c6;'>Worldwide Gross</div><div style='font-size:1.2rem;font-weight:800;'>{format_currency_cr(result['worldwide_cr'])}</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<div class='verdict'>Final Verdict: {result['verdict']}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='ott-banner'><strong>Post-Theatrical OTT Rights: {result['ott_platform']}</strong><br>{result['ott_note']}</div>",
            unsafe_allow_html=True,
        )

        if st.button("🔁 Try For Another Hit", use_container_width=True):
            reset_game()
            st.rerun()

with right:
    movie = st.session_state.current_movie
    safe_movie_key = "".join(ch if ch.isalnum() else "_" for ch in movie["title"])
    st.subheader("Current Roll")
    st.markdown(
        f"""
        <div class='hero' style='margin-top:0.3rem;'>
            <h2 style='margin-bottom:0.2rem;'>{movie['title']}</h2>
            <p style='margin-top:0;color:#b8c2dd;'>Release Year: {movie['year']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Draft From This Movie")
    for role in ROLES:
        person = movie["roles"][role]
        locked = st.session_state.roster[role] is not None
        st.button(
            f"Draft {person} as {role}",
            use_container_width=True,
            disabled=locked,
            key=f"draft_{role.replace(' ', '_')}_{safe_movie_key}_{movie['year']}",
            on_click=draft,
            args=(role,),
        )
