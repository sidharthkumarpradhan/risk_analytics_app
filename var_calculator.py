import numpy as np
from scipy import stats
from typing import List, Dict
import math

class VarCalculator:
    """Advanced VaR calculator with multiple methodologies"""
    
    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """Calculate daily returns from price series"""
        if len(prices) < 2:
            return []
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                return_val = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(return_val)
        
        return returns
    
    @staticmethod
    def calculate_var(prices: List[float]) -> Dict:
        """
        Calculate comprehensive VaR metrics using multiple methodologies
        Based on the Python implementation from the attached analysis file
        """
        if len(prices) < 50:
            raise ValueError("Insufficient data for VaR calculation (minimum 50 observations required)")
        
        # Calculate returns
        returns = VarCalculator.calculate_returns(prices)
        returns_array = np.array(returns)
        
        # Basic statistics
        daily_mean = np.mean(returns_array)
        daily_std = np.std(returns_array, ddof=1)  # Sample standard deviation
        monthly_mean = daily_mean * 22  # ~22 trading days per month
        monthly_std = daily_std * np.sqrt(22)
        
        # Higher moments for distribution analysis
        skewness = stats.skew(returns_array)
        kurtosis = stats.kurtosis(returns_array, fisher=False)  # Pearson kurtosis
        
        # Normality test (D'Agostino and Pearson's test)
        stat, normality_p_value = stats.normaltest(returns_array)
        
        # Performance metrics
        annual_return = (1 + daily_mean) ** 252 - 1  # ~252 trading days per year
        annual_std = daily_std * np.sqrt(252)
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        sharpe_ratio = (annual_return - risk_free_rate) / annual_std if annual_std != 0 else 0
        
        # 1. Parametric VaR (assumes normal distribution)
        z_05 = stats.norm.ppf(0.05)  # 5% quantile
        z_01 = stats.norm.ppf(0.01)  # 1% quantile
        parametric_var_5 = daily_mean - z_05 * daily_std
        parametric_var_1 = daily_mean - z_01 * daily_std
        
        # 2. Historical VaR (empirical quantiles)
        historical_var_5 = np.percentile(returns_array, 5)
        historical_var_1 = np.percentile(returns_array, 1)
        
        # 3. Historical CVaR (Conditional VaR / Expected Shortfall)
        returns_below_var_5 = returns_array[returns_array <= historical_var_5]
        returns_below_var_1 = returns_array[returns_array <= historical_var_1]
        
        historical_cvar_5 = np.mean(returns_below_var_5) if len(returns_below_var_5) > 0 else historical_var_5
        historical_cvar_1 = np.mean(returns_below_var_1) if len(returns_below_var_1) > 0 else historical_var_1
        
        # 4. Monte Carlo VaR (10,000 simulations)
        np.random.seed(42)  # For reproducibility
        n_simulations = 10000
        mc_returns = np.random.normal(daily_mean, daily_std, n_simulations)
        
        monte_carlo_var_5 = np.percentile(mc_returns, 5)
        monte_carlo_var_1 = np.percentile(mc_returns, 1)
        
        # Monte Carlo CVaR
        mc_returns_below_var_5 = mc_returns[mc_returns <= monte_carlo_var_5]
        mc_returns_below_var_1 = mc_returns[mc_returns <= monte_carlo_var_1]
        
        monte_carlo_cvar_5 = np.mean(mc_returns_below_var_5) if len(mc_returns_below_var_5) > 0 else monte_carlo_var_5
        monte_carlo_cvar_1 = np.mean(mc_returns_below_var_1) if len(mc_returns_below_var_1) > 0 else monte_carlo_var_1
        
        return {
            'parametric_var_5': float(parametric_var_5),
            'parametric_var_1': float(parametric_var_1),
            'historical_var_5': float(historical_var_5),
            'historical_var_1': float(historical_var_1),
            'historical_cvar_5': float(historical_cvar_5),
            'historical_cvar_1': float(historical_cvar_1),
            'monte_carlo_var_5': float(monte_carlo_var_5),
            'monte_carlo_var_1': float(monte_carlo_var_1),
            'monte_carlo_cvar_5': float(monte_carlo_cvar_5),
            'monte_carlo_cvar_1': float(monte_carlo_cvar_1),
            'daily_mean': float(daily_mean),
            'daily_std': float(daily_std),
            'monthly_mean': float(monthly_mean),
            'monthly_std': float(monthly_std),
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'normality_p_value': float(normality_p_value),
            'sharpe_ratio': float(sharpe_ratio),
            'annual_return': float(annual_return),
            'data_points': len(returns)
        }
    
    @staticmethod
    def generate_monte_carlo_simulation(mean: float, std: float, n_simulations: int = 10000) -> np.ndarray:
        """Generate Monte Carlo simulations for visualization"""
        np.random.seed(42)  # For reproducibility
        return np.random.normal(mean, std, n_simulations)
    
    @staticmethod
    def calculate_portfolio_var(weights: List[float], returns_matrix: np.ndarray, confidence_level: float = 0.05) -> float:
        """Calculate portfolio VaR given weights and return matrix"""
        if len(weights) != returns_matrix.shape[1]:
            raise ValueError("Number of weights must match number of assets")
        
        weights = np.array(weights)
        portfolio_returns = returns_matrix @ weights
        
        return np.percentile(portfolio_returns, confidence_level * 100)
    
    @staticmethod
    def backtest_var(returns: List[float], var_estimates: List[float], confidence_level: float = 0.05) -> Dict:
        """Backtest VaR model performance"""
        if len(returns) != len(var_estimates):
            raise ValueError("Returns and VaR estimates must have same length")
        
        violations = sum(1 for r, var in zip(returns, var_estimates) if r < var)
        total_observations = len(returns)
        violation_rate = violations / total_observations
        expected_violations = confidence_level * total_observations
        
        # Kupiec test for unconditional coverage
        if violations == 0 or violations == total_observations:
            kupiec_stat = float('inf')
            kupiec_p_value = 0.0
        else:
            lr_stat = 2 * (violations * np.log(violation_rate / confidence_level) + 
                          (total_observations - violations) * np.log((1 - violation_rate) / (1 - confidence_level)))
            kupiec_stat = lr_stat
            kupiec_p_value = 1 - stats.chi2.cdf(lr_stat, df=1)
        
        return {
            'violations': violations,
            'violation_rate': violation_rate,
            'expected_violations': expected_violations,
            'kupiec_statistic': kupiec_stat,
            'kupiec_p_value': kupiec_p_value,
            'model_adequate': kupiec_p_value > 0.05  # Null hypothesis: model is adequate
        }