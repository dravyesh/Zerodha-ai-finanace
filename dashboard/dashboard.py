# ============================================================
# ZERODHA AI FINANCIAL INTELLIGENCE - STREAMLIT DASHBOARD
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import requests


# ============================================================
# FASTAPI CONFIG
# ============================================================

FASTAPI_URL = "https://zerodha-ai-finanace.onrender.com"


# ============================================================
# SERVICES
# ============================================================

from services.portfolio import (
    read_portfolio,
    valid_coloumn,
    clean_data,
)

from services.market import (
    updated_current_price,
    get_stock_info,
    get_market_data,
)

from services.news import (
    get_stock_news,
)


# ============================================================
# ANALYTICS
# ============================================================

from Analytics.portfolio_analytics import (
    calculate_total_investment,
    calculate_current_value,
    calculate_profit_loss,
    calculate_profit_loss_percentage,
    calculate_portfolio_summary,
)

from Analytics.sector_analysis import (
    compute_sector_breakdown,
)


# ============================================================
# FASTAPI HELPERS
# ============================================================

def check_fastapi():
    """
    Check whether FastAPI backend is running.
    """

    try:

        response = requests.get(
            f"{FASTAPI_URL}/api/health",
            timeout=3,
        )

        return response.status_code == 200

    except Exception:

        return False


def post_fastapi(
    endpoint,
    payload,
    timeout=120,
):
    """
    Generic FastAPI POST helper.
    """

    try:

        response = requests.post(
            f"{FASTAPI_URL}{endpoint}",
            json=payload,
            timeout=timeout,
        )

        if response.status_code == 200:

            return {
                "success": True,
                "data": response.json(),
            }

        try:

            error_data = response.json()

            error_message = error_data.get(
                "detail",
                response.text,
            )

        except Exception:

            error_message = response.text

        return {
            "success": False,
            "error": (
                f"FastAPI returned "
                f"{response.status_code}: "
                f"{error_message}"
            ),
        }

    except requests.exceptions.ConnectionError:

        return {
            "success": False,
            "error": (
                "Unable to connect to FastAPI. "
                "Start it using: "
                "uvicorn fastapi_app:app --reload"
            ),
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "error": "FastAPI request timed out.",
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
        }


# ============================================================
# PORTFOLIO JSON CONVERTER
# ============================================================

def prepare_portfolio_payload(
    portfolio_df,
):
    """
    Convert DataFrame into JSON-safe list of dictionaries.
    """

    if portfolio_df is None:

        return []

    if portfolio_df.empty:

        return []

    safe_df = portfolio_df.copy()

    safe_df = safe_df.where(
        pd.notnull(safe_df),
        None,
    )

    return safe_df.to_dict(
        orient="records"
    )


# ============================================================
# PURE RAG API
# ============================================================

def call_rag_api(
    question,
):
    """
    Pure RAG call.

    Useful for general financial education questions only.
    """

    result = post_fastapi(
        "/api/rag/query",
        {
            "question": question,
        },
        timeout=120,
    )

    if not result["success"]:

        return result

    answer = result["data"].get(
        "answer",
        "",
    )

    return {
        "success": True,
        "answer": answer,
    }


# ============================================================
# HYBRID ASK AI API
# Portfolio + RAG + News
# ============================================================

def call_chat_api(
    question,
    portfolio_df,
    news_data=None,
):
    """
    Hybrid AI chat request.

    Sends:
    - question
    - uploaded portfolio
    - optional news

    FastAPI then calls AI.chat_chain.run_chat_chain().
    """

    if not question or not question.strip():

        return {
            "success": False,
            "error": "Question cannot be empty.",
        }

    portfolio_records = (
        prepare_portfolio_payload(
            portfolio_df
        )
    )

    payload = {
        "question": question.strip(),
        "portfolio": portfolio_records,
        "news": news_data or {},
    }

    result = post_fastapi(
        "/api/chat",
        payload,
        timeout=120,
    )

    if not result["success"]:

        return result

    answer = result["data"].get(
        "answer",
        "",
    )

    if not answer:

        return {
            "success": False,
            "error": (
                "AI did not return an answer."
            ),
        }

    return {
        "success": True,
        "answer": answer,
        "portfolio_loaded": (
            result["data"].get(
                "portfolio_loaded",
                bool(portfolio_records),
            )
        ),
    }


# ============================================================
# AI INSIGHTS API HELPERS
# ============================================================

def call_portfolio_ai_api(
    endpoint,
    portfolio_df,
):

    payload = {
        "portfolio": (
            prepare_portfolio_payload(
                portfolio_df
            )
        )
    }

    result = post_fastapi(
        endpoint,
        payload,
        timeout=120,
    )

    if not result["success"]:

        return result

    return {
        "success": True,
        "result": (
            result["data"].get(
                "result",
                "",
            )
        ),
    }


# ============================================================
# HISTORICAL MARKET DATA
# ============================================================

def get_historical_data(
    symbols,
    period="1y",
):
    """
    Fetch historical closing prices.
    """

    historical_data = []

    for symbol in symbols:

        try:

            yahoo_symbol = (
                f"{symbol}.NS"
            )

            stock = yf.Ticker(
                yahoo_symbol
            )

            history = stock.history(
                period=period,
                auto_adjust=False,
            )

            if history.empty:

                continue

            history = (
                history.reset_index()
            )

            history["Stock Symbol"] = (
                symbol
            )

            history = history[
                [
                    "Date",
                    "Stock Symbol",
                    "Close",
                ]
            ]

            history = history.dropna(
                subset=["Close"]
            )

            historical_data.append(
                history
            )

        except Exception as error:

            print(
                "Historical data error "
                f"for {symbol}: {error}"
            )

    if not historical_data:

        return pd.DataFrame()

    return pd.concat(
        historical_data,
        ignore_index=True,
    )


# ============================================================
# MAIN APP
# ============================================================

def main():

    # ========================================================
    # PAGE CONFIG
    # ========================================================

    st.set_page_config(
        page_title=(
            "Zerodha AI Financial Intelligence"
        ),
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ========================================================
    # SESSION STATE
    # ========================================================

    if "portfolio_data" not in st.session_state:
        st.session_state.portfolio_data = None

    if "news_data" not in st.session_state:
        st.session_state.news_data = {}

    if "file_name" not in st.session_state:
        st.session_state.file_name = None

    if "health_result" not in st.session_state:
        st.session_state.health_result = None

    if "risk_result" not in st.session_state:
        st.session_state.risk_result = None

    if "summary_result" not in st.session_state:
        st.session_state.summary_result = None

    if "improvement_result" not in st.session_state:
        st.session_state.improvement_result = None

    if "stock_ai_result" not in st.session_state:
        st.session_state.stock_ai_result = None

    if "rag_answer" not in st.session_state:
        st.session_state.rag_answer = None

    if "chat_answer" not in st.session_state:
        st.session_state.chat_answer = None

    # ========================================================
    # HEADER
    # ========================================================

    st.title(
        "📊 Zerodha AI Financial Intelligence"
    )

    st.caption(
        "Portfolio Analytics • Market Data • "
        "News • AI Insights"
    )

    # ========================================================
    # SIDEBAR
    # ========================================================

    with st.sidebar:

        st.header(
            "📁 Portfolio"
        )

        uploaded_file = st.file_uploader(
            "Upload Portfolio",
            type=["csv", "xlsx"],
        )

        st.divider()

        if (
            st.session_state
            .portfolio_data
            is not None
        ):

            st.success(
                "Portfolio loaded"
            )

            if st.session_state.file_name:

                st.caption(
                    "File: "
                    f"{st.session_state.file_name}"
                )

            if st.button(
                "🔄 Refresh Market Data",
                width="stretch",
            ):

                try:

                    with st.spinner(
                        "Updating market data..."
                    ):

                        df = (
                            st.session_state
                            .portfolio_data
                            .copy()
                        )

                        df = (
                            updated_current_price(
                                df
                            )
                        )

                        (
                            st.session_state
                            .portfolio_data
                        ) = df

                    st.success(
                        "Market data updated"
                    )

                except Exception as error:

                    st.error(
                        "Market data update "
                        f"failed: {error}"
                    )

    # ========================================================
    # LOAD PORTFOLIO
    # ========================================================

    if uploaded_file is not None:

        new_file = (
            st.session_state.file_name
            != uploaded_file.name
        )

        if new_file:

            try:

                with st.spinner(
                    "Reading portfolio..."
                ):

                    portfolio = (
                        read_portfolio(
                            uploaded_file
                        )
                    )

                missing_columns = (
                    valid_coloumn(
                        portfolio
                    )
                )

                if missing_columns:

                    st.error(
                        "Missing required columns: "
                        + ", ".join(
                            missing_columns
                        )
                    )

                    st.stop()

                portfolio = clean_data(
                    portfolio
                )

                with st.spinner(
                    "Fetching live market data..."
                ):

                    portfolio = (
                        updated_current_price(
                            portfolio
                        )
                    )

                (
                    st.session_state
                    .portfolio_data
                ) = portfolio

                st.session_state.file_name = (
                    uploaded_file.name
                )

                st.session_state.news_data = {}

                st.session_state.health_result = None
                st.session_state.risk_result = None
                st.session_state.summary_result = None
                st.session_state.improvement_result = None
                st.session_state.stock_ai_result = None
                st.session_state.rag_answer = None
                st.session_state.chat_answer = None

            except Exception as error:

                st.error(
                    "Unable to process portfolio: "
                    f"{error}"
                )

                st.stop()

    # ========================================================
    # NO PORTFOLIO
    # ========================================================

    if (
        st.session_state
        .portfolio_data
        is None
    ):

        st.info(
            "👈 Upload your portfolio "
            "from the sidebar to begin."
        )

        st.stop()

    # ========================================================
    # DATA
    # ========================================================

    portfolio = (
        st.session_state
        .portfolio_data
    )

    # ========================================================
    # COMMON CALCULATIONS
    # ========================================================

    try:

        total_investment = (
            calculate_total_investment(
                portfolio
            )
        )

    except Exception:

        total_investment = 0

    try:

        current_value = (
            calculate_current_value(
                portfolio
            )
        )

    except Exception:

        current_value = 0

    try:

        profit_loss = (
            calculate_profit_loss(
                portfolio
            )
        )

    except Exception:

        profit_loss = 0

    try:

        profit_loss_pct = (
            calculate_profit_loss_percentage(
                portfolio
            )
        )

    except Exception:

        profit_loss_pct = 0

    # ========================================================
    # NAVIGATION
    # ========================================================

    st.sidebar.divider()

    st.sidebar.subheader(
        "🧭 Sections"
    )

    section = st.sidebar.radio(
        "Go to",
        [
            "📈 Overview",
            "📊 Analytics",
            "🎯 Benchmark",
            "🤖 AI Insights",
            "📈 Stock Analysis",
            "📰 Market News",
            "💬 Ask AI",
        ],
    )

    # ========================================================
    # OVERVIEW
    # ========================================================

    if section == "📈 Overview":

        st.header(
            "📈 Portfolio Overview"
        )

        col1, col2, col3, col4 = (
            st.columns(4)
        )

        with col1:

            st.metric(
                "💰 Total Investment",
                f"₹ {total_investment:,.2f}",
            )

        with col2:

            st.metric(
                "📊 Current Value",
                f"₹ {current_value:,.2f}",
            )

        with col3:

            st.metric(
                "💹 Profit / Loss",
                f"₹ {profit_loss:,.2f}",
            )

        with col4:

            st.metric(
                "📈 Return",
                f"{profit_loss_pct:.2f}%",
            )

        st.divider()

        left, right = st.columns(2)

        with left:

            chart_df = pd.DataFrame(
                {
                    "Type": [
                        "Investment",
                        "Current Value",
                    ],
                    "Value": [
                        total_investment,
                        current_value,
                    ],
                }
            )

            fig = px.bar(
                chart_df,
                x="Type",
                y="Value",
                text_auto=".2s",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        with right:

            st.dataframe(
                portfolio,
                width="stretch",
                hide_index=True,
            )

    # ========================================================
    # ANALYTICS
    # ========================================================

    elif section == "📊 Analytics":

        st.header(
            "📊 Portfolio Analytics"
        )

        try:

            summary = (
                calculate_portfolio_summary(
                    portfolio
                )
            )

        except Exception:

            summary = {}

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:

            st.metric(
                "Total Value",
                (
                    f"₹ "
                    f"{summary.get('total_value', current_value):,.2f}"
                ),
            )

        with col2:

            st.metric(
                "Profit / Loss",
                (
                    f"₹ "
                    f"{summary.get('profit_loss', profit_loss):,.2f}"
                ),
            )

        with col3:

            st.metric(
                "Risk Score",
                (
                    f"{summary.get('risk_score', 0):.1f} / 10"
                ),
            )

        st.divider()

        st.subheader(
            "🥧 Sector Allocation"
        )

        try:

            sector_data = (
                compute_sector_breakdown(
                    portfolio
                )
            )

        except Exception:

            sector_data = {}

        if sector_data:

            sector_df = pd.DataFrame(
                [
                    {
                        "Sector": sector,
                        "Value": data.get(
                            "value",
                            0,
                        ),
                    }
                    for sector, data
                    in sector_data.items()
                ]
            )

            fig = px.pie(
                sector_df,
                names="Sector",
                values="Value",
                hole=0.5,
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        else:

            st.info(
                "Sector information unavailable."
            )

    # ========================================================
    # BENCHMARK
    # ========================================================

    elif section == "🎯 Benchmark":

        st.header(
            "🎯 Benchmark Comparison"
        )

        benchmark_data = (
            get_market_data(
                ["^NSEI"]
            )
        )

        benchmark = (
            benchmark_data.get(
                "^NSEI",
                {},
            )
        )

        benchmark_change = (
            benchmark.get(
                "change_pct"
            )
        )

        if benchmark_change is not None:

            col1, col2 = (
                st.columns(2)
            )

            with col1:

                st.metric(
                    "Portfolio Return",
                    f"{profit_loss_pct:+.2f}%",
                )

            with col2:

                st.metric(
                    "Nifty 50 Daily Change",
                    f"{benchmark_change:+.2f}%",
                )

        else:

            st.warning(
                "Nifty 50 data unavailable."
            )

    # ========================================================
    # AI INSIGHTS
    # ========================================================

    elif section == "🤖 AI Insights":

        st.header(
            "🤖 AI Portfolio Insights"
        )

        # ----------------------------------------------------
        # HEALTH SCORE
        # ----------------------------------------------------

        with st.expander(
            "🩺 Portfolio Health Score",
            expanded=True,
        ):

            if st.button(
                "Generate Health Score",
                key="health_score_button",
            ):

                with st.spinner(
                    "Analyzing portfolio health..."
                ):

                    result = (
                        call_portfolio_ai_api(
                            "/api/ai/health-score",
                            portfolio,
                        )
                    )

                if result["success"]:

                    (
                        st.session_state
                        .health_result
                    ) = result["result"]

                else:

                    st.error(
                        result["error"]
                    )

            if st.session_state.health_result:

                st.markdown(
                    st.session_state
                    .health_result
                )

        # ----------------------------------------------------
        # RISK
        # ----------------------------------------------------

        with st.expander(
            "⚠️ AI Risk Analysis"
        ):

            if st.button(
                "Generate Risk Analysis",
                key="risk_button",
            ):

                with st.spinner(
                    "Analyzing portfolio risk..."
                ):

                    result = (
                        call_portfolio_ai_api(
                            "/api/ai/risk-analysis",
                            portfolio,
                        )
                    )

                if result["success"]:

                    (
                        st.session_state
                        .risk_result
                    ) = result["result"]

                else:

                    st.error(
                        result["error"]
                    )

            if st.session_state.risk_result:

                st.markdown(
                    st.session_state
                    .risk_result
                )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        with st.expander(
            "📋 AI Portfolio Summary"
        ):

            if st.button(
                "Generate Summary",
                key="summary_button",
            ):

                with st.spinner(
                    "Generating portfolio summary..."
                ):

                    result = (
                        call_portfolio_ai_api(
                            "/api/ai/portfolio-summary",
                            portfolio,
                        )
                    )

                if result["success"]:

                    (
                        st.session_state
                        .summary_result
                    ) = result["result"]

                else:

                    st.error(
                        result["error"]
                    )

            if st.session_state.summary_result:

                st.markdown(
                    st.session_state
                    .summary_result
                )

        # ----------------------------------------------------
        # IMPROVEMENT
        # ----------------------------------------------------

        with st.expander(
            "💡 Improvement Suggestions"
        ):

            if st.button(
                "Generate Suggestions",
                key="improvement_button",
            ):

                with st.spinner(
                    "Generating suggestions..."
                ):

                    result = (
                        call_portfolio_ai_api(
                            "/api/ai/improvement",
                            portfolio,
                        )
                    )

                if result["success"]:

                    (
                        st.session_state
                        .improvement_result
                    ) = result["result"]

                else:

                    st.error(
                        result["error"]
                    )

            if (
                st.session_state
                .improvement_result
            ):

                st.markdown(
                    st.session_state
                    .improvement_result
                )

    # ========================================================
    # STOCK ANALYSIS
    # ========================================================

    elif section == "📈 Stock Analysis":

        st.header(
            "📈 Stock Analysis"
        )

        stocks = (
            portfolio["Stock Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        selected_stock = (
            st.selectbox(
                "Select Stock",
                stocks,
            )
        )

        stock_info = (
            get_stock_info(
                selected_stock
            )
        )

        st.json(
            stock_info
        )

    # ========================================================
    # MARKET NEWS
    # ========================================================

    elif section == "📰 Market News":

        st.header(
            "📰 Latest Market News"
        )

        stocks = (
            portfolio["Stock Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        selected_stock = (
            st.selectbox(
                "Select Stock",
                stocks,
                key="news_stock",
            )
        )

        if st.button(
            "Fetch Latest News",
            key="fetch_news_button",
        ):

            try:

                articles = (
                    get_stock_news(
                        selected_stock
                    )
                )

                (
                    st.session_state
                    .news_data[
                        selected_stock
                    ]
                ) = articles

            except Exception as error:

                st.error(
                    f"News error: {error}"
                )

        articles = (
            st.session_state
            .news_data
            .get(
                selected_stock,
                [],
            )
        )

        for article in articles:

            st.markdown(
                "### "
                + article.get(
                    "Title",
                    article.get(
                        "title",
                        "News",
                    ),
                )
            )

            st.write(
                article.get(
                    "Description",
                    article.get(
                        "description",
                        "",
                    ),
                )
            )

    # ========================================================
    # ASK AI - HYBRID
    # ========================================================

    elif section == "💬 Ask AI":

        st.header(
            "💬 Ask AI"
        )

        st.caption(
            "Ask questions about your uploaded portfolio, "
            "stocks and financial concepts. "
            "The assistant uses both portfolio data "
            "and FAISS RAG knowledge."
        )

        # ----------------------------------------------------
        # BACKEND STATUS
        # ----------------------------------------------------

        backend_connected = (
            check_fastapi()
        )

        if backend_connected:

            st.success(
                "🟢 FastAPI AI + RAG backend connected"
            )

        else:

            st.error(
                "🔴 FastAPI backend unavailable"
            )

            st.code(
                "uvicorn fastapi_app:app --reload"
            )

        # ----------------------------------------------------
        # CONTEXT STATUS
        # ----------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            st.info(
                "📊 Portfolio context: Available"
            )

        with col2:

            st.info(
                "📚 FAISS RAG knowledge: Enabled"
            )

        # ----------------------------------------------------
        # QUESTION
        # ----------------------------------------------------

        question = st.text_area(
            "Your Question",
            placeholder=(
                "Examples:\n"
                "Which stock has the highest current value?\n"
                "What is P/E ratio?\n"
                "Explain concentration risk based on my portfolio."
            ),
            height=130,
            key="hybrid_question",
        )

        # ----------------------------------------------------
        # ASK
        # ----------------------------------------------------

        if st.button(
            "🤖 Ask AI",
            type="primary",
            key="hybrid_ask_button",
            width="stretch",
        ):

            if not question.strip():

                st.warning(
                    "Please enter a question."
                )

            elif not backend_connected:

                st.error(
                    "FastAPI backend is not running."
                )

            else:

                # --------------------------------------------
                # PREPARE NEWS DATA
                # --------------------------------------------

                ai_news_data = {}

                for stock, articles in (
                    st.session_state
                    .news_data
                    .items()
                ):

                    ai_news_data[stock] = []

                    for article in articles:

                        ai_news_data[
                            stock
                        ].append(
                            {
                                "title": (
                                    article.get(
                                        "Title",
                                        article.get(
                                            "title",
                                            "",
                                        ),
                                    )
                                ),
                                "description": (
                                    article.get(
                                        "Description",
                                        article.get(
                                            "description",
                                            "",
                                        ),
                                    )
                                ),
                                "source": (
                                    article.get(
                                        "source",
                                        "",
                                    )
                                ),
                                "published": (
                                    article.get(
                                        "published",
                                        "",
                                    )
                                ),
                            }
                        )

                # --------------------------------------------
                # IMPORTANT:
                # THIS CALLS /api/chat,
                # NOT /api/rag/query
                # --------------------------------------------

                with st.spinner(
                    "AI is analyzing your portfolio "
                    "and financial knowledge..."
                ):

                    result = call_chat_api(
                        question=question,
                        portfolio_df=portfolio,
                        news_data=ai_news_data,
                    )

                if result["success"]:

                    (
                        st.session_state
                        .chat_answer
                    ) = result["answer"]

                else:

                    st.error(
                        result["error"]
                    )

        # ----------------------------------------------------
        # DISPLAY ANSWER
        # ----------------------------------------------------

        if st.session_state.chat_answer:

            st.divider()

            st.subheader(
                "🤖 AI Answer"
            )

            st.markdown(
                st.session_state
                .chat_answer
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
