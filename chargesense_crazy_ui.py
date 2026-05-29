import streamlit as st


def inject_crazy_ui():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

        :root {
            --cs-bg: #0b1727;
            --cs-panel: rgba(18, 34, 54, 0.9);
            --cs-panel-strong: rgba(22, 42, 66, 0.96);
            --cs-text: #f4f8fc;
            --cs-muted: #b8c8d8;
            --cs-primary: #49b8e8;
            --cs-primary-soft: rgba(73, 184, 232, 0.16);
            --cs-accent: #47d18c;
            --cs-line: rgba(171, 207, 226, 0.22);
            --cs-warning: #f2a93b;
        }

        html, body, [class*="css"] {
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            color: var(--cs-text);
            background:
                linear-gradient(180deg, #0f2238, #0b1727 34%, #081321),
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
                linear-gradient(rgba(117, 192, 228, 0.07) 1px, transparent 1px),
                linear-gradient(90deg, rgba(117, 192, 228, 0.07) 1px, transparent 1px);
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
                linear-gradient(180deg, #18314d, #12263d);
            border-right: 1px solid rgba(255, 255, 255, 0.16);
            box-shadow: 12px 0 38px rgba(0, 0, 0, 0.22);
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

        [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
            border-color: rgba(255, 255, 255, 0.36) !important;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            width: 100%;
            padding: 8px 10px;
            margin: 2px 0;
            border-radius: 8px;
            border: 1px solid transparent;
            transition:
                background 150ms ease,
                border-color 150ms ease,
                transform 150ms ease,
                box-shadow 150ms ease;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(73, 184, 232, 0.13);
            border-color: rgba(73, 184, 232, 0.36);
            transform: translateX(3px);
            box-shadow: inset 3px 0 0 var(--cs-primary);
            cursor: pointer;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
        [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
            background: rgba(73, 184, 232, 0.2);
            border-color: rgba(73, 184, 232, 0.5);
            box-shadow: inset 4px 0 0 var(--cs-accent), 0 8px 18px rgba(0, 0, 0, 0.14);
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
                linear-gradient(135deg, rgba(25, 50, 78, 0.96), rgba(15, 34, 56, 0.98));
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22);
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
                    rgba(73, 184, 232, 0.08) 19px,
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
            display: flex;
            align-items: center;
            gap: 14px;
            margin-top: 20px;
            font-size: clamp(2.8rem, 6vw, 5.6rem);
            line-height: 0.95;
            font-weight: 950;
            color: var(--cs-text);
            text-shadow: none;
        }

        .cs-hero-bolt {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: clamp(3.2rem, 6vw, 5.4rem);
            height: clamp(3.2rem, 6vw, 5.4rem);
            border-radius: 8px;
            background: linear-gradient(135deg, var(--cs-primary), var(--cs-accent));
            color: #06111f;
            font-size: 0.72em;
            box-shadow: 0 12px 28px rgba(73, 184, 232, 0.2);
            flex: 0 0 auto;
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
            background: rgba(255, 255, 255, 0.06);
            color: var(--cs-primary);
            font-weight: 750;
            box-shadow: none;
        }

        [data-testid="stMetric"] {
            position: relative;
            min-height: 118px;
            height: auto !important;
            padding: 18px 16px 16px 16px;
            border-radius: 8px;
            border: 1px solid var(--cs-line);
            background: var(--cs-panel-strong);
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.18);
            overflow: visible;
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
            font-size: clamp(1.05rem, 1.45vw, 1.65rem) !important;
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
            max-width: none !important;
            width: auto !important;
        }

        [data-testid="stMetric"] * {
            text-overflow: clip !important;
        }

        [data-testid="stMetric"] [title] {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
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
            background: var(--cs-panel) !important;
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.18);
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
            background: rgba(13, 28, 47, 0.96) !important;
            color: var(--cs-text) !important;
            box-shadow: inset 0 0 0 1px rgba(73, 184, 232, 0.04);
        }

        .stSelectbox div[data-baseweb="select"] span,
        .stSelectbox div[data-baseweb="select"] div {
            color: var(--cs-text) !important;
        }

        .stSelectbox div[data-baseweb="select"] svg {
            color: var(--cs-primary) !important;
            fill: var(--cs-primary) !important;
        }

        .stSelectbox div[data-baseweb="select"] > div:hover,
        .stTextInput input:hover,
        .stTextArea textarea:hover,
        .stNumberInput input:hover,
        .stDateInput input:hover,
        .stTimeInput input:hover {
            border-color: rgba(73, 184, 232, 0.55) !important;
            background: rgba(16, 35, 58, 0.98) !important;
        }

        .stSelectbox div[data-baseweb="select"] > div:focus-within,
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus,
        .stTimeInput input:focus {
            border-color: var(--cs-primary) !important;
            box-shadow: 0 0 0 2px rgba(73, 184, 232, 0.18) !important;
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
            background: rgba(8, 19, 33, 0.92) !important;
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
                flex-wrap: wrap;
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
                <div class="cs-hero-title"><span class="cs-hero-bolt">⚡</span><span>EVAtlas</span></div>
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
