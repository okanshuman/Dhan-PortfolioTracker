# web_app.py
from flask import Flask, render_template_string
import psycopg2

app = Flask(__name__)

# Database connection parameters (same as in app.py)
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
    
    cursor.execute("SELECT * FROM stock_holding_dhan ORDER BY date DESC")
    records = cursor.fetchall()
    
    cursor.close()
    conn.close()

    # Render HTML directly from a string instead of using a separate file.
    html_content = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Holdings</title>
    </head>
    <body>
        <h1>Stock Holdings Data</h1>
        <table border="1">
            <tr>
                <th>Date</th>
                <th>Trading Symbol</th>
                <th>Total Quantity</th>
                <th>Average Cost Price</th>
                <th>Last Traded Price</th>
            </tr>
            {% for record in records %}
            <tr>
                <td>{{ record[1] }}</td>
                <td>{{ record[2] }}</td>
                <td>{{ record[3] }}</td>
                <td>{{ record[4] }}</td>
                <td>{{ record[5] }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    
    return render_template_string(html_content, records=records)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)  # Change host to 0.0.0.0
