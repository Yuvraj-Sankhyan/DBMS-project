import os 
from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
import requests

app = Flask(__name__)

# MySQL Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="dbms_nifty"
    )

# Fetch IBM stock data from API and insert into the database
def fetch_ibm_data():
    # Get the API key from the system's environment variables
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
      raise ValueError("API key is not set in the environment variables.")

    # URL with the API key
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        if "Time Series (5min)" in data:
            time_series = data["Time Series (5min)"]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            for timestamp, values in time_series.items():
                open_price = values["1. open"]
                high_price = values["2. high"]
                low_price = values["3. low"]
                close_price = values["4. close"]
                volume = values["5. volume"]
                
                # Check for duplicate timestamp
                cursor.execute('SELECT COUNT(*) FROM IBM_data WHERE timestamp = %s', (timestamp,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                        INSERT INTO IBM_data (timestamp, open_price, high_price, low_price, close_price, volume)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (timestamp, open_price, high_price, low_price, close_price, volume))

            conn.commit()
            conn.close()
        else:
            print("Error: 'Time Series (5min)' not found in API response")
    else:
        print("Error: Unable to fetch data from the API")

# Route to handle login
# Route to insert login data
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if the credentials are correct in the registration table
    cursor.execute('SELECT * FROM registration WHERE email_id = %s AND password = %s', (email, password))
    user = cursor.fetchone()

    if user:
        # Insert login details into the login table (login_timestamp will be auto-filled)
        cursor.execute('''INSERT INTO login (email_id) VALUES (%s)''', (email,))
        conn.commit()

        # Successful login
        conn.close()
        return redirect(url_for('nifty50'))
    else:
        # Invalid credentials
        conn.close()
        return render_template('index.html', error="Invalid email or password")


# Route to handle registration
@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        names = request.form['names']
        surnames = request.form['surnames']
        email = request.form['emailCreate']
        password = request.form['passwordCreate']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute('SELECT COUNT(*) FROM registration WHERE email_id = %s', (email,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return render_template('index.html', error="Email already registered.")

        cursor.execute('''
            INSERT INTO registration (email_id, name, surname, password) 
            VALUES (%s, %s, %s, %s)
        ''', (email, names, surnames, password))

        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))

# Route to get IBM data for real-time graph
@app.route('/get_ibm_data', methods=['GET'])
def get_ibm_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT timestamp, close_price FROM IBM_data ORDER BY timestamp ASC LIMIT 100')
    data = cursor.fetchall()
    conn.close()
    
    return jsonify(data)

# Route for the index page (Login)
@app.route('/')
def index():
    return render_template('index.html')

# Route for the Nifty 50 page (IBM Stock Graph)
@app.route('/nifty50')
def nifty50():
    return render_template('nifty50.html')

if __name__ == "__main__":
    # Fetch the IBM data from the API and insert it into the database every time the server starts
    fetch_ibm_data()
    app.run(debug=True)
