import streamlit as st


def inject_crazy_ui():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

        :root {
            --cs-bg: #060711;
            --cs-panel: rgba(13, 18, 35, 0.76);
            --cs-panel-strong: rgba(19, 25, 50, 0.9);
            --cs-text: #f7fbff;
            --cs-muted: #aab8d3;
            --cs-cyan: #00e5ff;
            --cs-lime: #b6ff4d;
            --cs-pink: #ff3df2;
            --cs-amber: #ffcf33;
            --cs-red: #ff4778;
        }

        html, body, [class*="css"] {
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            color: var(--cs-text);
            background:
                radial-gradient(circle at 12% 10%, rgba(0, 229, 255, 0.24), transparent 25rem),
                radial-gradient(circle at 86% 6%, rgba(255, 61, 242, 0.2), transparent 26rem),
                radial-gradient(circle at 70% 85%, rgba(182, 255, 77, 0.14), transparent 25rem),
                linear-gradient(135deg, #060711 0%, #091323 42%, #12081e 100%);
            overflow-x: hidden;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.24;
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.07) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.07) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(to bottom, black, transparent 82%);
            z-index: 0;
        }

        .block-container {
            position: relative;
            z-index: 1;
            max-width: 1480px;
            padding-top: 1.3rem;
            padding-bottom: 4rem;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(9, 16, 33, 0.98), rgba(17, 8, 31, 0.98)),
                radial-gradient(circle at top, rgba(0, 229, 255, 0.18), transparent 22rem);
            border-right: 1px solid rgba(0, 229, 255, 0.24);
            box-shadow: 18px 0 55px rgba(0, 0, 0, 0.32);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label {
            color: #f7fbff !important;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label,
        [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stRadio {
            border-radius: 8px;
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        h1 {
            font-size: clamp(2.4rem, 5vw, 5rem) !important;
            line-height: 0.95 !important;
            font-weight: 900 !important;
            color: #ffffff !important;
            text-shadow:
                0 0 18px rgba(0, 229, 255, 0.42),
                0 0 44px rgba(255, 61, 242, 0.24);
        }

        h2 {
            color: #eaf7ff !important;
            font-weight: 850 !important;
        }

        h3 {
            color: #dff9ff !important;
            font-weight: 800 !important;
        }

        p, li, label, span, div {
            color: inherit;
        }

        .cs-hero {
            position: relative;
            min-height: 260px;
            padding: 34px;
            margin: 0 0 24px 0;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(0, 229, 255, 0.18), rgba(255, 61, 242, 0.13) 52%, rgba(182, 255, 77, 0.12)),
                rgba(6, 9, 20, 0.68);
            box-shadow:
                0 24px 80px rgba(0, 0, 0, 0.34),
                inset 0 0 60px rgba(255, 255, 255, 0.04);
            overflow: hidden;
        }

        .cs-hero::after {
            content: "";
            position: absolute;
            inset: -40%;
            background:
                repeating-linear-gradient(
                    115deg,
                    transparent 0,
                    transparent 18px,
                    rgba(255, 255, 255, 0.08) 19px,
                    transparent 21px
                );
            animation: cs-scan 8s linear infinite;
            opacity: 0.22;
        }

        .cs-hero-inner {
            position: relative;
            z-index: 1;
            max-width: 860px;
        }

        .cs-kicker {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 8px 11px;
            border: 1px solid rgba(182, 255, 77, 0.55);
            border-radius: 999px;
            color: var(--cs-lime);
            background: rgba(182, 255, 77, 0.08);
            font-weight: 800;
            font-size: 0.76rem;
            text-transform: uppercase;
        }

        .cs-hero-title {
            margin-top: 20px;
            font-size: clamp(3rem, 7vw, 6.6rem);
            line-height: 0.86;
            font-weight: 950;
            color: white;
            text-shadow:
                0 0 22px rgba(0, 229, 255, 0.55),
                0 0 60px rgba(255, 61, 242, 0.34);
        }

        .cs-hero-copy {
            max-width: 760px;
            margin-top: 18px;
            color: #d8e7ff;
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
            border: 1px solid rgba(255, 255, 255, 0.18);
            background: rgba(255, 255, 255, 0.08);
            color: #f7fbff;
            font-weight: 750;
            box-shadow: 0 0 24px rgba(0, 229, 255, 0.08);
        }

        [data-testid="stMetric"] {
            position: relative;
            min-height: 128px;
            padding: 18px 18px 16px 18px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background:
                linear-gradient(145deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.035)),
                rgba(8, 12, 25, 0.82);
            box-shadow:
                0 18px 46px rgba(0, 0, 0, 0.28),
                inset 0 0 38px rgba(0, 229, 255, 0.04);
            overflow: hidden;
        }

        [data-testid="stMetric"]::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--cs-cyan), var(--cs-pink), var(--cs-lime));
            box-shadow: 0 0 22px rgba(0, 229, 255, 0.65);
        }

        [data-testid="stMetricLabel"] p {
            color: var(--cs-muted) !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            font-size: 0.72rem !important;
        }

        [data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-weight: 900 !important;
            text-shadow: 0 0 18px rgba(0, 229, 255, 0.28);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"],
        .stPlotlyChart,
        [data-testid="stExpander"],
        .stAlert {
            border-radius: 8px !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            background: rgba(9, 14, 29, 0.74) !important;
            box-shadow: 0 18px 55px rgba(0, 0, 0, 0.24);
            overflow: hidden;
        }

        .stButton > button,
        .stDownloadButton > button,
        a[data-testid="stLinkButton"] {
            min-height: 44px;
            border: 1px solid rgba(0, 229, 255, 0.62) !important;
            border-radius: 8px !important;
            color: #031018 !important;
            background: linear-gradient(90deg, var(--cs-cyan), var(--cs-lime)) !important;
            font-weight: 900 !important;
            box-shadow:
                0 0 24px rgba(0, 229, 255, 0.26),
                0 14px 34px rgba(0, 0, 0, 0.3);
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        a[data-testid="stLinkButton"]:hover {
            transform: translateY(-1px);
            filter: saturate(1.25);
            box-shadow:
                0 0 32px rgba(0, 229, 255, 0.42),
                0 18px 42px rgba(0, 0, 0, 0.36);
        }

        .stSelectbox div[data-baseweb="select"] > div,
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input {
            border-radius: 8px !important;
            border: 1px solid rgba(0, 229, 255, 0.26) !important;
            background: rgba(5, 9, 20, 0.72) !important;
            color: #ffffff !important;
            box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.05);
        }

        .stSlider [data-baseweb="slider"] > div {
            color: var(--cs-cyan);
        }

        [data-testid="stMarkdownContainer"] code {
            border-radius: 8px;
            color: #b6ff4d;
            background: rgba(182, 255, 77, 0.1);
            border: 1px solid rgba(182, 255, 77, 0.18);
        }

        pre {
            border-radius: 8px !important;
            border: 1px solid rgba(0, 229, 255, 0.18) !important;
            background: rgba(4, 8, 18, 0.92) !important;
            box-shadow: inset 0 0 40px rgba(0, 229, 255, 0.05);
        }

        hr {
            border: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.9), rgba(255, 61, 242, 0.7), transparent);
        }

        @keyframes cs-scan {
            from { transform: translateX(-8%) translateY(-6%) rotate(0deg); }
            to { transform: translateX(8%) translateY(6%) rotate(0deg); }
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .cs-hero {
                padding: 24px;
                min-height: 230px;
            }

            .cs-hero-title {
                font-size: 3.2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_crazy_home_hero():
    st.markdown(
        """
        <section class="cs-hero">
            <div class="cs-hero-inner">
                <div class="cs-kicker">Live EV infrastructure command deck</div>
                <div class="cs-hero-title">ChargeSense</div>
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
