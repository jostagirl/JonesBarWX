import os
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_mysqldb import MySQL

# --- Configuration ---
app = Flask(__name__)

load_dotenv()

# Load Credentials
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
API_KEY = os.getenv("API_KEY", "").strip()
API_SECRET = os.getenv("API_SECRET", "").strip()
STATION_ID = os.getenv("STATION_ID", "").strip()

app.config['MYSQL_HOST'] = DB_HOST
app.config['MYSQL_USER'] = DB_USER
app.config['MYSQL_PASSWORD'] = DB_PASS # <--- This is where the password goes!
app.config['MYSQL_DB'] = DB_NAME

mysql = MySQL(app)

API_URL = f'https://api.weatherlink.com/v2/current/{STATION_ID}?api-key={API_KEY}'
headers = {'X-Api-Secret': API_SECRET}

# --- Routes ---

@app.route('/')
def dashboard():
    # 1. Connect to the database
    cur = mysql.connection.cursor()

    # 2. Fetch API Data Table (e.g., last 10 entries)
   
    api_data_query = "SELECT timestamp_utc, api_success, insert_network, skipped_inserts FROM system_health ORDER BY timestamp_utc DESC LIMIT 10"
    cur.execute(api_data_query)
    api_data = cur.fetchall()
    
    # Get column names for the header (optional, but helpful)
    # cur.description returns a tuple for each column; the first element is the column name
    api_data_columns = [i[0] for i in cur.description]

    # 3. Fetch some weather data

    api_wx_data_query = "SELECT timestamp_utc, api_success, insert_network, skipped_inserts FROM system_health ORDER BY timestamp_utc DESC LIMIT 10"
    cur.execute(api_wx_data_query)
    api_data = cur.fetchall()

    # 4. Close the cursor
    cur.close()

    # 5. Render the template and pass the data
    return render_template(
        'dashboard.html',
        api_data=api_data,
        api_data_columns=api_data_columns
    )

# --- Run the App ---
if __name__ == '__main__':
    # Set a secret key for session management (required for some Flask features)
    app.secret_key = 'super_secret_key' 
    app.run(debug=True)