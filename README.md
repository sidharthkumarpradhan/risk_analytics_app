# Risk Analytics Pro - Investment Portfolio VaR Analysis Dashboard

## 🎯 Overview

Risk Analytics Pro is a comprehensive investment risk analysis dashboard that provides professional-grade Value at Risk (VaR) calculations for mutual funds. Built with Python and Streamlit, it offers real-time data fetching, advanced statistical analysis, and interactive visualizations for investment risk assessment.

## 🌟 Key Features

### Advanced Risk Calculations
- **Parametric VaR**: Normal distribution-based risk estimates
- **Historical VaR**: Empirical quantile-based risk measures
- **Monte Carlo VaR**: Simulation-based risk analysis (10,000 iterations)
- **Conditional VaR (CVaR)**: Expected shortfall calculations

### Statistical Analysis
- Daily and monthly return statistics
- Skewness and kurtosis analysis
- D'Agostino-Pearson normality testing
- Sharpe ratio and performance metrics
- Q-Q plots for distribution assessment

### Interactive Dashboard
- **Overview Tab**: Key metrics and statistical summaries
- **VaR Analysis Tab**: Comprehensive risk metric comparisons
- **Distribution Tab**: Returns distribution with histogram and Q-Q plots
- **Monte Carlo Tab**: Interactive simulation analysis
- **Data Export Tab**: JSON and CSV export functionality

### Data Management
- Real-time AlphaVantage API integration
- PostgreSQL database with automatic schema creation
- 3-year historical data analysis
- Offline data persistence and caching

## 🚀 Live Demo

Deploy instantly on Streamlit Cloud: [Your App URL will appear here after deployment]

## 📊 Supported Funds

- **FCNTX** - Fidelity Contrafund
- **VFIAX** - Vanguard 500 Index Fund
- **FXNAX** - Fidelity US Bond Index Fund  
- **VTSMX** - Vanguard Total Stock Market Fund
- **FSKAX** - Fidelity Total Market Index Fund

## 🛠️ Technology Stack

- **Frontend**: Streamlit with custom financial styling
- **Backend**: Python with advanced statistical libraries
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Data Source**: AlphaVantage API for real-time fund data
- **Visualization**: Plotly for interactive charts
- **Statistics**: SciPy, NumPy, Pandas for calculations

## 📋 Prerequisites

- Python 3.8 or higher
- AlphaVantage API key (free tier available)
- SQLite database (automatically created)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/risk-analytics-pro.git
cd risk-analytics-pro
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file:
```env
ALPHAVANTAGE_API_KEY=your_api_key_here
DATABASE_PATH=risk_analytics.db
```

### 4. Run Application
```bash
streamlit run streamlit_app.py
```

Access the dashboard at `http://localhost:8501`

## 🌐 Deployment Options

### Streamlit Cloud (Recommended)
1. Push code to GitHub repository
2. Visit [streamlit.io/cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Set environment variables in Streamlit Cloud dashboard
5. Deploy with one click

### Heroku
```bash
# Create Procfile
echo "web: streamlit run streamlit_app.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile

# Deploy
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set ALPHAVANTAGE_API_KEY=your_key
git push heroku main
```

### Railway
1. Connect GitHub repository
2. Add PostgreSQL service
3. Set environment variables
4. Deploy automatically

## 📁 Project Structure

```
risk-analytics-pro/
├── streamlit_app.py          # Main Streamlit application
├── database.py               # PostgreSQL database manager
├── alphavantage_service.py   # API integration service
├── var_calculator.py         # VaR calculation engine
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── .env.example             # Environment variables template
└── README.md                # Project documentation
```

## 🎯 Usage Guide

### 1. Fund Selection
- Choose from pre-configured mutual funds in the sidebar
- Enter your AlphaVantage API key (or use default)

### 2. Data Fetching
- Click "Fetch & Analyze" to download 3 years of historical data
- Data is automatically stored in PostgreSQL for offline analysis

### 3. Risk Analysis
- View comprehensive VaR metrics across multiple methodologies
- Compare parametric, historical, and Monte Carlo results
- Analyze statistical distribution properties

### 4. Visualization
- Interactive charts show returns distribution
- Q-Q plots assess normality assumptions
- Monte Carlo simulations visualize risk scenarios

### 5. Export Results
- Download analysis results as JSON
- Export price data as CSV
- Generate comprehensive risk reports

## 📊 VaR Methodology

### Parametric VaR
Assumes returns follow a normal distribution:
```
VaR = μ - z_α × σ
```
Where μ is mean return, σ is standard deviation, and z_α is the critical value.

### Historical VaR
Uses empirical distribution of actual returns:
```
VaR = Quantile(returns, α)
```
More robust for non-normal distributions.

### Monte Carlo VaR
Simulates 10,000 potential outcomes:
```python
simulations = np.random.normal(μ, σ, 10000)
VaR = np.percentile(simulations, α × 100)
```

### Conditional VaR (Expected Shortfall)
Average loss beyond VaR threshold:
```
CVaR = E[Return | Return ≤ VaR]
```

## 🔧 Configuration

### Database Schema
Tables are created automatically:
- `funds`: Fund information and metadata
- `fund_prices`: Historical OHLCV price data
- `var_analyses`: VaR calculation results
- `analysis_logs`: Activity tracking and audit trail

### API Limits
- AlphaVantage Free Tier: 5 calls/minute, 500 calls/day
- Data is cached locally to minimize API usage
- Historical analysis works offline after initial data fetch

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Resources

- [AlphaVantage API Documentation](https://www.alphavantage.co/documentation/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [VaR Methodology Guide](https://www.investopedia.com/terms/v/var.asp)
- [Risk Management Best Practices](https://www.risk.net/)

## 📞 Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Contact: [your-email@domain.com]
- Documentation: [Link to detailed docs]

## 🏆 Acknowledgments

- AlphaVantage for providing financial data API
- Streamlit for the excellent web app framework
- SciPy community for statistical computing tools
- Financial risk management academic research

---

**Built with ❤️ for the investment analysis community**

*Professional risk analytics made accessible through modern web technology*