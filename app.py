import os
from flask import Flask, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import sqlite3
import csv
import re
import io
from flask import Response

# --- Configuration ---
# Create a folder called 'uploads' in your project directory
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# You must set a secret key for session management (e.g., flash messages)
app.secret_key = 'your_super_secret_key' 

# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """Checks if the file extension is in the allowed set."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- new: CSV -> SQLite import function ---
def import_csv_to_sqlite(csv_path, db_path=None, table_name=None):
    """Import a CSV file into a SQLite database.
    - csv_path: path to the CSV file
    - db_path: path to sqlite db file (defaults to uploads/data.db)
    - table_name: optional table name (defaults to filename without extension)
    Columns are created as TEXT using the CSV header row.
    """
    if db_path is None:
        db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.db')

    if table_name is None:
        base = os.path.splitext(os.path.basename(csv_path))[0]
        # safe table name: alnum + underscore
        table_name = re.sub(r'\W+', '_', base).strip('_') or 'imported_table'

    # Read header and rows
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.reader(fh)
        headers = next(reader, None)
        if not headers:
            return {'db': db_path, 'table': table_name, 'rows': 0}

        # normalize headers to safe column names
        cols = []
        for i, h in enumerate(headers, start=1):
            name = re.sub(r'\W+', '_', h).strip('_').lower()
            if not name:
                name = f'col{i}'
            cols.append(name)

        rows = [tuple(row) for row in reader]

    # Create DB/table and insert rows
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    col_defs = ', '.join(f'"{c}" TEXT' for c in cols)
    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_defs})')

    placeholders = ','.join('?' for _ in cols)
    col_list = ','.join(f'"{c}"' for c in cols)
    insert_sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'
    if rows:
        cur.executemany(insert_sql, rows)
    conn.commit()
    conn.close()

    return {'db': db_path, 'table': table_name, 'rows': len(rows)}

# --- list SQLite tables ---
def list_sqlite_tables(db_path=None):
    """Return a list of table names in the SQLite database."""
    if db_path is None:
        db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.db')
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()
    return tables

# --- Routes ---

@app.route('/')
def main_menu():
    """Renders the main menu page with a button to go to uploads."""
    return render_template('main_menu.html')

@app.route('/upload', methods=['GET'])
def upload_form():
    """Renders the file upload form (GET)."""
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles the file upload POST request."""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']

    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return 'No selected file', 400

    if file and allowed_file(file.filename):
        # Secure the filename to prevent directory traversal attacks
        filename = secure_filename(file.filename)
        # Save the file to the configured UPLOAD_FOLDER
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        # Import CSV into SQLite and report result
        result = import_csv_to_sqlite(save_path)

        # Render a result page that includes a Home button
        return render_template('upload_result.html', filename=filename, result=result)

    return 'File type not allowed', 400

@app.route('/process', methods=['GET'])
def process_page():
    """Render a page that lists tables in the SQLite DB with a 'Process' button (no action yet)."""
    db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.db')
    tables = list_sqlite_tables(db_path)
    return render_template('process.html', tables=tables, db=db_path)

# --- new: export table as pipe-delimited CSV ---
@app.route('/process/export/<table_name>', methods=['GET'])
def export_table(table_name):
    """Export the specified SQLite table as a pipe-delimited CSV for download."""
    # basic validation for safe table names
    if not re.match(r'^[A-Za-z0-9_]+$', table_name):
        return 'Invalid table name', 400

    db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.db')
    if not os.path.exists(db_path):
        return 'Database not found', 404

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(f'SELECT * FROM "{table_name}"')
    except sqlite3.OperationalError:
        conn.close()
        return 'Table not found', 404

    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter='|', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(cols)
    for row in rows:
        writer.writerow(row)
    data = output.getvalue()
    output.close()

    filename = f'{table_name}.csv'
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': 'text/csv; charset=utf-8'
    }
    return Response(data, headers=headers)

if __name__ == '__main__':
    # You can set debug=True for automatic reloading during development
    app.run(debug=True)