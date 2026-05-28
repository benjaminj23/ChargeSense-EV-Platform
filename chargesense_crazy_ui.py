import streamlit as st


def inject_crazy_ui():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

        :root {
            --cs-bg: #dce9f2;
            --cs-panel: rgba(245, 250, 253, 0.9);
            --cs-panel-strong: rgba(250, 253, 255, 0.96);
            --cs-text: #102033;
            --cs-muted: #536879;
            --cs-primary: #08779b;
            --cs-primary-soft: #d6eef6;
            --cs-accent: #2fb37c;
            --cs-line: #b8d0dc;
            --cs-warning: #f2a93b;
        }

        html, body, [class*="css"] {
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            color: var(--cs-text);
            background:
                linear-gradient(180deg, rgba(190, 215, 229, 0.96), rgba(220, 233, 242, 0.98) 34%, rgba(204, 221, 232, 0.98)),
                var(--cs-bg);
            overflow-x: hidden;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.22;
            background-image:
                linear-gradient(rgba(8, 126, 164, 0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(8, 126, 164, 0.1) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(to bottom, black, transparent 72%);
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
            background:
                linear-gradient(180deg, #102033, #0b1727);
            border-right: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 10px 0 34px rgba(8, 65, 92, 0.16);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label {
            color: #f7fbff !important;
        }

        [data-testid="stSidebar"] h1 {
            font-size: 2rem !important;
            line-height: 1.05 !important;
            overflow-wrap: normal !important;
            word-break: keep-all !important;
            text-shadow: none !important;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: #dce9f5 !important;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: #dce9f5 !important;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            color: #f7fbff !important;
        }

        [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
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
            font-size: clamp(2.2rem, 4vw, 4rem) !important;
            line-height: 1.05 !important;
            font-weight: 900 !important;
            color: var(--cs-text) !important;
            text-shadow: none;
            margin-top: 0 !important;
            margin-bottom: 1.2rem !important;
        }

        h2 {
            color: var(--cs-text) !important;
            font-weight: 850 !important;
        }

        h3 {
            color: var(--cs-text) !important;
            font-weight: 800 !important;
        }

        p, li, label, span, div {
            color: inherit;
        }

        .stApp label,
        .stApp [data-testid="stWidgetLabel"],
        .stApp [data-testid="stWidgetLabel"] p {
            color: var(--cs-text) !important;
            font-weight: 700;
        }

        .stApp small,
        .stApp .caption,
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] p {
            color: var(--cs-muted) !important;
        }

        .cs-hero {
            position: relative;
            min-height: 220px;
            padding: 32px;
            margin: 0 0 24px 0;
            border: 1px solid var(--cs-line);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(230, 243, 249, 0.96), rgba(248, 252, 254, 0.98));
            box-shadow: 0 18px 45px rgba(8, 65, 92, 0.16);
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
                    rgba(8, 126, 164, 0.08) 19px,
                    transparent 21px
                );
            animation: cs-scan 8s linear infinite;
            opacity: 0.16;
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
            color: var(--cs-primary);
            background: var(--cs-primary-soft);
            font-weight: 800;
            font-size: 0.76rem;
            text-transform: uppercase;
        }

        .cs-hero-title {
            margin-top: 20px;
            font-size: clamp(2.8rem, 6vw, 5.6rem);
            line-height: 0.95;
            font-weight: 950;
            color: var(--cs-text);
            text-shadow: none;
        }

        .cs-hero-copy {
            max-width: 760px;
            margin-top: 18px;
            color: var(--cs-muted);
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
            border: 1px solid var(--cs-line);
            background: rgba(248, 252, 254, 0.82);
            color: var(--cs-primary);
            font-weight: 750;
            box-shadow: none;
        }

        [data-testid="stMetric"] {
            position: relative;
            min-height: 118px;
            padding: 18px 16px 16px 16px;
            border-radius: 8px;
            border: 1px solid var(--cs-line);
            background: var(--cs-panel-strong);
            box-shadow: 0 14px 36px rgba(8, 65, 92, 0.14);
            overflow: hidden;
        }

        [data-testid="stMetric"]::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--cs-primary), var(--cs-accent));
            box-shadow: none;
        }

        [data-testid="stMetricLabel"] p {
            color: var(--cs-muted) !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            font-size: 0.72rem !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--cs-text) !important;
            font-size: clamp(1.3rem, 1.75vw, 2rem) !important;
            line-height: 1.12 !important;
            font-weight: 850 !important;
            text-shadow: none;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            word-break: normal !important;
            overflow-wrap: anywhere !important;
        }

        [data-testid="stMetricValue"] div {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            word-break: normal !important;
            overflow-wrap: anywhere !important;
        }

        [data-testid="stMetricDelta"] {
            white-space: normal !important;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"],
        .stPlotlyChart,
        [data-testid="stExpander"],
        .stAlert {
            border-radius: 8px !important;
            border: 1px solid var(--cs-line) !important;
            background: rgba(248, 252, 254, 0.9) !important;
            box-shadow: 0 14px 36px rgba(8, 65, 92, 0.12);
            overflow: hidden;
        }

        .stButton > button,
        .stDownloadButton > button,
        a[data-testid="stLinkButton"] {
            min-height: 44px;
            border: 1px solid var(--cs-primary) !important;
            border-radius: 8px !important;
            color: #ffffff !important;
            background: var(--cs-primary) !important;
            font-weight: 900 !important;
            box-shadow: 0 10px 24px rgba(8, 126, 164, 0.2);
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        a[data-testid="stLinkButton"]:hover {
            transform: translateY(-1px);
            filter: brightness(0.96);
            box-shadow: 0 14px 30px rgba(8, 126, 164, 0.25);
        }

        .stSelectbox div[data-baseweb="select"] > div,
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input {
            border-radius: 8px !important;
            border: 1px solid var(--cs-line) !important;
            background: rgba(250, 253, 255, 0.96) !important;
            color: var(--cs-text) !important;
            box-shadow: none;
        }

        .stSlider [data-baseweb="slider"] > div {
            color: var(--cs-primary);
        }

        [data-testid="stMarkdownContainer"] code {
            border-radius: 8px;
            color: var(--cs-primary);
            background: var(--cs-primary-soft);
            border: 1px solid var(--cs-line);
        }

        pre {
            border-radius: 8px !important;
            border: 1px solid var(--cs-line) !important;
            background: rgba(250, 253, 255, 0.96) !important;
            box-shadow: none;
        }

        hr {
            border: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--cs-line), transparent);
        }

        @keyframes cs-scan {
            from { transform: translateX(-8%) translateY(-6%) rotate(0deg); }
            to { transform: translateX(8%) translateY(6%) rotate(0deg); }
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 3.5rem;
            }

            .cs-hero {
                padding: 24px;
                min-height: 230px;
            }

            .cs-hero-title {
                font-size: 3rem;
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


def inject_chargesense_ui():
    inject_crazy_ui()


def render_chargesense_home_hero():
    render_crazy_home_hero()
