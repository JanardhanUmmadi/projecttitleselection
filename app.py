from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import datetime
import pandas as pd
import io

app = Flask(__name__)
CORS(app)

DATABASE = 'project_selection.db'

# Initialize the database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            email TEXT PRIMARY KEY,
                            name TEXT NOT NULL,
                            password TEXT NOT NULL,
                            type TEXT NOT NULL DEFAULT 'student')''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS registrations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project TEXT NOT NULL,
                            faculty TEXT NOT NULL,
                            members TEXT NOT NULL,
                            registered_by TEXT NOT NULL,
                            registered_at TEXT NOT NULL)''')

        conn.commit()

init_db()

# ========== ROUTES ==========

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name, email, password = data['name'], data['email'], data['password']
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already exists"}), 409
        cursor.execute("INSERT INTO users (email, name, password) VALUES (?, ?, ?)", (email, name, password))
        conn.commit()
    return jsonify({"status": "success", "message": "Registered successfully"})


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email, password = data['email'], data['password']
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        if user:
            return jsonify({
                "status": "success",
                "user": {"email": user[0], "name": user[1], "type": user[3]}
            })
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@app.route('/register_project', methods=['POST'])
def register_project():
    data = request.json
    project = data['project']
    faculty = data['faculty']
    members = data['members']
    registered_by = data['registered_by']
    registered_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Check if project already taken
        cursor.execute("SELECT * FROM registrations WHERE project=?", (project,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Project already taken"}), 400

        # Check if faculty has 5 groups already
        cursor.execute("SELECT COUNT(*) FROM registrations WHERE faculty=?", (faculty,))
        if cursor.fetchone()[0] >= 5:
            return jsonify({"status": "error", "message": "Faculty has max groups"}), 400

        # Insert registration
        cursor.execute("INSERT INTO registrations (project, faculty, members, registered_by, registered_at) VALUES (?, ?, ?, ?, ?)",
                       (project, faculty, str(members), registered_by, registered_at))
        conn.commit()
    return jsonify({"status": "success", "message": "Project registered successfully"})


@app.route('/get_registrations', methods=['GET'])
def get_registrations():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registrations")
        rows = cursor.fetchall()
        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "project": row[1],
                "faculty": row[2],
                "members": eval(row[3]),
                "registered_by": row[4],
                "registered_at": row[5]
            })
    return jsonify(data)


@app.route('/export_excel', methods=['GET'])
def export_excel():
    with sqlite3.connect(DATABASE) as conn:
        df = pd.read_sql_query("SELECT * FROM registrations", conn)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name="project_registrations.xlsx", as_attachment=True)

# ========== MAIN ==========
if __name__ == '__main__':
    app.run(debug=True)
