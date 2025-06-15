import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import json
import logging
from typing import List, Dict, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_analytics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        # Use SQLite database file
        self.db_path = os.getenv('DATABASE_PATH', 'risk_analytics.db')
        self.database_url = f'sqlite:///{self.db_path}'
        
        logger.info(f"Initializing DatabaseManager with SQLite database: {self.db_path}")
        
        self.engine = create_engine(self.database_url)
        self._ensure_tables_exist()
        
        logger.info("DatabaseManager initialization completed successfully")
    
    def _ensure_tables_exist(self):
        """Create tables if they don't exist"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS funds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(10) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fund_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_id INTEGER NOT NULL,
            date TIMESTAMP NOT NULL,
            open DECIMAL(10,4) NOT NULL,
            high DECIMAL(10,4) NOT NULL,
            low DECIMAL(10,4) NOT NULL,
            close DECIMAL(10,4) NOT NULL,
            volume INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fund_id) REFERENCES funds(id)
        );

        CREATE TABLE IF NOT EXISTS var_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_id INTEGER NOT NULL,
            analysis_date TIMESTAMP NOT NULL,
            parametric_var_5 DECIMAL(8,6),
            parametric_var_1 DECIMAL(8,6),
            historical_var_5 DECIMAL(8,6),
            historical_var_1 DECIMAL(8,6),
            historical_cvar_5 DECIMAL(8,6),
            historical_cvar_1 DECIMAL(8,6),
            monte_carlo_var_5 DECIMAL(8,6),
            monte_carlo_var_1 DECIMAL(8,6),
            monte_carlo_cvar_5 DECIMAL(8,6),
            monte_carlo_cvar_1 DECIMAL(8,6),
            daily_mean DECIMAL(10,8),
            daily_std DECIMAL(10,8),
            monthly_mean DECIMAL(10,8),
            monthly_std DECIMAL(10,8),
            skewness DECIMAL(8,6),
            kurtosis DECIMAL(8,6),
            normality_p_value DECIMAL(10,8),
            sharpe_ratio DECIMAL(8,6),
            annual_return DECIMAL(8,6),
            data_points INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fund_id) REFERENCES funds(id)
        );

        CREATE INDEX IF NOT EXISTS idx_fund_prices_fund_date ON fund_prices(fund_id, date);
        CREATE INDEX IF NOT EXISTS idx_var_analyses_fund_date ON var_analyses(fund_id, analysis_date);
        """
        
        logger.info("Creating database tables if they don't exist...")
        try:
            with self.engine.connect() as conn:
                # Split and execute each statement
                statements = create_tables_sql.strip().split(';')
                for statement in statements:
                    if statement.strip():
                        conn.execute(text(statement))
                conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def create_or_get_fund(self, symbol: str, name: str, description: str = None) -> int:
        """Create fund or return existing fund ID"""
        logger.info(f"Creating or retrieving fund: {symbol} - {name}")
        try:
            with self.engine.connect() as conn:
                # Check if fund exists
                result = conn.execute(
                    text("SELECT id FROM funds WHERE symbol = :symbol"),
                    {"symbol": symbol}
                ).fetchone()
                
                if result:
                    fund_id = result[0]
                    logger.info(f"Found existing fund {symbol} with ID: {fund_id}")
                    return fund_id
                
                # Create new fund
                logger.info(f"Creating new fund: {symbol}")
                result = conn.execute(
                    text("""
                        INSERT INTO funds (symbol, name, description) 
                        VALUES (:symbol, :name, :description)
                    """),
                    {"symbol": symbol, "name": name, "description": description}
                )
                conn.commit()
                
                # Get the inserted ID
                fund_id = conn.execute(
                    text("SELECT id FROM funds WHERE symbol = :symbol"),
                    {"symbol": symbol}
                ).fetchone()[0]
                
                logger.info(f"Successfully created fund {symbol} with ID: {fund_id}")
                return fund_id
                
        except Exception as e:
            logger.error(f"Error creating/getting fund {symbol}: {e}")
            raise

    def store_fund_prices(self, fund_id: int, prices: List[Dict]) -> None:
        """Store fund price data"""
        logger.info(f"Storing {len(prices)} price records for fund ID: {fund_id}")
        try:
            df = pd.DataFrame(prices)
            df['fund_id'] = fund_id
            df['created_at'] = datetime.now()
            
            # Convert date strings to datetime if needed
            if 'date' in df.columns and df['date'].dtype == 'object':
                df['date'] = pd.to_datetime(df['date'])
            
            df.to_sql('fund_prices', self.engine, if_exists='append', index=False)
            logger.info(f"Successfully stored {len(prices)} price records for fund ID: {fund_id}")
            
        except Exception as e:
            logger.error(f"Error storing fund prices for fund ID {fund_id}: {e}")
            raise

    def store_var_analysis(self, fund_id: int, var_results: Dict) -> int:
        """Store VaR analysis results"""
        try:
            analysis_data = {
                'fund_id': fund_id,
                'analysis_date': datetime.now(),
                'parametric_var_5': var_results.get('parametricVar5'),
                'parametric_var_1': var_results.get('parametricVar1'),
                'historical_var_5': var_results.get('historicalVar5'),
                'historical_var_1': var_results.get('historicalVar1'),
                'historical_cvar_5': var_results.get('historicalCvar5'),
                'historical_cvar_1': var_results.get('historicalCvar1'),
                'monte_carlo_var_5': var_results.get('monteCarloVar5'),
                'monte_carlo_var_1': var_results.get('monteCarloVar1'),
                'monte_carlo_cvar_5': var_results.get('monteCarloCvar5'),
                'monte_carlo_cvar_1': var_results.get('monteCarloCvar1'),
                'daily_mean': var_results.get('dailyMean'),
                'daily_std': var_results.get('dailyStd'),
                'monthly_mean': var_results.get('monthlyMean'),
                'monthly_std': var_results.get('monthlyStd'),
                'skewness': var_results.get('skewness'),
                'kurtosis': var_results.get('kurtosis'),
                'normality_p_value': var_results.get('normalityPValue'),
                'sharpe_ratio': var_results.get('sharpeRatio'),
                'annual_return': var_results.get('annualReturn'),
                'data_points': var_results.get('dataPoints')
            }
            
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO var_analyses (
                            fund_id, analysis_date, parametric_var_5, parametric_var_1,
                            historical_var_5, historical_var_1, historical_cvar_5, historical_cvar_1,
                            monte_carlo_var_5, monte_carlo_var_1, monte_carlo_cvar_5, monte_carlo_cvar_1,
                            daily_mean, daily_std, monthly_mean, monthly_std,
                            skewness, kurtosis, normality_p_value, sharpe_ratio,
                            annual_return, data_points
                        ) VALUES (
                            :fund_id, :analysis_date, :parametric_var_5, :parametric_var_1,
                            :historical_var_5, :historical_var_1, :historical_cvar_5, :historical_cvar_1,
                            :monte_carlo_var_5, :monte_carlo_var_1, :monte_carlo_cvar_5, :monte_carlo_cvar_1,
                            :daily_mean, :daily_std, :monthly_mean, :monthly_std,
                            :skewness, :kurtosis, :normality_p_value, :sharpe_ratio,
                            :annual_return, :data_points
                        )
                    """),
                    analysis_data
                )
                conn.commit()
                analysis_id = result.lastrowid
                
            print(f"✅ VaR analysis stored with ID: {analysis_id}")
            return analysis_id
            
        except Exception as e:
            print(f"❌ Error storing VaR analysis: {e}")
            raise

    def get_fund_analysis(self, symbol: str) -> Optional[Dict]:
        """Get latest fund analysis"""
        try:
            query = """
            SELECT f.*, va.* 
            FROM funds f
            JOIN var_analyses va ON f.id = va.fund_id
            WHERE f.symbol = :symbol
            ORDER BY va.analysis_date DESC
            LIMIT 1
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"symbol": symbol}).fetchone()
                
                if result:
                    columns = result._fields
                    return dict(zip(columns, result))
                return None
                
        except Exception as e:
            print(f"❌ Error getting fund analysis: {e}")
            return None

    def get_fund_returns(self, symbol: str, limit: int = 500) -> List[Dict]:
        """Get fund returns data for charting"""
        try:
            query = """
            SELECT fp.date, fp.close
            FROM funds f
            JOIN fund_prices fp ON f.id = fp.fund_id
            WHERE f.symbol = :symbol
            ORDER BY fp.date DESC
            LIMIT :limit
            """
            
            df = pd.read_sql(query, self.engine, params={"symbol": symbol, "limit": limit})
            
            if len(df) > 1:
                # Calculate returns
                df = df.sort_values('date')
                df['return'] = df['close'].pct_change()
                df = df.dropna()
                
                return [
                    {
                        'date': row['date'],
                        'return': row['return'],
                        'price': row['close']
                    }
                    for _, row in df.iterrows()
                ]
            return []
            
        except Exception as e:
            print(f"❌ Error getting fund returns: {e}")
            return []

    def export_fund_data(self, symbol: str, format: str = 'json') -> Optional[str]:
        """Export fund data"""
        try:
            # Get fund info
            fund_query = "SELECT * FROM funds WHERE symbol = :symbol"
            
            # Get prices
            prices_query = """
            SELECT fp.* FROM fund_prices fp
            JOIN funds f ON f.id = fp.fund_id
            WHERE f.symbol = :symbol
            ORDER BY fp.date
            """
            
            # Get analyses
            analyses_query = """
            SELECT va.* FROM var_analyses va
            JOIN funds f ON f.id = va.fund_id
            WHERE f.symbol = :symbol
            ORDER BY va.analysis_date DESC
            """
            
            with self.engine.connect() as conn:
                fund_df = pd.read_sql(fund_query, conn, params={"symbol": symbol})
                prices_df = pd.read_sql(prices_query, conn, params={"symbol": symbol})
                analyses_df = pd.read_sql(analyses_query, conn, params={"symbol": symbol})
            
            if format.lower() == 'json':
                export_data = {
                    'fund': fund_df.to_dict('records')[0] if not fund_df.empty else None,
                    'prices': prices_df.to_dict('records'),
                    'analyses': analyses_df.to_dict('records')
                }
                return json.dumps(export_data, default=str, indent=2)
            
            elif format.lower() == 'csv':
                # Return prices as CSV (most commonly requested)
                return prices_df.to_csv(index=False)
                
        except Exception as e:
            print(f"❌ Error exporting fund data: {e}")
            return None

    def get_database_info(self) -> Dict:
        """Get database statistics"""
        try:
            with self.engine.connect() as conn:
                funds_count = conn.execute(text("SELECT COUNT(*) FROM funds")).scalar()
                prices_count = conn.execute(text("SELECT COUNT(*) FROM fund_prices")).scalar()
                analyses_count = conn.execute(text("SELECT COUNT(*) FROM var_analyses")).scalar()
                
                return {
                    'database_type': 'SQLite',
                    'database_path': self.db_path,
                    'funds_count': funds_count,
                    'prices_count': prices_count,
                    'analyses_count': analyses_count
                }
        except Exception as e:
            print(f"❌ Error getting database info: {e}")
            return {}

class VarAnalysis:
    """Data class for VaR analysis results"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)