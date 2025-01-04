from flask import Flask, render_template, request, redirect, url_for
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

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Get the selected date from the form
        selected_date = request.form['date']
        cursor.execute("SELECT * FROM stock_holding_dhan WHERE date = %s ORDER BY trading_symbol ASC", (selected_date,))
        records = cursor.fetchall()
        
        # Calculate profit/loss for each stock
        stocks_with_profit_loss = []
        for record in records:
            date = record[1]  # Date
            trading_symbol = record[2]  # Trading Symbol
            total_qty = record[3]  # Total Quantity
            avg_cost_price = record[4]  # Average Cost Price
            last_traded_price = record[5]  # Last Traded Price
            
            # Calculate Profit/Loss
            profit_loss = (last_traded_price - avg_cost_price) * total_qty
            
            stocks_with_profit_loss.append((date, trading_symbol, total_qty, avg_cost_price, last_traded_price, profit_loss))
        
        total_count = len(stocks_with_profit_loss)  # Count of stocks
        
        cursor.close()
        conn.close()
        return render_template('index.html', records=stocks_with_profit_loss, date=selected_date, total_count=total_count)

    # Fetch all unique dates from the database for the home page
    cursor.execute("SELECT DISTINCT date FROM stock_holding_dhan ORDER BY date ASC")
    dates = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('index.html', dates=dates)

@app.route('/quantity_changes')
def quantity_changes():
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # Fetch all records from the database
    cursor.execute("SELECT * FROM stock_holding_dhan ORDER BY date ASC")
    records = cursor.fetchall()

    # Organize data by trading symbol and date
    data_by_symbol = defaultdict(lambda: defaultdict(list))
    for record in records:
        date = record[1]  # record[1] is the date
        trading_symbol = record[2]  # record[2] is the trading symbol
        total_qty = record[3]  # record[3] is the total quantity
        data_by_symbol[trading_symbol][date].append(total_qty)

    # Prepare a list of stocks with quantity differences including dates
    quantity_changes_list = []

    for symbol, dates in data_by_symbol.items():
        sorted_dates = sorted(dates.keys())  # Sort dates for chronological order
        previous_date = None
        previous_qty = None

        for date in sorted_dates:
            current_qty = dates[date][0]  # Get current quantity for that date
            
            if previous_date is not None:
                # Only append if there is a change in quantity and not marked as buy/sell
                cursor.execute("SELECT * FROM stock_holding_dhan_portfolio_updates WHERE trading_symbol=%s AND previous_date=%s AND change_date=%s",
                               (symbol, previous_date, date))
                marked_record = cursor.fetchone()

                if previous_qty != current_qty and marked_record is None:
                    quantity_changes_list.append((previous_date, date, symbol, previous_qty, current_qty))
            
            previous_date = date  # Update previous date for next iteration
            previous_qty = current_qty  # Update previous quantity for next iteration

    cursor.close()  # Close the cursor here after all operations are done.
    conn.close()  # Close the connection.

    return render_template('index.html', quantity_changes=quantity_changes_list)

@app.route('/mark_change', methods=['POST'])
def mark_change():
    trading_symbol = request.form['trading_symbol']
    previous_date = request.form['previous_date']
    change_date = request.form['current_date']  # Updated variable name

    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # Insert into stock_holding_dhan_portfolio_updates table to mark this change as buy/sell
    cursor.execute("INSERT INTO stock_holding_dhan_portfolio_updates (trading_symbol, previous_date, change_date) VALUES (%s, %s, %s)",
                   (trading_symbol, previous_date, change_date))
    
    conn.commit()
    
    cursor.close()
    conn.close()

    return redirect(url_for('quantity_changes'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)  # Change host to 0.0.0.0 if needed.
