from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'insecure_demo_key'  # Hardcoded weak secret key

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT, balance REAL)''')
    # Plaintext passwords - UNSAFE
    users = [
        (1, 'alice', 'password123', 15000.00),
        (2, 'bob', 'bobpass', 25000.00),
        (3, 'eve', 'evepass', 35000.00),
        (4, 'John', '5862', 50000.00),
        (5, "admin", 'secret123', 100000.00)
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", users)
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # No sanitization
        password = request.form['password']  # No sanitization
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # SQL Injection vulnerability
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        c.execute(query)
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]  # Not escaped - XSS risk
            flash(f'Welcome back, {user[1]}!', 'success')  # XSS
            return redirect(url_for('home'))
        flash('Invalid credentials!', 'error')
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # IDOR vulnerability
    user_id = request.args.get('user_id', session['user_id'])
    c.execute(f"SELECT * FROM users WHERE id = {user_id}")  # SQLi
    user = c.fetchone()
    
    # Get all users for dropdown
    c.execute("SELECT id, username FROM users WHERE id != ?", (session['user_id'],))
    all_users = c.fetchall()
    conn.close()
    
    if not user:
        return redirect(url_for('logout'))
    
    return render_template('home.html', user=user, all_users=all_users)

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    sender_id = session['user_id']
    receiver_id = request.form['receiver_id']  # No validation
    amount = request.form['amount']  # No validation
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        # SQL Injection in transfer
        c.execute(f"SELECT balance FROM users WHERE id = {sender_id}")
        sender_balance = c.fetchone()[0]
        
        c.execute(f"UPDATE users SET balance = balance - {amount} WHERE id = {sender_id}")
        c.execute(f"UPDATE users SET balance = balance + {amount} WHERE id = {receiver_id}")
        conn.commit()
        flash('Transfer completed!', 'success')
    except:
        conn.rollback()
        flash('Transfer failed!', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('home'))

@app.route('/switch_user', methods=['POST'])
def switch_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # No authorization check
    new_user_id = request.form['user_id']
    session['user_id'] = new_user_id
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM users WHERE id = {new_user_id}")  # SQLi
    user = c.fetchone()
    conn.close()
    
    if user:
        session['username'] = user[1]  # Not escaped
        flash(f'Switched to {user[1]}', 'info')  # XSS
    
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
