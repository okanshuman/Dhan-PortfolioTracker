# web_app.py
from flask import Flask, render_template
import psycopg2
from collections import defaultdict

app = Flask(__name__, template_folder='.')  # Set template folder to current directory

# Database connection parameters
db_params = {
    'dbname': 'stocks_db',
    'user': 'casaos',
    'password': 'casaos',
    'host': 'localhost'
}

@app.route('/')
def index():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    # Fetch all records from the database
    cursor.execute("SELECT * FROM stock_holding_dhan ORDER BY date ASC")
    records = cursor.fetchall()
    
    cursor.close()
    conn.close()

    # Organize data by trading symbol and date
    data_by_symbol = defaultdict(lambda: defaultdict(list))
    for record in records:
        date = record[1]  # record[1] is the date
        trading_symbol = record[2]  # record[2] is the trading symbol
        total_qty = record[3]  # record[3] is the total quantity
        data_by_symbol[trading_symbol][date].append(total_qty)

    # Prepare a list of stocks with quantity differences including dates
    quantity_changes = []

    for symbol, dates in data_by_symbol.items():
        sorted_dates = sorted(dates.keys())  # Sort dates for chronological order
        previous_date = None
        previous_qty = None

        for date in sorted_dates:
            current_qty = dates[date][0]  # Get current quantity for that date
            
            if previous_date is not None:
                quantity_changes.append((symbol, previous_date, previous_qty, date, current_qty))
            
            previous_date = date  # Update previous date for next iteration
            previous_qty = current_qty  # Update previous quantity for next iteration

    # Render HTML using the index.html file located in the root directory.
    return render_template('index.html', quantity_changes=quantity_changes)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)  # Change host to 0.0.0.0 if needed.
