import streamlit as st


def inject_evatlas_ui():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

        :root {
            --bg: #0b1727;
            --sidebar: #18314d;
            --sidebar2: #12263d;
            --panel: rgba(22, 42, 66, 0.96);
            --panel2: rgba(18, 34, 54, 0.9);
            --text: #f4f8fc;
            --muted: #b8c8d8;
            --primary: #49b8e8;
            --accent: #47d18c;
            --line: rgba(171, 207, 226, 0.22);
        }

        html, body, [class*="css"] {
            font-family: Inter, system-ui, sans-serif;
        }

        .stApp {
            color: var(--text);
            background:
                linear-gradient(180deg, #0f2238, #0b1727 35%, #081321),
                var(--bg);
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.2;
            background-image:
                linear-gradient(rgba(117, 192, 228, 0.07) 1px, transparent 1px),
                linear-gradient(90deg, rgba(117, 192, 228, 0.07) 1px, transparent 1px);
            background-size: 42px 42px;
            z-index: 0;
        }

        .block-container {
            position: relative;
            z-index: 1;
            max-width: 1480px;
            padding-top: 4.25rem;
            padding-bottom: 4rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--sidebar), var(--sidebar2));
            border-right: 1px solid rgba(255,255,255,0.16);
            box-shadow: 12px 0 38px rgba(0,0,0,0.22);
        }

        [data-testid="stSidebar"] h1 {
            font-size: 2rem !important;
            line-height: 1.05 !important;
            color: #fff !important;
            word-break: keep-all !important;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] label {
            color: #dce9f5 !important;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            width: 100%;
            padding: 8px 10px;
            margin: 2px 0;
            border-radius: 8px;
            border: 1px solid transparent;
            transition: 150ms ease;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(73,184,232,0.13);
            border-color: rgba(73,184,232,0.36);
            transform: translateX(3px);
            box-shadow: inset 3px 0 0 var(--primary);
            cursor: pointer;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: rgba(73,184,232,0.2);
            border-color: rgba(73,184,232,0.5);
            box-shadow: inset 4px 0 0 var(--accent);
        }

        h1, h2, h3 {
            color: var(--text) !important;
            letter-spacing: 0;
        }

        h1 {
            font-size: clamp(2.2rem, 4vw, 4rem) !important;
            line-height: 1.05 !important;
            font-weight: 900 !important;
            margin-top: 0 !important;
        }

        .stApp label,
        .stApp [data-testid="stWidgetLabel"],
        .stApp [data-testid="stWidgetLabel"] p {
            color: var(--text) !important;
            font-weight: 700;
        }

        .stApp [data-testid="stCaptionContainer"] p {
            color: var(--muted) !important;
        }

        .cs-hero {
            position: relative;
            min-height: 220px;
            padding: 32px;
            margin-bottom: 24px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: linear-gradient(135deg, rgba(25,50,78,0.96), rgba(15,34,56,0.98));
            box-shadow: 0 18px 45px rgba(0,0,0,0.22);
            overflow: hidden;
        }

        .cs-hero::after {
            content: "";
            position: absolute;
            inset: -40%;
            background: repeating-linear-gradient(
                115deg,
                transparent 0,
                transparent 18px,
                rgba(73,184,232,0.08) 19px,
                transparent 21px
            );
            animation: scan 8s linear infinite;
            opacity: 0.16;
        }

        .cs-hero-inner {
            position: relative;
            z-index: 1;
            max-width: 900px;
        }

        .cs-kicker {
            display: inline-flex;
            padding: 8px 11px;
            border: 1px solid rgba(71,209,140,0.55);
            border-radius: 999px;
            color: var(--primary);
            background: rgba(73,184,232,0.16);
            font-weight: 800;
            font-size: 0.76rem;
            text-transform: uppercase;
        }

        .cs-hero-title {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-top: 20px;
            font-size: clamp(2.8rem, 6vw, 5.6rem);
            line-height: 0.95;
            font-weight: 950;
            color: var(--text);
        }

        .cs-hero-bolt {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: clamp(3.2rem, 6vw, 5.4rem);
            height: clamp(3.2rem, 6vw, 5.4rem);
            border-radius: 8px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: #06111f;
            font-size: 0.72em;
            flex: 0 0 auto;
        }

        .cs-hero-copy {
            max-width: 760px;
            margin-top: 18px;
            color: var(--muted);
            font-size: 1.08rem;
            line-height: 1.65;
        }

        .cs-pulse-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 24px;
        }

        .cs-chip {
            padding: 9px 12px;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.06);
            color: var(--primary);
            font-weight: 750;
        }

        [data-testid="stMetric"] {
            min-height: 118px;
            height: auto !important;
            padding: 18px 16px 16px;
            border-radius: 8px;
            border: 1px solid var(--line);
            background: var(--panel);
            box-shadow: 0 14px 36px rgba(0,0,0,0.18);
            overflow: visible;
        }

        [data-testid="stMetric"]::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
        }

        [data-testid="stMetricLabel"] p {
            color: var(--muted) !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            font-size: 0.72rem !important;
        }

        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] div,
        [data-testid="stMetric"] [title] {
            color: var(--text) !important;
            font-size: clamp(1.05rem, 1.45vw, 1.65rem) !important;
            line-height: 1.12 !important;
            font-weight: 850 !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            overflow-wrap: anywhere !important;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"],
        .stPlotlyChart,
        [data-testid="stExpander"],
        .stAlert {
            border-radius: 8px !important;
            border: 1px solid var(--line) !important;
            background: var(--panel2) !important;
            box-shadow: 0 14px 36px rgba(0,0,0,0.18);
        }

        .stButton > button,
        .stDownloadButton > button,
        a[data-testid="stLinkButton"] {
            min-height: 44px;
            border: 1px solid var(--primary) !important;
            border-radius: 8px !important;
            color: #fff !important;
            background: var(--primary) !important;
            font-weight: 900 !important;
            transition: 160ms ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        a[data-testid="stLinkButton"]:hover {
            transform: translateY(-1px);
            filter: brightness(0.96);
        }

        .stSelectbox div[data-baseweb="select"] > div,
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input {
            border-radius: 8px !important;
            border: 1px solid var(--line) !important;
            background: rgba(13,28,47,0.96) !important;
            color: var(--text) !important;
        }

        .stSelectbox div[data-baseweb="select"] span,
        .stSelectbox div[data-baseweb="select"] div {
            color: var(--text) !important;
        }

        .stSelectbox div[data-baseweb="select"] svg {
            color: var(--primary) !important;
            fill: var(--primary) !important;
        }

        pre {
            border-radius: 8px !important;
            border: 1px solid var(--line) !important;
            background: rgba(8,19,33,0.92) !important;
        }

        hr {
            border: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--line), transparent);
        }

        @keyframes scan {
            from { transform: translateX(-8%) translateY(-6%); }
            to { transform: translateX(8%) translateY(6%); }
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 3.5rem;
            }

            .cs-hero-title {
                font-size: 3rem;
                flex-wrap: wrap;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_evatlas_home_hero():
    st.markdown(
        """
        <section class="cs-hero">
            <div class="cs-hero-inner">
                <div class="cs-kicker">Live EV infrastructure command deck</div>
                <div class="cs-hero-title">
                    <span class="cs-hero-bolt">⚡</span>
                    <span>EVAtlas</span>
                </div>
                <div class="cs-hero-copy">
                    Route planning, charger trust, fleet pressure, operator benchmarking, and investment intelligence
                    in one high-voltage prototype for Australia's EV charging network.
                </div>
                <div class="cs-pulse-row">
                    <span class="cs-chip">Route risk</span>
                    <span class="cs-chip">Live-style decisions</span>
                    <span class="cs-chip">Fleet planning</span>
                    <span class="cs-chip">Charger reliability</span>
                    <span class="cs-chip">Investment priority</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


# Backwards compatibility, so older app.py imports still work.
def inject_crazy_ui():
    inject_evatlas_ui()


def render_crazy_home_hero():
    render_evatlas_home_hero()
