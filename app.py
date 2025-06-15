import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from streamlit_option_menu import option_menu
import time

# Load environment variables
load_dotenv()

# Initialize centralized logging
from logging_config import setup_logging, get_logger, log_performance, log_api_call, log_data_operation, log_calculation
logger = setup_logging()
app_logger = get_logger('streamlit_app')

# Database and services imports
from database import DatabaseManager, VarAnalysis
from alphavantage_service import AlphaVantageService
from var_calculator import VarCalculator

app_logger.info("Risk Analytics Pro - Streamlit application starting")

# Page configuration
st.set_page_config(
    page_title="Risk Analytics Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for financial styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 1rem;
    }
    .financial-header {
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    .risk-metric {
        background-color: #FEF2F2;
        border-left: 4px solid #DC2626;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .profit-metric {
        background-color: #F0FDF4;
        border-left: 4px solid #059669;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Initialize services
    db_manager = DatabaseManager()
    alphavantage = AlphaVantageService()
    
    # Check if we have any analysis data to determine if we should show landing page
    fund_analysis = None
    selected_symbol = None
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Key input (properly masked)
        default_key = os.getenv("ALPHAVANTAGE_API_KEY", "ERBZK88O5KLSPYPL")
        api_key = st.text_input(
            "Stock API Key", 
            value="",
            type="password",
            placeholder="Enter your API key (optional - default key will be used)",
            help="Your API key is masked for security"
        )
        
        # Use default if no key entered
        if not api_key:
            api_key = default_key
            st.info("Using default API key")
        
        # Fund definitions
        fund_options = {
            "FCNTX": "Fidelity Contrafund",
            "VFIAX": "Vanguard 500 Index Fund",
            "FXNAX": "Fidelity US Bond Index Fund", 
            "VTSMX": "Vanguard Total Stock Market Fund",
            "FSKAX": "Fidelity Total Market Index Fund"
        }
        
        # Bulk fetch all funds button
        if st.button("🚀 Fetch All Funds", type="primary", use_container_width=True):
            app_logger.info("User initiated bulk fetch for all funds")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_funds = len(fund_options)
            successful_analyses = 0
            
            for i, (symbol, name) in enumerate(fund_options.items()):
                try:
                    progress = (i) / total_funds
                    progress_bar.progress(progress)
                    status_text.text(f"Analyzing {symbol} - {name}...")
                    
                    app_logger.info(f"Fetching data for {symbol}")
                    alphavantage.api_key = api_key
                    prices = alphavantage.get_recent_prices(symbol, days=1095)
                    
                    if len(prices) == 0:
                        app_logger.warning(f"No price data found for {symbol}")
                        continue
                    
                    app_logger.info(f"Retrieved {len(prices)} price records for {symbol}")
                    
                    # Store in database
                    fund_id = db_manager.create_or_get_fund(symbol, name)
                    db_manager.store_fund_prices(fund_id, prices)
                    
                    # Calculate VaR
                    close_prices = [p['close'] for p in prices]
                    var_results = VarCalculator.calculate_var(close_prices)
                    
                    # Convert to camelCase for database storage
                    camelCase_results = {
                        'parametricVar5': var_results['parametric_var_5'],
                        'parametricVar1': var_results['parametric_var_1'],
                        'historicalVar5': var_results['historical_var_5'],
                        'historicalVar1': var_results['historical_var_1'],
                        'historicalCvar5': var_results['historical_cvar_5'],
                        'historicalCvar1': var_results['historical_cvar_1'],
                        'monteCarloVar5': var_results['monte_carlo_var_5'],
                        'monteCarloVar1': var_results['monte_carlo_var_1'],
                        'monteCarloCvar5': var_results['monte_carlo_cvar_5'],
                        'monteCarloCvar1': var_results['monte_carlo_cvar_1'],
                        'dailyMean': var_results['daily_mean'],
                        'dailyStd': var_results['daily_std'],
                        'monthlyMean': var_results['monthly_mean'],
                        'monthlyStd': var_results['monthly_std'],
                        'skewness': var_results['skewness'],
                        'kurtosis': var_results['kurtosis'],
                        'normalityPValue': var_results['normality_p_value'],
                        'sharpeRatio': var_results['sharpe_ratio'],
                        'annualReturn': var_results['annual_return'],
                        'dataPoints': var_results['data_points']
                    }
                    
                    # Store analysis
                    analysis_id = db_manager.store_var_analysis(fund_id, camelCase_results)
                    app_logger.info(f"Successfully analyzed {symbol} - Analysis ID: {analysis_id}")
                    successful_analyses += 1
                    
                except Exception as e:
                    app_logger.error(f"Error analyzing {symbol}: {str(e)}")
                    continue
            
            # Update progress to complete
            progress_bar.progress(1.0)
            status_text.text(f"✅ Completed! Successfully analyzed {successful_analyses}/{total_funds} funds")
            
            if successful_analyses > 0:
                st.success(f"Successfully analyzed {successful_analyses} funds. Use the dropdown below to view results.")
                st.rerun()
            else:
                st.error("No funds were successfully analyzed. Please check your API key and try again.")
        
        st.divider()
        
        # Fund selection dropdown for viewing analysis
        st.markdown("### 📊 View Analysis Results")
        
        # Get funds that have been analyzed
        try:
            analyzed_funds_query = """
            SELECT DISTINCT f.symbol, f.name 
            FROM funds f 
            JOIN var_analyses v ON f.id = v.fund_id 
            ORDER BY f.symbol
            """
            analyzed_funds = db_manager.execute_query(analyzed_funds_query)
            
            if analyzed_funds:
                fund_choices = {fund['symbol']: fund['name'] for fund in analyzed_funds}
                selected_symbol = st.selectbox(
                    "Select Fund to View",
                    options=list(fund_choices.keys()),
                    format_func=lambda x: f"{x} - {fund_choices[x]}"
                )
            else:
                st.info("No funds have been analyzed yet. Click 'Fetch All Funds' to begin.")
                selected_symbol = None
                
        except Exception as e:
            app_logger.error(f"Error retrieving analyzed funds: {e}")
            st.warning("Unable to retrieve fund list. Using default options.")
            selected_symbol = st.selectbox(
                "Select Mutual Fund",
                options=list(fund_options.keys()),
                format_func=lambda x: f"{x} - {fund_options[x]}"
            )
        
        # Individual fetch button (for single fund analysis)
        if selected_symbol and st.button("🔄 Re-analyze Selected Fund", help="Re-fetch and analyze only the selected fund"):
            app_logger.info(f"User initiated re-analysis for {selected_symbol}")
            with st.spinner("Re-fetching data and running analysis..."):
                try:
                    # Get fund name
                    fund_name = fund_options.get(selected_symbol, f"{selected_symbol} Fund")
                    
                    # Fetch data
                    app_logger.info(f"Fetching data for {selected_symbol}")
                    alphavantage.api_key = api_key
                    prices = alphavantage.get_recent_prices(selected_symbol, days=1095)
                    
                    if len(prices) == 0:
                        app_logger.warning(f"No price data found for {selected_symbol}")
                        st.error("No price data found for this symbol")
                        st.stop()
                    
                    app_logger.info(f"Retrieved {len(prices)} price records for {selected_symbol}")
                    
                    # Store in database
                    fund_id = db_manager.create_or_get_fund(selected_symbol, fund_name)
                    db_manager.store_fund_prices(fund_id, prices)
                    
                    # Calculate VaR
                    close_prices = [p['close'] for p in prices]
                    var_results = VarCalculator.calculate_var(close_prices)
                    
                    # Convert to camelCase for database storage
                    camelCase_results = {
                        'parametricVar5': var_results['parametric_var_5'],
                        'parametricVar1': var_results['parametric_var_1'],
                        'historicalVar5': var_results['historical_var_5'],
                        'historicalVar1': var_results['historical_var_1'],
                        'historicalCvar5': var_results['historical_cvar_5'],
                        'historicalCvar1': var_results['historical_cvar_1'],
                        'monteCarloVar5': var_results['monte_carlo_var_5'],
                        'monteCarloVar1': var_results['monte_carlo_var_1'],
                        'monteCarloCvar5': var_results['monte_carlo_cvar_5'],
                        'monteCarloCvar1': var_results['monte_carlo_cvar_1'],
                        'dailyMean': var_results['daily_mean'],
                        'dailyStd': var_results['daily_std'],
                        'monthlyMean': var_results['monthly_mean'],
                        'monthlyStd': var_results['monthly_std'],
                        'skewness': var_results['skewness'],
                        'kurtosis': var_results['kurtosis'],
                        'normalityPValue': var_results['normality_p_value'],
                        'sharpeRatio': var_results['sharpe_ratio'],
                        'annualReturn': var_results['annual_return'],
                        'dataPoints': var_results['data_points']
                    }
                    
                    # Store analysis
                    analysis_id = db_manager.store_var_analysis(fund_id, camelCase_results)
                    
                    app_logger.info(f"Successfully re-analyzed {selected_symbol} - Analysis ID: {analysis_id}")
                    st.success(f"Successfully re-analyzed {len(prices)} price records for {selected_symbol}")
                    st.rerun()
                    
                except Exception as e:
                    app_logger.error(f"Error during re-analysis for {selected_symbol}: {str(e)}")
                    st.error(f"Error: {str(e)}")
    
    # Get latest analysis for selected fund
    fund_analysis = db_manager.get_fund_analysis(selected_symbol) if selected_symbol else None
    
    # Display landing page if no analysis data exists
    if not fund_analysis:
        display_landing_page()
    else:
        # Main content tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview", 
            "⚠️ VaR Analysis", 
            "📈 Distribution", 
            "🎲 Monte Carlo", 
            "💾 Data Export"
        ])
        
        with tab1:
            display_overview(fund_analysis, selected_symbol, db_manager)
        
        with tab2:
            display_var_analysis(fund_analysis)
            
        with tab3:
            display_returns_distribution(db_manager, selected_symbol)
            
        with tab4:
            display_monte_carlo(fund_analysis)
            
        with tab5:
            display_data_export(db_manager, selected_symbol)

def display_landing_page():
    """Display welcome landing page with application information"""
    
    # Header with logo-style design
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0; background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 50%, #059669 100%); border-radius: 1rem; margin-bottom: 2rem;">
        <h1 style="color: white; font-size: 3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">📊 Risk Analytics Pro</h1>
        <p style="color: #E5E7EB; font-size: 1.2rem; margin: 0.5rem 0 0 0;">Professional Investment Risk Analysis Dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Welcome section
    st.markdown("""
    ## Welcome to Risk Analytics Pro
    
    This interactive dashboard provides comprehensive Value at Risk (VaR) analysis for mutual funds and investment portfolios. 
    Our platform leverages multiple risk assessment methodologies to deliver institutional-grade risk analytics.
    
    **The analysis covers multiple risk calculation methods:**
    - **Parametric VaR**: Normal distribution-based risk estimates
    - **Historical VaR**: Empirical distribution analysis from actual returns
    - **Monte Carlo VaR**: Simulation-based risk modeling with 10,000+ iterations
    """)
    
    # Featured capabilities
    st.markdown("## Featured Capabilities")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📈 Market Data Integration
        - Real-time data via AlphaVantage API
        - 3+ years of historical pricing
        - Daily OHLCV data processing
        - Automated data validation
        """)
    
    with col2:
        st.markdown("""
        ### ⚠️ Risk Metrics
        - VaR at 95% and 99% confidence levels
        - Conditional VaR (Expected Shortfall)
        - Volatility and correlation analysis
        - Distribution testing and normality checks
        """)
    
    with col3:
        st.markdown("""
        ### 📊 Analytics & Reporting
        - Interactive visualizations
        - Statistical analysis dashboard
        - Monte Carlo simulation results
        - Data export functionality
        """)
    
    # Supported funds
    st.markdown("## Supported Mutual Funds")
    
    funds_data = {
        "Symbol": ["FCNTX", "VFIAX", "FXNAX", "VTSMX", "FSKAX"],
        "Fund Name": [
            "Fidelity Contrafund",
            "Vanguard 500 Index Fund",
            "Fidelity US Bond Index Fund",
            "Vanguard Total Stock Market Index",
            "Fidelity Total Market Index Fund"
        ],
        "Category": [
            "Large Cap Growth",
            "Large Cap Blend",
            "Intermediate Bond",
            "Total Stock Market",
            "Total Stock Market"
        ],
        "Risk Level": ["High", "Medium", "Low", "Medium", "Medium"]
    }
    
    st.dataframe(pd.DataFrame(funds_data), hide_index=True, use_container_width=True)
    
    # Getting started
    st.markdown("""
    ## Getting Started
    
    1. **Select a Fund**: Choose from our supported mutual funds in the sidebar
    2. **Configure API**: Enter your AlphaVantage API key (optional - default provided)
    3. **Fetch & Analyze**: Click the button to retrieve data and run comprehensive VaR analysis
    4. **Explore Results**: Navigate through the analysis tabs to explore risk metrics and visualizations
    
    ### About the Analysis
    
    Our VaR analysis processes 3+ years of daily returns data to calculate:
    - **Daily and Monthly Statistics**: Mean returns, volatility, and distribution characteristics
    - **Risk Metrics**: Value at Risk and Conditional Value at Risk at multiple confidence levels
    - **Statistical Tests**: Normality testing, skewness, and kurtosis analysis
    - **Performance Metrics**: Sharpe ratio and risk-adjusted returns
    
    **Ready to begin?** Select a fund from the sidebar and click "Fetch & Analyze" to start your risk analysis.
    """)

def display_overview(fund_analysis, selected_symbol, db_manager):
    """Display overview metrics"""
    st.header("📊 Key Metrics Overview")
    
    if fund_analysis:
        app_logger.info(f"Displaying overview for {selected_symbol} with analysis data")
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Get latest price data directly from fund_prices table
            current_nav = 0
            try:
                price_query = """
                SELECT fp.close 
                FROM fund_prices fp 
                JOIN funds f ON fp.fund_id = f.id 
                WHERE f.symbol = ? 
                ORDER BY fp.date DESC 
                LIMIT 1
                """
                price_results = db_manager.execute_query(price_query, (selected_symbol,))
                if price_results and len(price_results) > 0 and price_results[0]['close'] is not None:
                    current_nav = float(price_results[0]['close'])
                    app_logger.info(f"Retrieved NAV for {selected_symbol}: ${current_nav:.2f}")
                else:
                    app_logger.warning(f"No valid price data found for {selected_symbol}")
            except Exception as e:
                app_logger.error(f"Error retrieving NAV for {selected_symbol}: {e}")
            
            # Display NAV metric
            if current_nav > 0:
                st.metric(
                    "Current NAV",
                    f"${current_nav:.2f}",
                    delta=f"{selected_symbol}"
                )
            else:
                st.metric(
                    "Current NAV",
                    "No Data",
                    delta="Check price data"
                )
        
        with col2:
            daily_vol = float(fund_analysis.get('daily_std', 0)) * 100
            st.metric(
                "Daily Volatility",
                f"{daily_vol:.2f}%",
                delta="Annualized"
            )
        
        with col3:
            sharpe_ratio = float(fund_analysis.get('sharpe_ratio', 0))
            st.metric(
                "Sharpe Ratio",
                f"{sharpe_ratio:.3f}",
                delta="Risk-adjusted return"
            )
        
        with col4:
            data_points = fund_analysis.get('data_points', 0)
            st.metric(
                "Data Points",
                f"{data_points:,}",
                delta="3-year analysis"
            )
        
        # Statistical analysis
        st.subheader("Statistical Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Return Statistics")
            stats_data = {
                "Metric": ["Daily Mean", "Daily Std", "Monthly Mean", "Monthly Std", "Annual Return"],
                "Value": [
                    f"{float(fund_analysis.get('daily_mean', 0)) * 100:.3f}%",
                    f"{float(fund_analysis.get('daily_std', 0)) * 100:.3f}%", 
                    f"{float(fund_analysis.get('monthly_mean', 0)) * 100:.2f}%",
                    f"{float(fund_analysis.get('monthly_std', 0)) * 100:.2f}%",
                    f"{float(fund_analysis.get('annual_return', 0)) * 100:.2f}%"
                ]
            }
            st.dataframe(pd.DataFrame(stats_data), hide_index=True)
        
        with col2:
            st.markdown("### Distribution Tests")
            
            skewness = float(fund_analysis.get('skewness', 0))
            kurtosis = float(fund_analysis.get('kurtosis', 0))
            normality_p = float(fund_analysis.get('normality_p_value', 1))
            
            # Normality test interpretation
            normality_status = "Normal" if normality_p >= 0.05 else "Non-normal"
            skew_desc = "Right-skewed" if skewness > 0.1 else "Left-skewed" if skewness < -0.1 else "Symmetric"
            kurt_desc = "Fat tails" if kurtosis > 3.5 else "Thin tails" if kurtosis < 2.5 else "Normal tails"
            
            test_data = {
                "Test": ["Normality (p-value)", "Skewness", "Kurtosis", "Distribution", "Tail Risk"],
                "Result": [
                    f"{normality_p:.6f}",
                    f"{skewness:.3f}",
                    f"{kurtosis:.3f}",
                    normality_status,
                    kurt_desc
                ],
                "Interpretation": [
                    normality_status,
                    skew_desc,
                    kurt_desc,
                    "Parametric VaR reliable" if normality_p >= 0.05 else "Use Historical VaR",
                    "Higher tail risk" if kurtosis > 3.5 else "Normal tail risk"
                ]
            }
            st.dataframe(pd.DataFrame(test_data), hide_index=True)
            
    else:
        st.info("No analysis data available. Please select a fund and click 'Fetch & Analyze' to begin.")

def display_var_analysis(fund_analysis):
    """Display VaR analysis results"""
    st.header("⚠️ Value at Risk Analysis")
    
    if fund_analysis:
        # VaR comparison table
        var_data = {
            "Method": ["Parametric", "Historical", "Monte Carlo"],
            "VaR 5%": [
                f"{float(fund_analysis.get('parametric_var_5', 0)) * 100:.2f}%",
                f"{float(fund_analysis.get('historical_var_5', 0)) * 100:.2f}%",
                f"{float(fund_analysis.get('monte_carlo_var_5', 0)) * 100:.2f}%"
            ],
            "VaR 1%": [
                f"{float(fund_analysis.get('parametric_var_1', 0)) * 100:.2f}%",
                f"{float(fund_analysis.get('historical_var_1', 0)) * 100:.2f}%",
                f"{float(fund_analysis.get('monte_carlo_var_1', 0)) * 100:.2f}%"
            ],
            "CVaR 5%": [
                "N/A",
                f"{float(fund_analysis.get('historical_cvar_5', 0)) * 100:.2f}%",
                f"{float(fund_analysis.get('monte_carlo_cvar_5', 0)) * 100:.2f}%"
            ],
            "CVaR 1%": [
                "N/A", 
                f"{float(fund_analysis.get('historical_cvar_1', 0)) * 100:.2f}%",
                f"{float(fund_analysis.get('monte_carlo_cvar_1', 0)) * 100:.2f}%"
            ]
        }
        
        st.dataframe(pd.DataFrame(var_data), hide_index=True)
        
        # VaR visualization
        methods = ["Parametric", "Historical", "Monte Carlo"]
        var_5_values = [
            float(fund_analysis.get('parametric_var_5', 0)) * 100,
            float(fund_analysis.get('historical_var_5', 0)) * 100,
            float(fund_analysis.get('monte_carlo_var_5', 0)) * 100
        ]
        var_1_values = [
            float(fund_analysis.get('parametric_var_1', 0)) * 100,
            float(fund_analysis.get('historical_var_1', 0)) * 100,
            float(fund_analysis.get('monte_carlo_var_1', 0)) * 100
        ]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name='VaR 5%', x=methods, y=var_5_values, marker_color='#DC2626'))
        fig.add_trace(go.Bar(name='VaR 1%', x=methods, y=var_1_values, marker_color='#991B1B'))
        
        fig.update_layout(
            title='Value at Risk Comparison',
            xaxis_title='Method',
            yaxis_title='VaR (%)',
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No VaR analysis data available. Please run analysis first.")

def display_returns_distribution(db_manager, selected_symbol):
    """Display returns distribution analysis"""
    st.header("📈 Returns Distribution")
    
    try:
        returns_data = db_manager.get_fund_returns(selected_symbol, limit=1000)
        
        if returns_data:
            returns = [r['return'] for r in returns_data]
            
            # Histogram
            fig = px.histogram(
                x=returns, 
                nbins=50, 
                title=f"Daily Returns Distribution - {selected_symbol}",
                labels={'x': 'Daily Return', 'y': 'Frequency'}
            )
            fig.update_traces(marker_color='#1E3A8A')
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary statistics
            st.subheader("Distribution Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Mean", f"{np.mean(returns)*100:.3f}%")
            with col2:
                st.metric("Std Dev", f"{np.std(returns)*100:.3f}%")
            with col3:
                st.metric("Skewness", f"{pd.Series(returns).skew():.3f}")
            with col4:
                st.metric("Kurtosis", f"{pd.Series(returns).kurtosis():.3f}")
        else:
            st.info("No returns data available. Please run analysis first.")
    except Exception as e:
        st.error(f"Error displaying returns distribution: {e}")

def display_monte_carlo(fund_analysis):
    """Display Monte Carlo simulation"""
    st.header("🎲 Monte Carlo Simulation")
    
    if fund_analysis:
        daily_mean = float(fund_analysis.get('daily_mean', 0))
        daily_std = float(fund_analysis.get('daily_std', 0))
        
        # Generate Monte Carlo simulation
        n_simulations = 10000
        simulated_returns = np.random.normal(daily_mean, daily_std, n_simulations)
        
        # Histogram of simulated returns
        fig = px.histogram(
            x=simulated_returns * 100,
            nbins=100,
            title=f"Monte Carlo Simulation - {n_simulations:,} Iterations",
            labels={'x': 'Simulated Daily Return (%)', 'y': 'Frequency'}
        )
        fig.update_traces(marker_color='#059669')
        st.plotly_chart(fig, use_container_width=True)
        
        # Simulation statistics
        st.subheader("Simulation Results")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Mean", f"{np.mean(simulated_returns)*100:.3f}%")
        with col2:
            st.metric("5th Percentile", f"{np.percentile(simulated_returns, 5)*100:.3f}%")
        with col3:
            st.metric("1st Percentile", f"{np.percentile(simulated_returns, 1)*100:.3f}%")
        with col4:
            st.metric("Worst Case", f"{np.min(simulated_returns)*100:.3f}%")
    else:
        st.info("No analysis data available for Monte Carlo simulation.")

def display_data_export(db_manager, selected_symbol):
    """Display data export options with querying functionality and schema documentation"""
    st.header("💾 Data Export & Query Interface")
    
    # Database Schema Documentation
    with st.expander("📋 Database Schema Documentation", expanded=False):
        st.markdown("""
        ### Database Tables and Structure
        
        **funds**
        - `id`: INTEGER PRIMARY KEY (Auto-increment)
        - `symbol`: TEXT NOT NULL UNIQUE (Fund ticker symbol)
        - `name`: TEXT NOT NULL (Full fund name)
        - `description`: TEXT (Optional fund description)
        - `is_active`: BOOLEAN DEFAULT 1 (Active status)
        - `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        
        **fund_prices**
        - `id`: INTEGER PRIMARY KEY (Auto-increment)
        - `fund_id`: INTEGER (Foreign key to funds.id)
        - `date`: DATE NOT NULL (Trading date)
        - `open`: REAL (Opening price)
        - `high`: REAL (Daily high price)
        - `low`: REAL (Daily low price)
        - `close`: REAL (Closing price)
        - `volume`: INTEGER (Trading volume)
        - `return`: REAL (Daily return percentage)
        
        **var_analyses**
        - `id`: INTEGER PRIMARY KEY (Auto-increment)
        - `fund_id`: INTEGER (Foreign key to funds.id)
        - `parametric_var_5`: REAL (5% Parametric VaR)
        - `parametric_var_1`: REAL (1% Parametric VaR)
        - `historical_var_5`: REAL (5% Historical VaR)
        - `historical_var_1`: REAL (1% Historical VaR)
        - `historical_cvar_5`: REAL (5% Historical CVaR)
        - `historical_cvar_1`: REAL (1% Historical CVaR)
        - `monte_carlo_var_5`: REAL (5% Monte Carlo VaR)
        - `monte_carlo_var_1`: REAL (1% Monte Carlo VaR)
        - `monte_carlo_cvar_5`: REAL (5% Monte Carlo CVaR)
        - `monte_carlo_cvar_1`: REAL (1% Monte Carlo CVaR)
        - `daily_mean`: REAL (Daily mean return)
        - `daily_std`: REAL (Daily standard deviation)
        - `monthly_mean`: REAL (Monthly mean return)
        - `monthly_std`: REAL (Monthly standard deviation)
        - `skewness`: REAL (Return distribution skewness)
        - `kurtosis`: REAL (Return distribution kurtosis)
        - `normality_p_value`: REAL (Normality test p-value)
        - `sharpe_ratio`: REAL (Risk-adjusted return ratio)
        - `annual_return`: REAL (Annualized return)
        - `data_points`: INTEGER (Number of data points analyzed)
        - `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
    
    # Query Interface
    st.subheader("🔍 Custom Data Query")
    
    query_tabs = st.tabs(["Quick Queries", "Custom SQL", "Filtered Export"])
    
    with query_tabs[0]:
        st.markdown("### Pre-built Queries")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Latest VaR Analysis"):
                try:
                    query = """
                    SELECT f.symbol, f.name, v.parametric_var_5, v.historical_var_5, 
                           v.monte_carlo_var_5, v.sharpe_ratio, v.created_at
                    FROM var_analyses v
                    JOIN funds f ON v.fund_id = f.id
                    ORDER BY v.created_at DESC
                    LIMIT 10
                    """
                    results = db_manager.execute_query(query)
                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df, hide_index=True, use_container_width=True)
                    else:
                        st.info("No VaR analysis data found")
                except Exception as e:
                    st.error(f"Query error: {e}")
        
        with col2:
            if st.button("Price Summary by Fund"):
                try:
                    query = """
                    SELECT f.symbol, f.name, 
                           COUNT(fp.id) as price_records,
                           MIN(fp.date) as earliest_date,
                           MAX(fp.date) as latest_date,
                           ROUND(AVG(fp.close), 2) as avg_price
                    FROM funds f
                    LEFT JOIN fund_prices fp ON f.id = fp.fund_id
                    GROUP BY f.id, f.symbol, f.name
                    ORDER BY price_records DESC
                    """
                    results = db_manager.execute_query(query)
                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df, hide_index=True, use_container_width=True)
                    else:
                        st.info("No price data found")
                except Exception as e:
                    st.error(f"Query error: {e}")
        
        # Risk comparison query
        if st.button("Risk Metrics Comparison", use_container_width=True):
            try:
                query = """
                SELECT f.symbol, f.name,
                       ROUND(v.parametric_var_5 * 100, 2) as param_var_5_pct,
                       ROUND(v.historical_var_5 * 100, 2) as hist_var_5_pct,
                       ROUND(v.monte_carlo_var_5 * 100, 2) as mc_var_5_pct,
                       ROUND(v.daily_std * 100, 2) as daily_vol_pct,
                       ROUND(v.sharpe_ratio, 3) as sharpe_ratio
                FROM var_analyses v
                JOIN funds f ON v.fund_id = f.id
                ORDER BY v.created_at DESC
                """
                results = db_manager.execute_query(query)
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, hide_index=True, use_container_width=True)
                else:
                    st.info("No analysis data found for comparison")
            except Exception as e:
                st.error(f"Query error: {e}")
    
    with query_tabs[1]:
        st.markdown("### Custom SQL Query")
        st.warning("⚠️ Advanced users only. Be careful with SQL syntax.")
        
        custom_query = st.text_area(
            "Enter SQL Query:",
            placeholder="""SELECT f.symbol, COUNT(fp.id) as records 
FROM funds f 
LEFT JOIN fund_prices fp ON f.id = fp.fund_id 
GROUP BY f.symbol;""",
            height=100
        )
        
        if st.button("Execute Query"):
            if custom_query.strip():
                try:
                    # Basic SQL injection protection
                    dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
                    query_upper = custom_query.upper()
                    if any(keyword in query_upper for keyword in dangerous_keywords):
                        st.error("Potentially dangerous SQL operations are not allowed.")
                    else:
                        results = db_manager.execute_query(custom_query)
                        if results:
                            df = pd.DataFrame(results)
                            st.dataframe(df, hide_index=True, use_container_width=True)
                            
                            # Option to download query results
                            csv_data = df.to_csv(index=False)
                            st.download_button(
                                label="Download Query Results as CSV",
                                data=csv_data,
                                file_name="query_results.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("Query returned no results")
                except Exception as e:
                    st.error(f"Query execution error: {e}")
            else:
                st.warning("Please enter a SQL query")
    
    with query_tabs[2]:
        st.markdown("### Filtered Data Export")
        
        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=365))
        with col2:
            end_date = st.date_input("End Date", value=datetime.now())
        
        # Export options
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            st.markdown("#### Analysis Data Export")
            if st.button("Export Analysis Results (JSON)"):
                try:
                    data = db_manager.export_fund_data(selected_symbol, format='json')
                    if data:
                        st.download_button(
                            label="Download Analysis JSON",
                            data=data,
                            file_name=f"{selected_symbol}_analysis_{datetime.now().strftime('%Y%m%d')}.json",
                            mime="application/json"
                        )
                    else:
                        st.warning("No analysis data available for export")
                except Exception as e:
                    st.error(f"Export error: {e}")
        
        with export_col2:
            st.markdown("#### Price Data Export")
            if st.button("Export Price Data (CSV)"):
                try:
                    # Get filtered price data
                    query = """
                    SELECT fp.date, fp.open, fp.high, fp.low, fp.close, fp.volume, fp.return
                    FROM fund_prices fp
                    JOIN funds f ON fp.fund_id = f.id
                    WHERE f.symbol = ? AND fp.date BETWEEN ? AND ?
                    ORDER BY fp.date DESC
                    """
                    results = db_manager.execute_query(query, (selected_symbol, start_date, end_date))
                    
                    if results:
                        df = pd.DataFrame(results)
                        csv_data = df.to_csv(index=False)
                        st.download_button(
                            label="Download Price CSV",
                            data=csv_data,
                            file_name=f"{selected_symbol}_prices_{start_date}_{end_date}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("No price data available for the selected date range")
                except Exception as e:
                    st.error(f"Export error: {e}")
    
    # Database statistics
    st.subheader("📊 Database Statistics")
    try:
        db_info = db_manager.get_database_info()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Funds", db_info.get('total_funds', 0))
        with col2:
            st.metric("Price Records", db_info.get('total_prices', 0))
        with col3:
            st.metric("Analyses", db_info.get('total_analyses', 0))
        with col4:
            st.metric("Database Size", f"{db_info.get('db_size_mb', 0):.1f} MB")
            
    except Exception as e:
        st.error(f"Error retrieving database statistics: {e}")

if __name__ == "__main__":
    main()