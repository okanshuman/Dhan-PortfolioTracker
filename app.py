# app.py
import credentials as cr
from dhanhq import dhanhq
import psycopg2
from datetime import datetime
import schedule
import time

# Initialize Dhan API client
dhan = dhanhq(cr.clientId, cr.apiToken)

# Database connection parameters
db_params = {
    'dbname': 'stocks_db',
    'user': 'casaos',
    'password': 'casaos',
    'host': 'localhost'
}

def fetch_and_store_data():
    holdingResponse = dhan.get_holdings()

    # Check if the response is successful and contains data
    if holdingResponse.get('status') == 'success' and 'data' in holdingResponse:
        holdings = holdingResponse['data']  # Extract the holdings data
        date_today = datetime.now().date()

        # Connect to PostgreSQL database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Insert each holding into the database
        for item in holdings:
            trading_symbol = item['tradingSymbol']
            total_qty = item['totalQty']
            avg_cost_price = item['avgCostPrice']
            last_traded_price = item['lastTradedPrice']

            try:
                cursor.execute("""
                    INSERT INTO stock_holding_dhan (date, trading_symbol, total_qty, avg_cost_price, last_traded_price)
                    VALUES (%s, %s, %s, %s, %s)
                """, (date_today, trading_symbol, total_qty, avg_cost_price, last_traded_price))
            except psycopg2.IntegrityError:
                conn.rollback()  # Rollback the transaction on error
                print(f"Duplicate entry for {trading_symbol} on {date_today}, skipping insertion.")
            else:
                conn.commit()  # Commit only if no error occurred

        cursor.close()
        conn.close()
        
        print(f"Data stored successfully for {date_today}")
    else:
        print("Failed to retrieve holdings or no data available.")

def job():
    # Check if today is a weekday (Monday to Friday)
    if datetime.now().weekday() < 5:  # Monday is 0 and Sunday is 6
        fetch_and_store_data()
    else:
        print("Today is a weekend. Skipping data fetch.")

# Schedule the job every day at 3:27 PM IST
schedule.every().day.at("15:27").do(job)

print("Scheduler started. Waiting for scheduled time...")

# Keep running the scheduler
while True:
    schedule.run_pending()
    time.sleep(60)  # wait one minute before checking again
