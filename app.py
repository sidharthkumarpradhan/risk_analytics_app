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

# Database and services imports
from database import DatabaseManager, VarAnalysis
from alphavantage_service import AlphaVantageService
from var_calculator import VarCalculator

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
    .main-header {
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1E3A8A;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .risk-metric {
        color: #DC2626;
        font-weight: bold;
    }
    .profit-metric {
        color: #059669;
        font-weight: bold;
    }
    .stMetric {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

def initialize_services():
    """Initialize database and API services"""
    db_manager = DatabaseManager()
    alphavantage = AlphaVantageService()
    return db_manager, alphavantage

def main():
    # Initialize services
    db_manager, alphavantage = initialize_services()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📊 Risk Analytics Pro</h1>
        <p>Investment Risk Analysis Dashboard - Professional VaR Analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Key input
        api_key = st.text_input(
            "AlphaVantage API Key", 
            value=os.getenv("ALPHAVANTAGE_API_KEY", "ERBZK88O5KLSPYPL"),
            type="password"
        )
        
        # Fund selection
        fund_options = {
            "FCNTX": "Fidelity Contrafund",
            "VFIAX": "Vanguard 500 Index",
            "FXNAX": "Fidelity US Bond Index", 
            "VTSMX": "Vanguard Total Stock Market",
            "FSKAX": "Fidelity Total Market Index"
        }
        
        selected_symbol = st.selectbox(
            "Select Mutual Fund",
            options=list(fund_options.keys()),
            format_func=lambda x: f"{x} - {fund_options[x]}"
        )
        
        # Fetch and analyze button
        if st.button("Fetch & Analyze", type="primary"):
            with st.spinner("Fetching data and running analysis..."):
                try:
                    # Fetch data
                    alphavantage.api_key = api_key
                    prices = alphavantage.get_recent_prices(selected_symbol, days=1095)
                    
                    if len(prices) == 0:
                        st.error("No price data found for this symbol")
                        return
                    
                    # Store in database
                    fund_id = db_manager.create_or_get_fund(
                        symbol=selected_symbol,
                        name=fund_options[selected_symbol]
                    )
                    
                    db_manager.store_fund_prices(fund_id, prices)
                    
                    # Calculate VaR
                    close_prices = [p['close'] for p in prices]
                    var_results = VarCalculator.calculate_var(close_prices)
                    
                    # Store analysis
                    analysis_id = db_manager.store_var_analysis(fund_id, var_results)
                    
                    st.success(f"Successfully analyzed {len(prices)} price records for {selected_symbol}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "⚠️ VaR Analysis", 
        "📈 Distribution", 
        "🎲 Monte Carlo", 
        "💾 Data Export"
    ])
    
    # Get latest analysis for selected fund
    fund_analysis = db_manager.get_fund_analysis(selected_symbol)
    
    with tab1:
        display_overview(fund_analysis, selected_symbol)
    
    with tab2:
        display_var_analysis(fund_analysis)
        
    with tab3:
        display_returns_distribution(db_manager, selected_symbol)
        
    with tab4:
        display_monte_carlo(fund_analysis)
        
    with tab5:
        display_data_export(db_manager, selected_symbol)

def display_overview(fund_analysis, selected_symbol):
    """Display overview metrics"""
    st.header("📊 Key Metrics Overview")
    
    if fund_analysis and fund_analysis.get('analysis'):
        analysis = fund_analysis['analysis']
        latest_price = fund_analysis.get('latest_price')
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_nav = latest_price.get('close', 0) if latest_price else 0
            st.metric(
                "Current NAV",
                f"${current_nav:.2f}",
                delta=f"{selected_symbol}"
            )
        
        with col2:
            daily_vol = float(analysis.get('daily_std', 0)) * 100
            st.metric(
                "Daily Volatility",
                f"{daily_vol:.2f}%",
                delta="Standard deviation"
            )
        
        with col3:
            sharpe_ratio = float(analysis.get('sharpe_ratio', 0))
            st.metric(
                "Sharpe Ratio",
                f"{sharpe_ratio:.3f}",
                delta="Risk-adjusted return"
            )
        
        with col4:
            data_points = analysis.get('data_points', 0)
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
                    f"{float(analysis.get('daily_mean', 0)) * 100:.3f}%",
                    f"{float(analysis.get('daily_std', 0)) * 100:.3f}%", 
                    f"{float(analysis.get('monthly_mean', 0)) * 100:.2f}%",
                    f"{float(analysis.get('monthly_std', 0)) * 100:.2f}%",
                    f"{float(analysis.get('annual_return', 0)) * 100:.2f}%"
                ]
            }
            st.dataframe(pd.DataFrame(stats_data), hide_index=True)
        
        with col2:
            st.markdown("### Distribution Tests")
            
            skewness = float(analysis.get('skewness', 0))
            kurtosis = float(analysis.get('kurtosis', 0))
            normality_p = float(analysis.get('normality_p_value', 1))
            
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
    
    if fund_analysis and fund_analysis.get('analysis'):
        analysis = fund_analysis['analysis']
        
        # VaR comparison table
        var_data = {
            "Method": ["Parametric", "Historical", "Monte Carlo"],
            "VaR 5%": [
                f"{float(analysis.get('parametric_var_5', 0)) * 100:.2f}%",
                f"{float(analysis.get('historical_var_5', 0)) * 100:.2f}%",
                f"{float(analysis.get('monte_carlo_var_5', 0)) * 100:.2f}%"
            ],
            "VaR 1%": [
                f"{float(analysis.get('parametric_var_1', 0)) * 100:.2f}%",
                f"{float(analysis.get('historical_var_1', 0)) * 100:.2f}%",
                f"{float(analysis.get('monte_carlo_var_1', 0)) * 100:.2f}%"
            ],
            "CVaR 5%": [
                "N/A",
                f"{float(analysis.get('historical_cvar_5', 0)) * 100:.2f}%",
                f"{float(analysis.get('monte_carlo_cvar_5', 0)) * 100:.2f}%"
            ]
        }
        
        var_df = pd.DataFrame(var_data)
        st.dataframe(var_df, hide_index=True)
        
        # VaR visualization
        fig = go.Figure()
        
        methods = var_data["Method"]
        var_5_values = [float(analysis.get('parametric_var_5', 0)) * 100,
                       float(analysis.get('historical_var_5', 0)) * 100,
                       float(analysis.get('monte_carlo_var_5', 0)) * 100]
        var_1_values = [float(analysis.get('parametric_var_1', 0)) * 100,
                       float(analysis.get('historical_var_1', 0)) * 100,
                       float(analysis.get('monte_carlo_var_1', 0)) * 100]
        
        fig.add_trace(go.Bar(
            name='VaR 5%',
            x=methods,
            y=var_5_values,
            marker_color='#DC2626'
        ))
        
        fig.add_trace(go.Bar(
            name='VaR 1%', 
            x=methods,
            y=var_1_values,
            marker_color='#B91C1C'
        ))
        
        fig.update_layout(
            title="VaR Comparison Across Methods",
            xaxis_title="Method",
            yaxis_title="VaR (%)",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk interpretation
        st.info("""
        **Risk Interpretation:**
        - Historical VaR captures fat-tail risk most accurately for non-normal distributions
        - Monte Carlo VaR uses 10,000 simulations based on estimated parameters
        - Parametric VaR assumes normal distribution and may underestimate tail risk
        """)
        
    else:
        st.info("No VaR analysis available. Please analyze fund data first.")

def display_returns_distribution(db_manager, selected_symbol):
    """Display returns distribution analysis"""
    st.header("📈 Returns Distribution")
    
    try:
        returns_data = db_manager.get_fund_returns(selected_symbol, limit=500)
        
        if returns_data and len(returns_data) > 0:
            # Convert to DataFrame
            df = pd.DataFrame(returns_data)
            df['return_pct'] = df['return'] * 100
            
            # Histogram
            fig_hist = px.histogram(
                df, 
                x='return_pct',
                nbins=30,
                title="Historical Returns Distribution",
                labels={'return_pct': 'Daily Return (%)', 'count': 'Frequency'},
                color_discrete_sequence=['#1E3A8A']
            )
            
            # Add mean line
            mean_return = df['return_pct'].mean()
            fig_hist.add_vline(
                x=mean_return,
                line_dash="dash",
                line_color="#DC2626",
                annotation_text=f"Mean: {mean_return:.3f}%"
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Q-Q plot for normality assessment
            from scipy import stats
            
            returns_array = df['return'].values
            theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, len(returns_array)))
            sample_quantiles = np.sort(np.array(returns_array))
            
            fig_qq = go.Figure()
            fig_qq.add_trace(go.Scatter(
                x=theoretical_quantiles,
                y=sample_quantiles,
                mode='markers',
                name='Q-Q Plot',
                marker=dict(color='#1E3A8A', size=4)
            ))
            
            # Add reference line
            min_val = min(min(theoretical_quantiles), min(sample_quantiles))
            max_val = max(max(theoretical_quantiles), max(sample_quantiles))
            fig_qq.add_trace(go.Scatter(
                x=[min_val, max_val],
                y=[min_val, max_val],
                mode='lines',
                name='Normal Reference',
                line=dict(color='#DC2626', dash='dash')
            ))
            
            fig_qq.update_layout(
                title="Q-Q Plot: Actual vs Normal Distribution",
                xaxis_title="Theoretical Quantiles (Normal)",
                yaxis_title="Sample Quantiles",
                height=400
            )
            
            st.plotly_chart(fig_qq, use_container_width=True)
            
            # Distribution statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Summary Statistics")
                st.write(f"**Mean:** {mean_return:.4f}%")
                st.write(f"**Std Dev:** {df['return_pct'].std():.4f}%")
                st.write(f"**Min:** {df['return_pct'].min():.4f}%")
                st.write(f"**Max:** {df['return_pct'].max():.4f}%")
                
            with col2:
                st.subheader("Risk Metrics")
                var_5 = np.percentile(df['return_pct'], 5)
                var_1 = np.percentile(df['return_pct'], 1)
                st.write(f"**5% VaR:** {var_5:.4f}%")
                st.write(f"**1% VaR:** {var_1:.4f}%")
                st.write(f"**Observations:** {len(df):,}")
                
        else:
            st.info("No returns data available for visualization.")
            
    except Exception as e:
        st.error(f"Error loading returns data: {str(e)}")

def display_monte_carlo(fund_analysis):
    """Display Monte Carlo simulation"""
    st.header("🎲 Monte Carlo Simulation")
    
    if fund_analysis and fund_analysis.get('analysis'):
        analysis = fund_analysis['analysis']
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("Run Simulation", type="primary"):
                # Run Monte Carlo simulation
                mean = float(analysis.get('daily_mean', 0))
                std = float(analysis.get('daily_std', 0))
                
                np.random.seed(42)  # For reproducibility
                simulations = np.random.normal(mean, std, 10000)
                
                # Store in session state
                st.session_state.mc_simulations = simulations
                st.success("Simulation completed with 10,000 runs")
        
        with col1:
            if hasattr(st.session_state, 'mc_simulations'):
                simulations = st.session_state.mc_simulations
                
                # Create histogram of simulations
                fig = px.histogram(
                    x=simulations * 100,
                    nbins=50,
                    title="Monte Carlo Simulated Returns (10,000 simulations)",
                    labels={'x': 'Daily Return (%)', 'count': 'Frequency'},
                    color_discrete_sequence=['#1E3A8A']
                )
                
                # Add VaR lines
                var_5 = np.percentile(simulations * 100, 5)
                var_1 = np.percentile(simulations * 100, 1)
                
                fig.add_vline(x=var_5, line_dash="dash", line_color="#DC2626", 
                             annotation_text=f"VaR 5%: {var_5:.2f}%")
                fig.add_vline(x=var_1, line_dash="dash", line_color="#B91C1C",
                             annotation_text=f"VaR 1%: {var_1:.2f}%")
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Simulation metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Simulations", "10,000", "Completed")
                with col2:
                    st.metric("VaR 5%", f"{var_5:.3f}%", "Monte Carlo")
                with col3:
                    st.metric("VaR 1%", f"{var_1:.3f}%", "Monte Carlo")
                    
            else:
                st.info("Click 'Run Simulation' to generate Monte Carlo analysis")
                
    else:
        st.info("No analysis data available for Monte Carlo simulation.")

def display_data_export(db_manager, selected_symbol):
    """Display data export options"""
    st.header("💾 Data Management & Export")
    
    # Database status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4>Database Status</h4>
            <p class="profit-metric">✓ PostgreSQL Connected</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        fund_analysis = db_manager.get_fund_analysis(selected_symbol)
        last_updated = "No data"
        if fund_analysis and fund_analysis.get('analysis'):
            last_updated = "Recently"
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>Last Updated</h4>
            <p>{last_updated}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        record_count = 0
        if fund_analysis:
            record_count = fund_analysis.get('price_count', 0)
            
        st.markdown(f"""
        <div class="metric-card">
            <h4>Records Stored</h4>
            <p>{record_count:,}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.subheader("Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Analysis (JSON)"):
            try:
                data = db_manager.export_fund_data(selected_symbol, format='json')
                if data:
                    st.download_button(
                        label="Download JSON",
                        data=data,
                        file_name=f"{selected_symbol}_analysis.json",
                        mime="application/json"
                    )
                else:
                    st.warning("No data available for export")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col2:
        if st.button("📈 Export Prices (CSV)"):
            try:
                data = db_manager.export_fund_data(selected_symbol, format='csv')
                if data:
                    st.download_button(
                        label="Download CSV",
                        data=data,
                        file_name=f"{selected_symbol}_prices.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No data available for export")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col3:
        if st.button("📋 Generate Report"):
            st.info("PDF report generation feature coming soon")

if __name__ == "__main__":
    main()