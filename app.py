import os
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Flask, g, jsonify, request, send_from_directory, abort
from werkzeug.utils import secure_filename

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, 'instance', 'rockson.db')
SCHEMA    = os.path.join(BASE_DIR, 'schema.sql')
IMG_DIR   = os.path.join(BASE_DIR, 'static', 'images', 'exercises')
ALLOWED   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    with open(SCHEMA) as f:
        db.executescript(f.read())
    db.commit()
    db.close()

def rows_to_list(rows):
    return [dict(r) for r in rows]


# ── Serve the SPA ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/static/images/exercises/<path:filename>')
def serve_exercise_image(filename):
    return send_from_directory(IMG_DIR, filename)


# ── Settings ──────────────────────────────────────────────────────────────────

@app.route('/api/settings', methods=['GET'])
def get_settings():
    db   = get_db()
    rows = db.execute('SELECT key, value FROM settings').fetchall()
    return jsonify({r['key']: r['value'] for r in rows})

@app.route('/api/settings', methods=['PUT'])
def update_settings():
    db   = get_db()
    data = request.get_json()
    for key, value in data.items():
        db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/settings/logo', methods=['POST'])
def upload_logo():
    if 'file' not in request.files:
        abort(400, 'No file part')
    f = request.files['file']
    if not f.filename:
        abort(400, 'No file selected')
    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED:
        abort(400, 'File type not allowed')
    filename = 'pt_logo.' + ext
    logo_dir = os.path.join(BASE_DIR, 'static', 'images')
    os.makedirs(logo_dir, exist_ok=True)
    f.save(os.path.join(logo_dir, filename))
    db = get_db()
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('pt_logo', ?)", (filename,))
    db.commit()
    return jsonify({'filename': filename})


# ── Muscle groups ─────────────────────────────────────────────────────────────

@app.route('/api/muscle-groups', methods=['GET'])
def get_muscle_groups():
    db   = get_db()
    rows = db.execute(
        'SELECT * FROM muscle_groups ORDER BY sort_order, name'
    ).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/muscle-groups', methods=['POST'])
def create_muscle_group():
    db   = get_db()
    data = request.get_json()
    cur  = db.execute(
        'INSERT INTO muscle_groups (name, color, sort_order) VALUES (?, ?, ?)',
        (data['name'], data.get('color', '#f9b233'), data.get('sort_order', 99))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid}), 201

@app.route('/api/muscle-groups/<int:mgid>', methods=['PUT'])
def update_muscle_group(mgid):
    db   = get_db()
    data = request.get_json()
    db.execute(
        'UPDATE muscle_groups SET name=?, color=?, sort_order=?, active=? WHERE id=?',
        (data['name'], data.get('color', '#f9b233'),
         data.get('sort_order', 99), data.get('active', 1), mgid)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/muscle-groups/<int:mgid>', methods=['DELETE'])
def delete_muscle_group(mgid):
    db = get_db()
    db.execute('DELETE FROM muscle_groups WHERE id=?', (mgid,))
    db.commit()
    return jsonify({'ok': True})


# ── Exercise library ──────────────────────────────────────────────────────────

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    db   = get_db()
    rows = db.execute('''
        SELECT e.*, mg.name AS muscle_group_name, mg.color AS muscle_group_color
        FROM exercises e
        LEFT JOIN muscle_groups mg ON e.muscle_group_id = mg.id
        ORDER BY mg.sort_order, e.name
    ''').fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/exercises', methods=['POST'])
def create_exercise():
    db   = get_db()
    data = request.get_json()
    cur  = db.execute(
        '''INSERT INTO exercises
           (name, muscle_group_id, default_sets, default_reps, is_default)
           VALUES (?, ?, ?, ?, 0)''',
        (data['name'], data.get('muscle_group_id'),
         data.get('default_sets'), data.get('default_reps'))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid}), 201

@app.route('/api/exercises/<int:eid>', methods=['PUT'])
def update_exercise(eid):
    db   = get_db()
    data = request.get_json()
    db.execute(
        '''UPDATE exercises SET name=?, muscle_group_id=?,
           default_sets=?, default_reps=? WHERE id=?''',
        (data['name'], data.get('muscle_group_id'),
         data.get('default_sets'), data.get('default_reps'), eid)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/exercises/<int:eid>', methods=['DELETE'])
def delete_exercise(eid):
    db = get_db()
    db.execute('DELETE FROM exercises WHERE id=?', (eid,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/exercises/<int:eid>/image', methods=['POST'])
def upload_exercise_image(eid):
    if 'file' not in request.files:
        abort(400, 'No file')
    f   = request.files['file']
    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED:
        abort(400, 'File type not allowed')
    filename = secure_filename(f'exercise_{eid}.{ext}')
    os.makedirs(IMG_DIR, exist_ok=True)
    f.save(os.path.join(IMG_DIR, filename))
    db = get_db()
    db.execute('UPDATE exercises SET image_filename=? WHERE id=?', (filename, eid))
    db.commit()
    return jsonify({'filename': filename})


# ── Clients ───────────────────────────────────────────────────────────────────

@app.route('/api/clients', methods=['GET'])
def get_clients():
    db   = get_db()
    rows = db.execute(
        'SELECT * FROM clients ORDER BY name'
    ).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/clients', methods=['POST'])
def create_client():
    db   = get_db()
    data = request.get_json()
    cur  = db.execute(
        'INSERT INTO clients (name, notes) VALUES (?, ?)',
        (data['name'], data.get('notes', ''))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid, 'name': data['name']}), 201

@app.route('/api/clients/<int:cid>', methods=['PUT'])
def update_client(cid):
    db   = get_db()
    data = request.get_json()
    db.execute(
        'UPDATE clients SET name=?, notes=? WHERE id=?',
        (data['name'], data.get('notes', ''), cid)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/clients/<int:cid>', methods=['DELETE'])
def delete_client(cid):
    db = get_db()
    db.execute('DELETE FROM clients WHERE id=?', (cid,))
    db.commit()
    return jsonify({'ok': True})


# ── Templates ─────────────────────────────────────────────────────────────────

@app.route('/api/templates', methods=['GET'])
def get_templates():
    db   = get_db()
    rows = db.execute('SELECT * FROM templates ORDER BY name').fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/templates', methods=['POST'])
def create_template():
    db   = get_db()
    data = request.get_json()
    cur  = db.execute(
        'INSERT INTO templates (name, description) VALUES (?, ?)',
        (data['name'], data.get('description', ''))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid}), 201

@app.route('/api/templates/<int:tid>', methods=['DELETE'])
def delete_template(tid):
    db = get_db()
    db.execute('DELETE FROM templates WHERE id=?', (tid,))
    db.commit()
    return jsonify({'ok': True})


# ── Schedules ─────────────────────────────────────────────────────────────────

@app.route('/api/clients/<int:cid>/schedules', methods=['GET'])
def get_client_schedules(cid):
    db   = get_db()
    rows = db.execute(
        '''SELECT * FROM schedules WHERE client_id=?
           ORDER BY year DESC, week_number DESC''',
        (cid,)
    ).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    db   = get_db()
    data = request.get_json()

    # Auto-calculate week dates if not provided
    week   = int(data['week_number'])
    year   = int(data.get('year', datetime.now().year))
    monday = datetime.strptime(f'{year}-W{week:02d}-1', '%G-W%V-%u')
    sunday = monday + timedelta(days=6)

    cur = db.execute(
        '''INSERT INTO schedules
           (client_id, week_number, year, date_start, date_end, status, notes)
           VALUES (?, ?, ?, ?, ?, 'draft', ?)''',
        (data['client_id'], week, year,
         data.get('date_start', monday.strftime('%Y-%m-%d')),
         data.get('date_end',   sunday.strftime('%Y-%m-%d')),
         data.get('notes', ''))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid}), 201

@app.route('/api/schedules/<int:sid>', methods=['GET'])
def get_schedule(sid):
    db       = get_db()
    schedule = db.execute('SELECT * FROM schedules WHERE id=?', (sid,)).fetchone()
    if not schedule:
        abort(404)

    days = db.execute(
        'SELECT * FROM schedule_days WHERE schedule_id=? ORDER BY sort_order, day_of_week',
        (sid,)
    ).fetchall()

    result = dict(schedule)
    result['days'] = []

    for day in days:
        d = dict(day)

        # muscle groups for this day
        mgs = db.execute(
            '''SELECT mg.* FROM day_muscle_groups dmg
               JOIN muscle_groups mg ON dmg.muscle_group_id = mg.id
               WHERE dmg.schedule_day_id=?''',
            (day['id'],)
        ).fetchall()
        d['muscle_groups'] = rows_to_list(mgs)

        # exercises for this day
        exs = db.execute(
            '''SELECT de.*,
                      e.name  AS library_name,
                      mg.name AS muscle_group_name,
                      mg.color AS muscle_group_color
               FROM day_exercises de
               LEFT JOIN exercises     e  ON de.exercise_id     = e.id
               LEFT JOIN muscle_groups mg ON de.muscle_group_id = mg.id
               WHERE de.schedule_day_id=?
               ORDER BY de.sort_order''',
            (day['id'],)
        ).fetchall()
        d['exercises'] = rows_to_list(exs)

        result['days'].append(d)

    return jsonify(result)

@app.route('/api/schedules/<int:sid>', methods=['PUT'])
def update_schedule(sid):
    db   = get_db()
    data = request.get_json()
    db.execute(
        '''UPDATE schedules SET week_number=?, year=?, date_start=?, date_end=?,
           status=?, notes=?, updated_at=datetime('now') WHERE id=?''',
        (data['week_number'], data.get('year', datetime.now().year),
         data.get('date_start'), data.get('date_end'),
         data.get('status', 'draft'), data.get('notes', ''), sid)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/schedules/<int:sid>', methods=['DELETE'])
def delete_schedule(sid):
    db = get_db()
    db.execute('DELETE FROM schedules WHERE id=?', (sid,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/schedules/<int:sid>/finalize', methods=['POST'])
def finalize_schedule(sid):
    db = get_db()
    db.execute(
        "UPDATE schedules SET status='final', updated_at=datetime('now') WHERE id=?",
        (sid,)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/schedules/<int:sid>/duplicate', methods=['POST'])
def duplicate_schedule(sid):
    """Duplicate a schedule as a new draft for a given week."""
    db   = get_db()
    data = request.get_json()
    src  = db.execute('SELECT * FROM schedules WHERE id=?', (sid,)).fetchone()
    if not src:
        abort(404)

    week   = int(data['week_number'])
    year   = int(data.get('year', datetime.now().year))
    monday = datetime.strptime(f'{year}-W{week:02d}-1', '%G-W%V-%u')
    sunday = monday + timedelta(days=6)

    new_sid_cur = db.execute(
        '''INSERT INTO schedules
           (client_id, week_number, year, date_start, date_end, status, notes)
           VALUES (?, ?, ?, ?, ?, 'draft', ?)''',
        (src['client_id'], week, year,
         monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d'),
         src['notes'] or '')
    )
    new_sid = new_sid_cur.lastrowid

    # Copy days
    old_days = db.execute(
        'SELECT * FROM schedule_days WHERE schedule_id=? ORDER BY sort_order',
        (sid,)
    ).fetchall()

    for old_day in old_days:
        new_day_cur = db.execute(
            '''INSERT INTO schedule_days (schedule_id, day_of_week, day_label, sort_order)
               VALUES (?, ?, ?, ?)''',
            (new_sid, old_day['day_of_week'],
             old_day['day_label'], old_day['sort_order'])
        )
        new_day_id = new_day_cur.lastrowid

        # Copy muscle groups
        mgs = db.execute(
            'SELECT * FROM day_muscle_groups WHERE schedule_day_id=?',
            (old_day['id'],)
        ).fetchall()
        for mg in mgs:
            db.execute(
                'INSERT INTO day_muscle_groups (schedule_day_id, muscle_group_id) VALUES (?, ?)',
                (new_day_id, mg['muscle_group_id'])
            )

        # Copy exercises
        exs = db.execute(
            'SELECT * FROM day_exercises WHERE schedule_day_id=? ORDER BY sort_order',
            (old_day['id'],)
        ).fetchall()
        for ex in exs:
            db.execute(
                '''INSERT INTO day_exercises
                   (schedule_day_id, exercise_id, custom_name, muscle_group_id,
                    set_code, sets, reps, image_filename, notes, sort_order, is_warmup)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (new_day_id, ex['exercise_id'], ex['custom_name'],
                 ex['muscle_group_id'], ex['set_code'], ex['sets'],
                 ex['reps'], ex['image_filename'], ex['notes'],
                 ex['sort_order'], ex['is_warmup'])
            )

    db.commit()
    return jsonify({'id': new_sid}), 201


# ── Schedule days ─────────────────────────────────────────────────────────────

@app.route('/api/schedules/<int:sid>/days', methods=['POST'])
def create_day(sid):
    db   = get_db()
    data = request.get_json()
    cur  = db.execute(
        '''INSERT INTO schedule_days (schedule_id, day_of_week, day_label, sort_order)
           VALUES (?, ?, ?, ?)''',
        (sid, data['day_of_week'], data.get('day_label', ''),
         data.get('sort_order', 0))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid}), 201

@app.route('/api/days/<int:did>', methods=['PUT'])
def update_day(did):
    db   = get_db()
    data = request.get_json()
    db.execute(
        'UPDATE schedule_days SET day_of_week=?, day_label=?, sort_order=? WHERE id=?',
        (data['day_of_week'], data.get('day_label', ''),
         data.get('sort_order', 0), did)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/days/<int:did>', methods=['DELETE'])
def delete_day(did):
    db = get_db()
    db.execute('DELETE FROM schedule_days WHERE id=?', (did,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/days/<int:did>/muscle-groups', methods=['PUT'])
def set_day_muscle_groups(did):
    db   = get_db()
    data = request.get_json()  # { muscle_group_ids: [1,2,3] }
    db.execute('DELETE FROM day_muscle_groups WHERE schedule_day_id=?', (did,))
    for mgid in data.get('muscle_group_ids', []):
        db.execute(
            'INSERT INTO day_muscle_groups (schedule_day_id, muscle_group_id) VALUES (?, ?)',
            (did, mgid)
        )
    db.commit()
    return jsonify({'ok': True})


# ── Day exercises ─────────────────────────────────────────────────────────────

@app.route('/api/days/<int:did>/exercises', methods=['POST'])
def add_exercise_to_day(did):
    db   = get_db()
    data = request.get_json()

    # Resolve defaults from library if exercise_id provided
    ex_row = None
    if data.get('exercise_id'):
        ex_row = db.execute(
            'SELECT * FROM exercises WHERE id=?', (data['exercise_id'],)
        ).fetchone()

    sets = data.get('sets') or (ex_row['default_sets'] if ex_row else None)
    reps = data.get('reps') or (ex_row['default_reps'] if ex_row else None)
    mgid = data.get('muscle_group_id') or (ex_row['muscle_group_id'] if ex_row else None)

    # Next sort_order
    max_order = db.execute(
        'SELECT COALESCE(MAX(sort_order),0) FROM day_exercises WHERE schedule_day_id=?',
        (did,)
    ).fetchone()[0]

    cur = db.execute(
        '''INSERT INTO day_exercises
           (schedule_day_id, exercise_id, custom_name, muscle_group_id,
            set_code, sets, reps, notes, sort_order, is_warmup)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (did, data.get('exercise_id'), data.get('custom_name'),
         mgid, data.get('set_code', ''),
         sets, reps, data.get('notes', ''),
         max_order + 1, data.get('is_warmup', 0))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid}), 201

@app.route('/api/exercises/day/<int:dex_id>', methods=['PUT'])
def update_day_exercise(dex_id):
    db   = get_db()
    data = request.get_json()
    # Fetch existing row so auto-save (which only sends a subset of fields)
    # never overwrites columns it didn't touch with None.
    existing = db.execute(
        'SELECT * FROM day_exercises WHERE id=?', (dex_id,)
    ).fetchone()
    if not existing:
        abort(404)
    db.execute(
        '''UPDATE day_exercises SET exercise_id=?, custom_name=?, muscle_group_id=?,
           set_code=?, sets=?, reps=?, notes=?, sort_order=?, is_warmup=?
           WHERE id=?''',
        (data.get('exercise_id',    existing['exercise_id']),
         data.get('custom_name',    existing['custom_name']),
         data.get('muscle_group_id',existing['muscle_group_id']),
         data.get('set_code',       existing['set_code']),
         data.get('sets',           existing['sets']),
         data.get('reps',           existing['reps']),
         data.get('notes',          existing['notes']),
         data.get('sort_order',     existing['sort_order']),
         data.get('is_warmup',      existing['is_warmup']),
         dex_id)
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/exercises/day/<int:dex_id>', methods=['DELETE'])
def delete_day_exercise(dex_id):
    db = get_db()
    db.execute('DELETE FROM day_exercises WHERE id=?', (dex_id,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/exercises/day/<int:dex_id>/image', methods=['POST'])
def upload_day_exercise_image(dex_id):
    if 'file' not in request.files:
        abort(400, 'No file')
    f   = request.files['file']
    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED:
        abort(400, 'File type not allowed')
    filename = secure_filename(f'dex_{dex_id}.{ext}')
    os.makedirs(IMG_DIR, exist_ok=True)
    f.save(os.path.join(IMG_DIR, filename))
    db = get_db()
    db.execute('UPDATE day_exercises SET image_filename=? WHERE id=?', (filename, dex_id))
    db.commit()
    return jsonify({'filename': filename})

@app.route('/api/days/<int:did>/exercises/reorder', methods=['PUT'])
def reorder_exercises(did):
    """Accept ordered list of exercise IDs and update sort_order."""
    db   = get_db()
    data = request.get_json()  # { ids: [3, 1, 2] }
    for i, eid in enumerate(data['ids']):
        db.execute(
            'UPDATE day_exercises SET sort_order=? WHERE id=? AND schedule_day_id=?',
            (i, eid, did)
        )
    db.commit()
    return jsonify({'ok': True})


# ── PDF export ────────────────────────────────────────────────────────────────

@app.route('/api/schedules/<int:sid>/pdf', methods=['GET'])
def export_pdf(sid):
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        abort(500, 'WeasyPrint not installed')

    import io
    from flask import make_response

    mode     = request.args.get('mode', 'dark')   # dark | light
    schedule = _build_schedule_data(sid)
    if not schedule:
        abort(404)

    html_str = _render_pdf_html(schedule, mode)
    pdf_bytes = HTML(string=html_str, base_url=BASE_DIR).write_pdf()

    client_name = schedule['client_name'].replace(' ', '_')
    filename    = f'Rockson_{client_name}_Week{schedule["week_number"]}.pdf'

    resp = make_response(pdf_bytes)
    resp.headers['Content-Type']        = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp

@app.route('/api/schedules/<int:sid>/pdf/preview', methods=['GET'])
def preview_pdf_html(sid):
    """Return the raw HTML that would be converted to PDF (for in-browser preview)."""
    mode     = request.args.get('mode', 'dark')
    schedule = _build_schedule_data(sid)
    if not schedule:
        abort(404)
    return _render_pdf_html(schedule, mode), 200, {'Content-Type': 'text/html'}


def _build_schedule_data(sid):
    db       = get_db()
    schedule = db.execute(
        '''SELECT s.*, c.name AS client_name
           FROM schedules s JOIN clients c ON s.client_id = c.id
           WHERE s.id=?''', (sid,)
    ).fetchone()
    if not schedule:
        return None

    settings_rows = db.execute('SELECT key, value FROM settings').fetchall()
    settings      = {r['key']: r['value'] for r in settings_rows}

    days = db.execute(
        'SELECT * FROM schedule_days WHERE schedule_id=? ORDER BY sort_order, day_of_week',
        (sid,)
    ).fetchall()

    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    result    = dict(schedule)
    result['settings'] = settings
    result['days']     = []

    for day in days:
        d  = dict(day)
        d['day_name'] = day_names[day['day_of_week']]

        mgs = db.execute(
            '''SELECT mg.* FROM day_muscle_groups dmg
               JOIN muscle_groups mg ON dmg.muscle_group_id = mg.id
               WHERE dmg.schedule_day_id=?''', (day['id'],)
        ).fetchall()
        d['muscle_groups'] = rows_to_list(mgs)

        exs = db.execute(
            '''SELECT de.*,
                      COALESCE(de.custom_name, e.name) AS display_name,
                      mg.name  AS muscle_group_name,
                      mg.color AS muscle_group_color
               FROM day_exercises de
               LEFT JOIN exercises     e  ON de.exercise_id     = e.id
               LEFT JOIN muscle_groups mg ON de.muscle_group_id = mg.id
               WHERE de.schedule_day_id=?
               ORDER BY de.sort_order''', (day['id'],)
        ).fetchall()
        d['exercises'] = rows_to_list(exs)
        result['days'].append(d)

    # Weekly volume per muscle group
    volume = db.execute(
        '''SELECT mg.name, mg.color, SUM(de.sets) AS total_sets
           FROM day_exercises de
           JOIN schedule_days sd ON de.schedule_day_id = sd.id
           JOIN muscle_groups mg ON de.muscle_group_id = mg.id
           WHERE sd.schedule_id=? AND de.is_warmup=0
           GROUP BY mg.id
           ORDER BY mg.sort_order''', (sid,)
    ).fetchall()
    result['volume'] = rows_to_list(volume)

    return result


def _render_pdf_html(data, mode='dark'):
    """Build the full HTML string for the PDF export."""
    is_dark = (mode == 'dark')

    bg      = '#0d0d0d' if is_dark else '#ffffff'
    surface = '#141414' if is_dark else '#f8f8f8'
    card    = '#1a1a1a' if is_dark else '#f0f0f0'
    border  = '#2a2a2a' if is_dark else '#e0e0e0'
    text    = '#f0f0f0' if is_dark else '#111111'
    muted   = '#666666' if is_dark else '#999999'
    gold    = '#f9b233'

    pt_name = data['settings'].get('pt_name', 'Rockson Performance')

    # Build stats
    training_days = len(data['days'])
    total_sets    = sum(v['total_sets'] or 0 for v in data['volume'])

    # Format dates
    try:
        ds = datetime.strptime(data['date_start'], '%Y-%m-%d').strftime('%d %b %Y')
        de = datetime.strptime(data['date_end'],   '%Y-%m-%d').strftime('%d %b %Y')
        date_range = f'{ds} – {de}'
    except Exception:
        date_range = ''

    pages_html = ''
    total_pages = len(data['days'])

    for page_num, day in enumerate(data['days'], 1):
        mgs_str = ' · '.join(mg['name'] for mg in day['muscle_groups'])
        focus   = ' · '.join(
            ex['display_name'] for ex in day['exercises'] if not ex['is_warmup']
        )[:80]

        # Warmup rows
        warmup_html = ''
        for ex in day['exercises']:
            if ex['is_warmup']:
                warmup_html += f'''
                <tr style="background:rgba(185,246,202,0.05)">
                  <td colspan="2" style="padding:7px 14px;font-size:11px;
                      color:#b9f6ca;font-weight:500;letter-spacing:1px;
                      text-transform:uppercase;border-bottom:1px solid {border}">
                    WARM-UP — {ex["display_name"]}
                    {'<span style="font-size:10px;color:'+muted+';font-weight:400"> — '+ex["notes"]+'</span>' if ex.get("notes") else ''}
                  </td>
                  <td style="padding:7px 14px;font-size:11px;color:#b9f6ca;
                      font-weight:600;text-align:right;border-bottom:1px solid {border}">
                    {ex["sets"] or ''} × {ex["reps"] or ''}
                  </td>
                  <td style="border-bottom:1px solid {border}"></td>
                </tr>'''

        # Exercise rows
        exercise_rows = ''
        for ex in day['exercises']:
            if ex['is_warmup']:
                continue
            pill_color  = ex.get('muscle_group_color') or gold
            mg_name     = ex.get('muscle_group_name') or ''
            notes_html  = f'<div style="font-size:10px;font-style:italic;color:{muted};margin-top:4px;line-height:1.5">{ex["notes"]}</div>' if ex.get('notes') else ''

            # Resolve image path
            img_path = None
            img_file = ex.get('image_filename')
            if img_file:
                candidate = os.path.join(IMG_DIR, img_file)
                if os.path.exists(candidate):
                    img_path = candidate

            if img_path:
                # Large image layout: exercise info left, image right
                exercise_rows += (
                    f'<tr style="border-top:1px solid {border}">'
                    f'<td style="padding:10px 8px 10px 14px;font-family:Arial Black,Arial,sans-serif;'
                    f'font-size:13px;color:{muted};width:42px;vertical-align:top;padding-top:14px">'
                    f'{ex.get("set_code") or ""}</td>'
                    f'<td style="padding:10px 8px;vertical-align:top">'
                    f'<div style="font-size:14px;font-weight:600;color:{text};margin-bottom:5px">{ex["display_name"]}</div>'
                    f'<div style="display:inline-block;font-size:9px;padding:2px 7px;border-radius:12px;'
                    f'font-weight:500;text-transform:uppercase;letter-spacing:0.8px;'
                    f'background:{pill_color}22;color:{pill_color}">{mg_name}</div>'
                    f'{notes_html}</td>'
                    f'<td style="padding:10px 8px;width:70px;text-align:center;vertical-align:top;padding-top:14px">'
                    f'<span style="font-family:Arial Black,Arial,sans-serif;font-size:20px;color:{gold};font-weight:900">{ex["sets"] or ""}</span>'
                    f'<div style="font-size:9px;color:{muted};margin-top:2px;letter-spacing:1px;text-transform:uppercase">sets</div></td>'
                    f'<td style="padding:10px 8px;width:90px;vertical-align:top;padding-top:14px">'
                    f'<span style="font-size:15px;font-weight:600;color:{gold}">{ex["reps"] or ""}</span>'
                    f'<div style="font-size:9px;color:{muted};margin-top:2px;letter-spacing:1px;text-transform:uppercase">reps</div></td>'
                    f'<td style="padding:6px 14px 6px 8px;width:136px;vertical-align:middle;text-align:right">'
                    f'<img src="file://{img_path}" style="width:120px;height:120px;object-fit:contain;'
                    f'border-radius:6px;display:block;margin-left:auto;background:{surface}"></td>'
                    f'</tr>'
                )
            else:
                # Compact layout: no image
                exercise_rows += (
                    f'<tr style="border-top:1px solid {border}">'
                    f'<td style="padding:9px 8px 9px 14px;font-family:Arial Black,Arial,sans-serif;'
                    f'font-size:13px;color:{muted};width:42px">{ex.get("set_code") or ""}</td>'
                    f'<td style="padding:9px 8px">'
                    f'<div style="font-size:13px;font-weight:600;color:{text}">{ex["display_name"]}</div>'
                    f'<div style="display:inline-block;font-size:9px;padding:2px 7px;border-radius:12px;'
                    f'margin-top:4px;font-weight:500;text-transform:uppercase;letter-spacing:0.8px;'
                    f'background:{pill_color}22;color:{pill_color}">{mg_name}</div>'
                    f'{notes_html}</td>'
                    f'<td style="padding:9px 8px;width:70px;text-align:center">'
                    f'<span style="font-family:Arial Black,Arial,sans-serif;font-size:18px;color:{gold};font-weight:900">{ex["sets"] or ""}</span></td>'
                    f'<td style="padding:9px 8px;width:90px;font-size:13px;font-weight:600;color:{gold}">{ex["reps"] or ""}</td>'
                    f'<td style="padding:9px 14px 9px 8px;width:136px"></td>'
                    f'</tr>'
                )

        # Volume bars for this page
        vol_bars = ''
        max_vol = max((v['total_sets'] or 0 for v in data['volume']), default=1)
        for v in data['volume']:
            pct   = int((v['total_sets'] or 0) / max(max_vol, 1) * 100)
            color = v['color'] or gold
            vol_bars += f'''
            <div style="background:{surface};border:1px solid {border};
                border-radius:4px;padding:10px 12px;flex:1;min-width:80px">
              <div style="font-size:8px;text-transform:uppercase;letter-spacing:1px;
                  color:{muted};margin-bottom:5px">{v["name"]}</div>
              <div style="height:2px;background:{border};border-radius:2px;
                  margin-bottom:6px;overflow:hidden">
                <div style="height:100%;width:{pct}%;background:{color};border-radius:2px"></div>
              </div>
              <div style="font-family:Arial Black,Arial,sans-serif;font-size:20px;
                  color:{color};line-height:1">{v["total_sets"] or 0}</div>
              <div style="font-size:8px;color:{muted};margin-top:2px">sets/week</div>
            </div>'''

        pages_html += f'''
        <div style="background:{bg};color:{text};font-family:Arial,sans-serif;
            width:210mm;min-height:297mm;page-break-after:always;
            box-sizing:border-box;display:flex;flex-direction:column">

          <!-- Header -->
          <div style="background:{surface};border-bottom:1px solid {border};
              padding:18px 28px;display:flex;align-items:flex-start;
              justify-content:space-between">
            <div>
              <div style="font-family:Arial Black,Arial,sans-serif;font-size:14px;
                  letter-spacing:3px;color:{gold};text-transform:uppercase">
                ▲ {pt_name}
              </div>
              <div style="font-size:9px;color:{muted};letter-spacing:1.5px;
                  text-transform:uppercase;margin-top:3px">Personal Training Schedule</div>
            </div>
            <div style="text-align:right">
              <div style="font-size:9px;color:{muted};letter-spacing:2px;
                  text-transform:uppercase;margin-bottom:3px">Athlete</div>
              <div style="font-family:Arial Black,Arial,sans-serif;font-size:24px;
                  letter-spacing:2px;color:{gold};line-height:1">{data["client_name"]}</div>
              <div style="font-size:9px;color:{muted};margin-top:4px;letter-spacing:1px">
                Week {data["week_number"]} · {date_range}
              </div>
            </div>
          </div>

          <!-- Stats bar -->
          <div style="display:flex;background:{surface};border-bottom:1px solid {border}">
            <div style="flex:1;padding:12px 18px;border-right:1px solid {border}">
              <div style="font-family:Arial Black,Arial,sans-serif;font-size:22px;
                  color:{gold};line-height:1">{training_days}</div>
              <div style="font-size:9px;color:{muted};text-transform:uppercase;
                  letter-spacing:1.5px;margin-top:3px">Workouts / week</div>
            </div>
            <div style="flex:1;padding:12px 18px;border-right:1px solid {border}">
              <div style="font-family:Arial Black,Arial,sans-serif;font-size:22px;
                  color:{gold};line-height:1">{total_sets}</div>
              <div style="font-size:9px;color:{muted};text-transform:uppercase;
                  letter-spacing:1.5px;margin-top:3px">Total sets / week</div>
            </div>
            <div style="flex:1;padding:12px 18px;border-right:1px solid {border}">
              <div style="font-family:Arial Black,Arial,sans-serif;font-size:22px;
                  color:{gold};line-height:1">{page_num}/{total_pages}</div>
              <div style="font-size:9px;color:{muted};text-transform:uppercase;
                  letter-spacing:1.5px;margin-top:3px">Day</div>
            </div>
            <div style="flex:2;padding:12px 18px">
              <div style="font-size:9px;color:{muted};text-transform:uppercase;
                  letter-spacing:1.5px;margin-bottom:4px">Muscle groups today</div>
              <div style="font-size:12px;font-weight:600;color:{text}">{mgs_str}</div>
            </div>
          </div>

          <!-- Day header -->
          <div style="padding:16px 28px 12px;border-bottom:1px solid {border}">
            <div style="display:flex;align-items:center;justify-content:space-between">
              <div>
                <div style="font-family:Arial Black,Arial,sans-serif;font-size:28px;
                    letter-spacing:1px;line-height:1;color:{text}">
                  {day.get("day_label") or f"Day {page_num}"} — {day["day_name"]}
                </div>
                <div style="font-size:10px;color:{muted};margin-top:4px;
                    letter-spacing:0.8px;text-transform:uppercase">{focus}</div>
              </div>
              <div style="font-family:Arial Black,Arial,sans-serif;font-size:12px;
                  color:{gold};border:1px solid {border};padding:6px 14px;
                  border-radius:3px;letter-spacing:2px;text-transform:uppercase">
                {day["day_name"]}
              </div>
            </div>
          </div>

          <!-- Exercise table -->
          <div style="flex:1;padding:0 0 0 0">
            <table style="width:100%;border-collapse:collapse">
              <thead>
                <tr style="background:{surface}">
                  <th style="padding:7px 8px 7px 14px;font-size:9px;font-weight:500;
                      text-transform:uppercase;letter-spacing:2px;color:{muted};
                      text-align:left;width:42px">Code</th>
                  <th style="padding:7px 8px;font-size:9px;font-weight:500;
                      text-transform:uppercase;letter-spacing:2px;color:{muted};
                      text-align:left">Exercise</th>
                  <th style="padding:7px 8px;font-size:9px;font-weight:500;
                      text-transform:uppercase;letter-spacing:2px;color:{muted};
                      text-align:center;width:70px">Sets</th>
                  <th style="padding:7px 8px;font-size:9px;font-weight:500;
                      text-transform:uppercase;letter-spacing:2px;color:{muted};
                      text-align:left;width:90px">Reps</th>
                  <th style="padding:7px 14px 7px 8px;font-size:9px;font-weight:500;
                      text-transform:uppercase;letter-spacing:2px;color:{muted};
                      text-align:left;width:60px">Photo</th>
                </tr>
              </thead>
              <tbody>
                {warmup_html}
                {exercise_rows}
              </tbody>
            </table>
          </div>

          <!-- Volume section -->
          <div style="padding:14px 28px;border-top:1px solid {border}">
            <div style="font-size:9px;font-weight:500;letter-spacing:2px;
                text-transform:uppercase;color:{muted};margin-bottom:10px">
              Weekly volume — total sets per muscle group
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              {vol_bars}
            </div>
          </div>

          <!-- Footer -->
          <div style="background:{surface};border-top:1px solid {border};
              padding:8px 28px;display:flex;align-items:center;
              justify-content:space-between">
            <div style="font-size:9px;color:{muted};letter-spacing:1px;
                text-transform:uppercase">
              {pt_name} · {data["client_name"]} · Week {data["week_number"]}
            </div>
            <div style="font-size:9px;color:{muted};letter-spacing:1px;
                text-transform:uppercase">Page {page_num} of {total_pages}</div>
          </div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 0; }}
  body {{ margin: 0; padding: 0; }}
</style>
</head>
<body>{pages_html}</body>
</html>'''


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5002, debug=False)
