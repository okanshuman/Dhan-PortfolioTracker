from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from collections import defaultdict
from datetime import datetime, date

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
    
    # Fetch all dates and their total portfolio value
    cursor.execute("""
        SELECT date, SUM(last_traded_price * total_qty) AS daily_value
        FROM stock_holding_dhan 
        GROUP BY date 
        ORDER BY date ASC
    """)
    date_values = cursor.fetchall()
    dates = [date[0].strftime('%Y-%m-%d') for date in date_values]
    
    # Calculate daily changes
    date_change_map = {}
    for i in range(len(date_values)):
        current_date = date_values[i][0].strftime('%Y-%m-%d')
        current_value = float(date_values[i][1])
        if i == 0:
            # First day has no previous day to compare, so change is 0
            date_change_map[current_date] = 0.0
        else:
            prev_value = float(date_values[i-1][1])
            daily_change = current_value - prev_value
            date_change_map[current_date] = daily_change

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
            cursor.close()
            conn.close()
            return render_template('index.html', dates=dates, date_change_map={})
        
        stocks_with_profit_loss = []
        total_profit_loss = 0.0
        total_profit_count = 0
        total_loss_count = 0
        total_portfolio_value = 0.0
        total_investment = 0.0
        
        for record in records:
            date = record[0]
            trading_symbol = record[1]
            total_qty = record[2]
            avg_cost_price = float(record[3])
            last_traded_price = float(record[4])
            
            profit_loss = (last_traded_price - avg_cost_price) * total_qty
            current_value = last_traded_price * total_qty
            investment = avg_cost_price * total_qty
            
            stock_data = {
                'date': date,
                'symbol': trading_symbol,
                'qty': total_qty,
                'avg_cost': avg_cost_price,
                'ltp': last_traded_price,
                'profit_loss': profit_loss,
                'current_value': current_value,
                'percent_change': ((last_traded_price - avg_cost_price) / avg_cost_price * 100) if avg_cost_price > 0 else 0,
                'investment': investment
            }
            
            stocks_with_profit_loss.append(stock_data)
            total_profit_loss += profit_loss
            total_portfolio_value += current_value
            total_investment += investment
            
            if profit_loss > 0:
                total_profit_count += 1
            elif profit_loss < 0:
                total_loss_count += 1
        
        total_count = len(stocks_with_profit_loss)
        profit_percentage = (total_profit_count / total_count * 100) if total_count > 0 else 0
        loss_percentage = (total_loss_count / total_count * 100) if total_count > 0 else 0
        
        sorted_stocks = sorted(stocks_with_profit_loss, key=lambda x: x['percent_change'], reverse=True)
        top_winners = sorted_stocks[:5]
        top_losers = sorted_stocks[-5:][::-1]
        
        prev_date = sorted(dates)[-2] if len(dates) > 1 else None
        daily_change_percent = 0
        if prev_date:
            cursor.execute("""
                SELECT SUM(last_traded_price * total_qty) 
                FROM stock_holding_dhan 
                WHERE date = %s
            """, (prev_date,))
            prev_value = float(cursor.fetchone()[0] or 0)
            daily_change_percent = ((total_portfolio_value - prev_value) / prev_value * 100) if prev_value > 0 else 0
        
        cursor.close()
        conn.close()
        
        return render_template('index.html',
            records=stocks_with_profit_loss,
            date=selected_date,
            total_count=total_count,
            total_profit_loss=total_profit_loss,
            total_profit_count=total_profit_count,
            total_loss_count=total_loss_count,
            profit_percentage=profit_percentage,
            loss_percentage=loss_percentage,
            dates=dates,
            total_portfolio_value=total_portfolio_value,
            daily_change_percent=daily_change_percent,
            top_winners=top_winners,
            top_losers=top_losers,
            total_investment=total_investment,
            date_change_map=date_change_map
        )

    cursor.close()
    conn.close()
    return render_template('index.html', dates=dates, date_change_map=date_change_map)

@app.route('/profit_loss_chart')
def profit_loss_chart():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date, SUM((last_traded_price - avg_cost_price) * total_qty) AS daily_total,
               SUM(last_traded_price * total_qty) AS portfolio_value
        FROM stock_holding_dhan 
        GROUP BY date 
        ORDER BY date ASC
    """)
    results = cursor.fetchall()
    
    dates = [result[0].strftime('%Y-%m-%d') for result in results]
    daily_totals = [float(result[1]) for result in results]
    portfolio_values = [float(result[2]) for result in results]
    changes_in_totals = [daily_totals[i] - daily_totals[i-1] if i > 0 else 0 for i in range(len(daily_totals))]
    
    cursor.close()
    conn.close()

    return render_template('profit_loss_chart.html',
        dates=dates,
        daily_totals=daily_totals,
        changes_in_totals=changes_in_totals,
        portfolio_values=portfolio_values
    )

@app.route('/quantity_changes')
def quantity_changes():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT date FROM stock_holding_dhan ORDER BY date ASC")
    dates = [date[0].strftime('%Y-%m-%d') for date in cursor.fetchall()]

    cursor.execute("SELECT * FROM stock_holding_dhan ORDER BY date ASC")
    records = cursor.fetchall()

    data_by_symbol = defaultdict(lambda: defaultdict(list))
    for record in records:
        date = record[1]
        trading_symbol = record[2]
        total_qty = record[3]
        data_by_symbol[trading_symbol][date].append(total_qty)

    quantity_changes_list = []

    for symbol, dates_dict in data_by_symbol.items():
        sorted_dates = sorted(dates_dict.keys())
        previous_date = None
        previous_qty = None

        for date_obj in sorted_dates:
            current_qty = dates_dict[date_obj][0]

            if previous_date is not None:
                cursor.execute("""
                    SELECT * FROM stock_holding_dhan_portfolio_updates 
                    WHERE trading_symbol=%s AND previous_date=%s AND change_date=%s
                """, (symbol, previous_date, date_obj))
                marked_record = cursor.fetchone()

                if previous_qty != current_qty and marked_record is None:
                    quantity_changes_list.append({
                        'prev_date': previous_date.strftime('%Y-%m-%d'),
                        'curr_date': date_obj.strftime('%Y-%m-%d'),
                        'symbol': symbol,
                        'prev_qty': previous_qty,
                        'curr_qty': current_qty,
                        'change': current_qty - previous_qty
                    })

            previous_date = date_obj
            previous_qty = current_qty

    cursor.close()
    conn.close()

    return render_template('index.html', quantity_changes=quantity_changes_list, dates=dates, date_change_map={})


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
            SELECT date, last_traded_price, total_qty, avg_cost_price
            FROM stock_holding_dhan 
            WHERE trading_symbol = %s 
            ORDER BY date ASC
        """, (symbol,))
        
        results = cursor.fetchall()
        dates = [result[0].strftime('%Y-%m-%d') for result in results]
        prices = [float(result[1]) for result in results]
        quantities = [result[2] for result in results]
        avg_costs = [float(result[3]) for result in results]
        
        return jsonify({
            'symbol': symbol,
            'dates': dates,
            'prices': prices,
            'quantities': quantities,
            'avg_costs': avg_costs
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)