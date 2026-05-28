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
