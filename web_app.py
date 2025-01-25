# web_app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from collections import defaultdict
from datetime import datetime

app = Flask(__name__, template_folder='templates')

# Database configuration
db_config = {
    'dbname': 'stocks_db',
    'user': 'casaos',
    'password': 'casaos',
    'host': 'localhost'
}

def get_db_connection():
    return psycopg2.connect(**db_config)

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        selected_date = request.form['date']
        cursor.execute("""
            SELECT date, trading_symbol, total_qty, avg_cost_price, last_traded_price 
            FROM stock_holding_dhan 
            WHERE date = %s 
            ORDER BY trading_symbol ASC
        """, (selected_date,))
        records = cursor.fetchall()
        
        if not records:
            return redirect(url_for('index'))
        
        stocks_with_profit_loss = []
        total_profit_loss = 0.0
        total_profit_count = 0
        total_loss_count = 0
        total_profit = 0.0
        total_loss = 0.0
        
        for record in records:
            date = record[0]
            trading_symbol = record[1]
            total_qty = record[2]
            avg_cost_price = float(record[3])
            last_traded_price = float(record[4])
            
            profit_loss = (last_traded_price - avg_cost_price) * total_qty
            
            stocks_with_profit_loss.append((
                date,
                trading_symbol,
                total_qty,
                avg_cost_price,
                last_traded_price,
                profit_loss
            ))
            
            total_profit_loss += profit_loss
            
            if profit_loss > 0:
                total_profit_count += 1
                total_profit += profit_loss
            elif profit_loss < 0:
                total_loss_count += 1
                total_loss += abs(profit_loss)
        
        total_count = len(stocks_with_profit_loss)
        profit_percentage = (total_profit_count / total_count * 100) if total_count > 0 else 0
        loss_percentage = (total_loss_count / total_count * 100) if total_count > 0 else 0
        
        cursor.close()
        conn.close()
        
        return render_template('index.html',
            records=stocks_with_profit_loss,
            date=selected_date,
            total_count=total_count,
            total_profit_loss=total_profit_loss,
            total_profit_count=total_profit_count,
            total_loss_count=total_loss_count,
            total_profit=total_profit,
            total_loss=total_loss,
            profit_percentage=profit_percentage,
            loss_percentage=loss_percentage
        )

    # GET request - fetch available dates
    cursor.execute("SELECT DISTINCT date FROM stock_holding_dhan ORDER BY date ASC")
    dates = [date[0].strftime('%Y-%m-%d') for date in cursor.fetchall()]
    
    cursor.close()
    conn.close()

    return render_template('index.html', dates=dates)

@app.route('/profit_loss_chart')
def profit_loss_chart():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date, SUM((last_traded_price - avg_cost_price) * total_qty) AS daily_total 
        FROM stock_holding_dhan 
        GROUP BY date 
        ORDER BY date ASC
    """)
    results = cursor.fetchall()
    
    dates = [result[0].strftime('%Y-%m-%d') for result in results]
    daily_totals = [float(result[1]) for result in results]

    changes_in_totals = [daily_totals[i] - daily_totals[i-1] for i in range(1, len(daily_totals))]
    
    cursor.close()
    conn.close()

    return render_template('profit_loss_chart.html',
        dates=dates,
        daily_totals=daily_totals,
        changes_in_totals=changes_in_totals
    )

@app.route('/quantity_changes')
def quantity_changes():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM stock_holding_dhan ORDER BY date ASC")
    records = cursor.fetchall()

    data_by_symbol = defaultdict(lambda: defaultdict(list))
    for record in records:
        date = record[1]
        trading_symbol = record[2]
        total_qty = record[3]
        data_by_symbol[trading_symbol][date].append(total_qty)

    quantity_changes_list = []

    for symbol, dates in data_by_symbol.items():
        sorted_dates = sorted(dates.keys())
        previous_date = None
        previous_qty = None

        for date in sorted_dates:
            current_qty = dates[date][0]
            
            if previous_date is not None:
                cursor.execute("""
                    SELECT * FROM stock_holding_dhan_portfolio_updates 
                    WHERE trading_symbol=%s AND previous_date=%s AND change_date=%s
                """, (symbol, previous_date, date))
                marked_record = cursor.fetchone()

                if previous_qty != current_qty and marked_record is None:
                    quantity_changes_list.append((
                        previous_date.strftime('%Y-%m-%d'),
                        date.strftime('%Y-%m-%d'),
                        symbol,
                        previous_qty,
                        current_qty
                    ))
            
            previous_date = date
            previous_qty = current_qty

    cursor.close()
    conn.close()

    return render_template('index.html', quantity_changes=quantity_changes_list)

@app.route('/mark_change', methods=['POST'])
def mark_change():
    trading_symbol = request.form['trading_symbol']
    previous_date = request.form['previous_date']
    change_date = request.form['current_date']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO stock_holding_dhan_portfolio_updates 
            (trading_symbol, previous_date, change_date) 
            VALUES (%s, %s, %s)
        """, (trading_symbol, previous_date, change_date))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error marking change: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('quantity_changes'))

@app.route('/stock_history/<symbol>')
def stock_history(symbol):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT date, last_traded_price 
            FROM stock_holding_dhan 
            WHERE trading_symbol = %s 
            ORDER BY date ASC
        """, (symbol,))
        
        results = cursor.fetchall()
        dates = [result[0].strftime('%Y-%m-%d') for result in results]
        prices = [float(result[1]) for result in results]
        
        return jsonify({
            'symbol': symbol,
            'dates': dates,
            'prices': prices
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)