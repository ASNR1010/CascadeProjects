import sqlite3
import requests
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('url_status.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS url_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            status TEXT,
            response_time REAL,
            checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    urls = data.get('urls', [])
    results = []
    
    # Validate URLs before checking
    valid_urls = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        valid_urls.append(url)
    
    for url in valid_urls:
        try:
            # Try HTTPS first, then fallback to HTTP
            try:
                response = requests.get(url.replace('http://', 'https://'), timeout=5, verify=False)
                status = 'UP' if response.status_code == 200 else 'DOWN'
                response_time = round(response.elapsed.total_seconds() * 1000, 2)
            except Exception:
                response = requests.get(url, timeout=5)
                status = 'UP' if response.status_code == 200 else 'DOWN'
                response_time = round(response.elapsed.total_seconds() * 1000, 2)
        except requests.exceptions.RequestException as e:
            print(f"Error checking URL {url}: {e}")
            status = 'DOWN'
            response_time = 0
        except Exception as e:
            print(f"Unexpected error checking URL {url}: {e}")
            status = 'ERROR'
            response_time = 0
        
        # Save to DB
        try:
            conn = sqlite3.connect('url_status.db')
            c = conn.cursor()
            c.execute('''
                INSERT INTO url_status (url, status, response_time, checked_at)
                VALUES (?, ?, ?, datetime('now'))
            ''', (url, status, response_time))
            conn.commit()
            conn.close()
            results.append({
                'url': url, 
                'status': status, 
                'response_time': response_time
            })
        except Exception as e:
            print(f"Error saving to DB: {e}")
            results.append({
                'url': url, 
                'status': 'ERROR', 
                'response_time': 0
            })
    return jsonify(results)

@app.route('/history', methods=['GET'])
def history():
    conn = sqlite3.connect('url_status.db')
    c = conn.cursor()
    c.execute('SELECT url, status, response_time, checked_at FROM url_status ORDER BY checked_at DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    history = [{'url': r[0], 'status': r[1], 'response_time': r[2], 'checked_at': r[3]} for r in rows]
    return jsonify(history)


#---------
@app.route('/chart-data')
def chart_data():
    try:
        conn = sqlite3.connect('url_status.db')
        c = conn.cursor()
        
        # First check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='url_status'")
        if not c.fetchone():
            return jsonify([])  # Return empty array if table doesn't exist
            
        # Fetch last 30 checks
        c.execute("SELECT checked_at, status, response_time FROM url_status ORDER BY checked_at DESC LIMIT 30")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return jsonify([])  # Return empty array if no data
            
        # Prepare data for Chart.js
        data = []
        for checked_at, status, response_time in reversed(rows):  # reversed for chronological order
            try:
                # Convert datetime to ISO format
                checked_at = checked_at.replace(' ', 'T')  # Convert SQLite datetime format to ISO
                data.append({
                    'x': checked_at,
                    'y': 1 if status == 'UP' else 0,  # 1 for UP, 0 for DOWN
                    'response_time': float(response_time)
                })
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
                
        return jsonify(data)
        
    except Exception as e:
        print(f"Error in chart_data endpoint: {e}")
        return jsonify([])  # Return empty array on error
#---------

if __name__ == '__main__':
    app.run(debug=True)







