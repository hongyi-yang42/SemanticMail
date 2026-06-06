"""CSS injection for SemanticMail."""

import streamlit as st


def inject_styles() -> None:
    """Inject custom CSS styles into the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Risk level colors */
        .risk-low { color: #28a745; font-weight: bold; }
        .risk-medium { color: #d39e00; font-weight: bold; }
        .risk-high { color: #fd7e14; font-weight: bold; }
        .risk-critical { color: #dc3545; font-weight: bold; }

        /* Card styling */
        .email-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            background-color: #fafafa;
        }

        .email-card:hover {
            border-color: #4a90d9;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        /* General spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Expander styling */
        .streamlit-expanderHeader {
            font-size: 1rem;
            font-weight: 500;
        }

        /* Metric cards */
        [data-testid="stMetricValue"] {
            font-size: 1.2rem;
        }

        /* Inbox row buttons — left-align text for email-list feel */
        .stButton > button {
            text-align: left !important;
            justify-content: flex-start !important;
        }

        /* Tabs styling — flatter, less boxed */
        .stTabs [data-testid="stTabNav"] {
            gap: 2px;
        }
        .stTabs [role="tab"] {
            padding: 6px 14px;
            font-size: 0.85em;
            border-radius: 6px 6px 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
