"""
NEXTRIDE - College Ride Sharing System
Flask Backend with MySQL (primary) and SQLite (fallback)
"""
# Template reload trigger - 2026-04-20 07:20:45

import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import math

from flask import (Flask, request, jsonify, session,
                   render_template, redirect, url_for, flash)
from werkzeug.security import generate_password_hash, check_password_hash

# ── App Config ────────────────────────────────────────────────
app = Flask(__name__)  # templates/ and static/ are in the same folder as app.py
app.secret_key = os.environ.get('SECRET_KEY', 'nextride_secret_2024')

# ── Database Selection ────────────────────────────────────────
USE_MYSQL = False   # Set True + fill creds to use MySQL

MYSQL_CONFIG = {
    'host':     os.environ.get('MYSQL_HOST', 'localhost'),
    'user':     os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASS', ''),
    'database': os.environ.get('MYSQL_DB',   'nextride'),
}

SQLITE_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'nextride.db')
# Also support running from within backend/ directly
if not os.path.isdir(os.path.join(os.path.dirname(__file__), '..', 'database')):
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'nextride.db')


# ── Penalty Configuration ─────────────────────────────────────
PENALTY_RATES = {
    'cancellation_rider':       100,    # Rider cancels booking
    'cancellation_driver':      200,    # Driver cancels ride
    'delay_per_minute':         2,      # ₹2 per minute late (capped)
    'missed_ride':              150,    # Rider didn't show up
    'delay_cap':                100,    # Maximum delay penalty
}


# ── DB Helpers ────────────────────────────────────────────────
def get_db():
    """Return a database connection (MySQL or SQLite)."""
    if USE_MYSQL:
        import mysql.connector
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        conn.autocommit = False
        return conn, conn.cursor(dictionary=True)
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn, conn.cursor()


def row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return dict(row)


def rows_to_list(rows):
    return [row_to_dict(r) for r in rows]


# ── Penalty Helper Functions ──────────────────────────────────
def apply_penalty(conn, cur, student_id, request_id, penalty_type, amount, reason=""):
    """Apply a penalty to a student and record it in the Penalties table."""
    ph = '?' if not USE_MYSQL else '%s'
    
    # Check if penalty already exists for this request
    cur.execute(f"""
        SELECT penalty_id FROM Penalties 
        WHERE student_id={ph} AND request_id={ph} AND penalty_type={ph}
    """, (student_id, request_id, penalty_type))
    
    if cur.fetchone() is None:  # Only apply if not already applied
        cur.execute(f"""
            INSERT INTO Penalties (student_id, request_id, penalty_type, amount, reason)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        """, (student_id, request_id, penalty_type, amount, reason))
        conn.commit()
        return True
    return False


def calculate_delay_penalty(scheduled_time, actual_time):
    """Calculate penalty based on delay in minutes."""
    try:
        if isinstance(scheduled_time, str):
            scheduled = datetime.strptime(scheduled_time, '%Y-%m-%d %H:%M:%S')
        else:
            scheduled = scheduled_time
            
        if isinstance(actual_time, str):
            actual = datetime.strptime(actual_time, '%Y-%m-%d %H:%M:%S')
        else:
            actual = actual_time
        
        delay_minutes = max(0, (actual - scheduled).total_seconds() / 60)
        delay_penalty = min(delay_minutes * PENALTY_RATES['delay_per_minute'], PENALTY_RATES['delay_cap'])
        return delay_penalty
    except:
        return 0


def init_db():
    """Initialize the SQLite database with schema + sample data."""
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema_sqlite.sql')
    conn, cur = get_db()
    with open(schema_path, 'r') as f:
        cur.executescript(f.read())

    # Seed sample students if empty
    cur.execute("SELECT COUNT(*) as c FROM Students")
    count = cur.fetchone()
    n = count['c'] if isinstance(count, dict) else count[0]
    if n == 0:
        students = [
            ('Arjun Sharma',  'arjun@college.edu',  '9876543210', generate_password_hash('arjun123')),
            ('Priya Mehta',   'priya@college.edu',  '9876543211', generate_password_hash('priya123')),
            ('Rohan Gupta',   'rohan@college.edu',  '9876543212', generate_password_hash('rohan123')),
            ('Sneha Verma',   'sneha@college.edu',  '9876543213', generate_password_hash('sneha123')),
            ('Vikram Singh',  'vikram@college.edu', '9876543214', generate_password_hash('vikram123')),
        ]
        cur.executemany(
            "INSERT INTO Students (name,email,phone,password) VALUES (?,?,?,?)",
            students
        )
        # Seed rides
        now = datetime.now()
        rides = [
            (1, 'Main Gate', 'Railway Station', (now+timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'), 3, 3, 50.0,  'Open'),
            (2, 'Hostel A',  'City Mall',        (now+timedelta(hours=3)).strftime('%Y-%m-%d %H:%M'), 2, 2, 30.0,  'Open'),
            (3, 'Library',   'Airport',          (now+timedelta(hours=5)).strftime('%Y-%m-%d %H:%M'), 4, 4, 120.0, 'Open'),
            (4, 'Canteen',   'Bus Stand',        (now+timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'), 3, 3, 20.0,  'Open'),
            (5, 'Gate 2',    'Metro Station',    (now+timedelta(hours=4)).strftime('%Y-%m-%d %H:%M'), 2, 2, 40.0,  'Open'),
        ]
        cur.executemany(
            "INSERT INTO Rides (driver_id,source,destination,ride_time,total_seats,available_seats,price_per_seat,status) VALUES (?,?,?,?,?,?,?,?)",
            rides
        )
        conn.commit()
    conn.close()


# ── Auth Decorator ────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ── Page Routes ───────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('dashboard.html', user=session.get('user_name'))

@app.route('/post-ride')
@login_required
def post_ride_page():
    return render_template('post_ride.html', user=session.get('user_name'))

@app.route('/search')
@login_required
def search_page():
    return render_template('search.html', user=session.get('user_name'))

@app.route('/my-bookings')
@login_required
def my_bookings_page():
    return render_template('my_bookings.html', user=session.get('user_name'))

@app.route('/driver-requests')
@login_required
def driver_requests_page():
    return render_template('driver_requests.html', user=session.get('user_name'))

@app.route('/history')
@login_required
def history_page():
    return render_template('history.html', user=session.get('user_name'))

@app.route('/penalties')
@login_required
def penalties_page():
    return render_template('penalties.html', user=session.get('user_name'))


# ── Auth API ──────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    name, email, phone = data.get('name'), data.get('email'), data.get('phone')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({'error': 'Name, email and password are required'}), 400

    hashed = generate_password_hash(password)
    conn, cur = get_db()
    try:
        ph = '?' if not USE_MYSQL else '%s'
        cur.execute(
            f"INSERT INTO Students (name,email,phone,password) VALUES ({ph},{ph},{ph},{ph})",
            (name, email, phone, hashed)
        )
        conn.commit()
        return jsonify({'message': 'Registered successfully'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Email already registered'}), 409
    finally:
        conn.close()


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email, password = data.get('email'), data.get('password')

    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    cur.execute(f"SELECT * FROM Students WHERE email={ph}", (email,))
    user = row_to_dict(cur.fetchone())
    conn.close()

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id']   = user['student_id']
    session['user_name'] = user['name']
    return jsonify({'message': 'Login successful', 'name': user['name']})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out'})


@app.route('/api/me')
@login_required
def api_me():
    return jsonify({'user_id': session['user_id'], 'name': session['user_name']})


# ── Rides API ─────────────────────────────────────────────────
@app.route('/api/rides', methods=['GET'])
@login_required
def api_get_rides():
    """Search available rides with filters."""
    source      = request.args.get('source', '')
    destination = request.args.get('dest', '')
    min_price   = request.args.get('min_price', 0, type=float)
    max_price   = request.args.get('max_price', 9999, type=float)
    min_seats   = request.args.get('min_seats', 1, type=int)
    sort_by     = request.args.get('sort', 'ride_time')  # ride_time | price | available_seats
    date_filter = request.args.get('date', '')

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ph = '?' if not USE_MYSQL else '%s'

    query = f"""
        SELECT r.ride_id, r.source, r.destination, r.ride_time,
               r.total_seats, r.available_seats, r.price_per_seat, r.status,
               s.name AS driver_name, s.phone AS driver_phone
        FROM Rides r
        JOIN Students s ON r.driver_id = s.student_id
        WHERE r.status = 'Open'
          AND r.available_seats >= {ph}
          AND r.ride_time > {ph}
          AND r.price_per_seat BETWEEN {ph} AND {ph}
          AND r.driver_id != {ph}
    """
    params = [min_seats, now_str, min_price, max_price, session['user_id']]

    if source:
        query += f" AND LOWER(r.source) LIKE {ph}"
        params.append(f'%{source.lower()}%')
    if destination:
        query += f" AND LOWER(r.destination) LIKE {ph}"
        params.append(f'%{destination.lower()}%')
    if date_filter:
        query += f" AND DATE(r.ride_time) = {ph}"
        params.append(date_filter)

    # Sorting
    sort_map = {
        'ride_time':       'r.ride_time ASC',
        'price':           'r.price_per_seat ASC',
        'available_seats': 'r.available_seats DESC',
    }
    query += f" ORDER BY {sort_map.get(sort_by, 'r.ride_time ASC')}"

    conn, cur = get_db()
    cur.execute(query, params)
    rides = rows_to_list(cur.fetchall())
    conn.close()

    # Convert datetime to string for JSON
    for ride in rides:
        if isinstance(ride.get('ride_time'), datetime):
            ride['ride_time'] = ride['ride_time'].strftime('%Y-%m-%d %H:%M')

    return jsonify(rides)


@app.route('/api/rides', methods=['POST'])
@login_required
def api_post_ride():
    data = request.get_json()
    source      = data.get('source')
    destination = data.get('destination')
    ride_time   = data.get('ride_time')
    total_seats = int(data.get('total_seats', 1))
    price       = float(data.get('price_per_seat', 0))

    if not all([source, destination, ride_time]):
        return jsonify({'error': 'All fields required'}), 400

    # Ensure future ride
    if datetime.strptime(ride_time, '%Y-%m-%dT%H:%M') <= datetime.now():
        return jsonify({'error': 'Ride time must be in the future'}), 400

    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    cur.execute(
        f"INSERT INTO Rides (driver_id,source,destination,ride_time,total_seats,available_seats,price_per_seat) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})",
        (session['user_id'], source, destination, ride_time, total_seats, total_seats, price)
    )
    conn.commit()
    ride_id = cur.lastrowid
    conn.close()
    return jsonify({'message': 'Ride posted', 'ride_id': ride_id}), 201


@app.route('/api/rides/<int:ride_id>', methods=['DELETE'])
@login_required
def api_cancel_ride(ride_id):
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    cur.execute(f"SELECT * FROM Rides WHERE ride_id={ph}", (ride_id,))
    ride = row_to_dict(cur.fetchone())

    if not ride:
        conn.close()
        return jsonify({'error': 'Ride not found'}), 404
    if ride['driver_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Not your ride'}), 403

    # Get all accepted riders for this ride and apply driver cancellation penalty
    cur.execute(f"""
        SELECT request_id, rider_id FROM Requests 
        WHERE ride_id={ph} AND status='Accepted'
    """, (ride_id,))
    accepted_requests = rows_to_list(cur.fetchall())
    
    for req in accepted_requests:
        apply_penalty(conn, cur, req['rider_id'], req['request_id'], 
                     'Driver-Cancellation', 
                     PENALTY_RATES['cancellation_driver'],
                     "Driver cancelled the ride")
        # Update request status
        cur.execute(f"UPDATE Requests SET status='Cancelled', completion_status='Driver-Cancelled' WHERE request_id={ph}", 
                   (req['request_id'],))

    cur.execute(f"UPDATE Rides SET status='Cancelled' WHERE ride_id={ph}", (ride_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Ride cancelled', 'penalty_applied_to': len(accepted_requests), 'penalty_amount': PENALTY_RATES['cancellation_driver']})


# ── Requests API ──────────────────────────────────────────────
@app.route('/api/requests', methods=['POST'])
@login_required
def api_request_ride():
    data    = request.get_json()
    ride_id = int(data.get('ride_id'))
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'

    # Fetch ride
    cur.execute(f"SELECT * FROM Rides WHERE ride_id={ph}", (ride_id,))
    ride = row_to_dict(cur.fetchone())
    if not ride:
        conn.close(); return jsonify({'error': 'Ride not found'}), 404

    # Constraint: driver != rider
    if ride['driver_id'] == session['user_id']:
        conn.close(); return jsonify({'error': 'You cannot book your own ride'}), 400

    # Constraint: no overbooking
    if ride['available_seats'] <= 0:
        conn.close(); return jsonify({'error': 'No seats available'}), 400

    if ride['status'] != 'Open':
        conn.close(); return jsonify({'error': 'Ride not available'}), 400

    try:
        cur.execute(
            f"INSERT INTO Requests (ride_id,rider_id) VALUES ({ph},{ph})",
            (ride_id, session['user_id'])
        )
        conn.commit()
        req_id = cur.lastrowid

        # Auto-create pending payment
        amount = ride['price_per_seat']
        cur.execute(
            f"INSERT INTO Payments (request_id,amount) VALUES ({ph},{ph})",
            (req_id, amount)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Request sent', 'request_id': req_id}), 201
    except Exception:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Already requested this ride'}), 409


@app.route('/api/requests/<int:req_id>', methods=['PATCH'])
@login_required
def api_handle_request(req_id):
    """Driver accepts/rejects a request."""
    data   = request.get_json()
    status = data.get('status')  # 'Accepted' or 'Rejected'

    if status not in ('Accepted', 'Rejected'):
        return jsonify({'error': 'Invalid status'}), 400

    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'

    # Verify ownership
    cur.execute(f"""
        SELECT rq.*, r.driver_id, r.available_seats
        FROM Requests rq
        JOIN Rides r ON rq.ride_id = r.ride_id
        WHERE rq.request_id = {ph}
    """, (req_id,))
    req = row_to_dict(cur.fetchone())

    if not req:
        conn.close(); return jsonify({'error': 'Request not found'}), 404
    if req['driver_id'] != session['user_id']:
        conn.close(); return jsonify({'error': 'Not authorized'}), 403
    if req['status'] != 'Pending':
        conn.close(); return jsonify({'error': 'Request already handled'}), 400

    # Check seats if accepting
    if status == 'Accepted' and req['available_seats'] <= 0:
        conn.close(); return jsonify({'error': 'No seats available'}), 400

    cur.execute(f"UPDATE Requests SET status={ph} WHERE request_id={ph}", (status, req_id))

    # SQLite: manually update seats (MySQL uses trigger)
    if not USE_MYSQL and status == 'Accepted':
        cur.execute(f"UPDATE Rides SET available_seats = available_seats - 1 WHERE ride_id={ph}",
                    (req['ride_id'],))
        cur.execute(f"UPDATE Rides SET status='Full' WHERE ride_id={ph} AND available_seats=0",
                    (req['ride_id'],))

    # Update payment status
    if status == 'Accepted':
        cur.execute(f"""
            UPDATE Payments SET status='Paid', paid_at=datetime('now')
            WHERE request_id={ph}
        """, (req_id,))

    conn.commit()
    conn.close()
    return jsonify({'message': f'Request {status}'})


@app.route('/api/requests/<int:req_id>/cancel', methods=['PATCH'])
@login_required
def api_cancel_request(req_id):
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'

    cur.execute(f"""
        SELECT rq.*, r.driver_id
        FROM Requests rq
        JOIN Rides r ON rq.ride_id = r.ride_id
        WHERE rq.request_id={ph} AND rq.rider_id={ph}
    """, (req_id, session['user_id']))
    req = row_to_dict(cur.fetchone())

    if not req:
        conn.close(); return jsonify({'error': 'Request not found'}), 404

    # Apply rider cancellation penalty if ride was accepted
    if req['status'] == 'Accepted':
        apply_penalty(conn, cur, session['user_id'], req_id, 
                     'Cancellation', 
                     PENALTY_RATES['cancellation_rider'],
                     "Rider cancelled booking")

    cur.execute(f"UPDATE Requests SET status='Cancelled', completion_status='Cancelled' WHERE request_id={ph}", (req_id,))

    if not USE_MYSQL and req['status'] == 'Accepted':
        cur.execute(f"UPDATE Rides SET available_seats=available_seats+1, status='Open' WHERE ride_id={ph}",
                    (req['ride_id'],))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Booking cancelled', 'penalty_applied': req['status'] == 'Accepted', 'penalty_amount': PENALTY_RATES['cancellation_rider'] if req['status'] == 'Accepted' else 0})


# ── My Bookings & History ─────────────────────────────────────
@app.route('/api/my-bookings')
@login_required
def api_my_bookings():
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    cur.execute(f"""
        SELECT rq.request_id, rq.status as req_status,
               r.ride_id, r.source, r.destination, r.ride_time,
               r.price_per_seat,
               s.name AS driver_name, s.phone AS driver_phone,
               p.status AS payment_status, p.amount
        FROM Requests rq
        JOIN Rides r    ON rq.ride_id   = r.ride_id
        JOIN Students s ON r.driver_id  = s.student_id
        LEFT JOIN Payments p ON p.request_id = rq.request_id
        WHERE rq.rider_id = {ph}
        ORDER BY r.ride_time DESC
    """, (session['user_id'],))
    bookings = rows_to_list(cur.fetchall())
    conn.close()
    return jsonify(bookings)


@app.route('/api/driver-requests')
@login_required
def api_driver_requests():
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    cur.execute(f"""
        SELECT rq.request_id, rq.status AS req_status, rq.created_at,
               r.ride_id, r.source, r.destination, r.ride_time, r.price_per_seat,
               s.name AS rider_name, s.phone AS rider_phone
        FROM Requests rq
        JOIN Rides r    ON rq.ride_id  = r.ride_id
        JOIN Students s ON rq.rider_id = s.student_id
        WHERE r.driver_id = {ph}
        ORDER BY rq.created_at DESC
    """, (session['user_id'],))
    reqs = rows_to_list(cur.fetchall())
    conn.close()
    return jsonify(reqs)


# ── Ride Completion & Penalties ───────────────────────────────
@app.route('/api/rides/<int:ride_id>/complete', methods=['PATCH'])
@login_required
def api_complete_ride(ride_id):
    """Mark ride as completed with actual arrival time. Driver submits this."""
    data = request.get_json()
    actual_arrival_time = data.get('actual_arrival_time')  # ISO format: '2024-04-20T15:30:00'

    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    
    cur.execute(f"SELECT * FROM Rides WHERE ride_id={ph}", (ride_id,))
    ride = row_to_dict(cur.fetchone())
    
    if not ride:
        conn.close()
        return jsonify({'error': 'Ride not found'}), 404
    
    if ride['driver_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403
    
    # Get all accepted requests for this ride
    cur.execute(f"""
        SELECT request_id, rider_id FROM Requests 
        WHERE ride_id={ph} AND status='Accepted'
    """, (ride_id,))
    accepted_requests = rows_to_list(cur.fetchall())
    
    penalties_applied = []
    
    try:
        actual_time = datetime.fromisoformat(actual_arrival_time.replace('Z', '+00:00')) if 'T' in actual_arrival_time else datetime.strptime(actual_arrival_time, '%Y-%m-%d %H:%M:%S')
    except:
        actual_time = datetime.now()
    
    scheduled_time = datetime.fromisoformat(ride['ride_time'].replace('Z', '+00:00')) if isinstance(ride['ride_time'], str) and 'T' in ride['ride_time'] else datetime.strptime(ride['ride_time'], '%Y-%m-%d %H:%M:%S') if isinstance(ride['ride_time'], str) else ride['ride_time']
    
    # Check for delays
    delay_minutes = max(0, (actual_time - scheduled_time).total_seconds() / 60)
    
    for req in accepted_requests:
        if delay_minutes > 5:  # Only penalize if more than 5 minutes late
            delay_penalty = calculate_delay_penalty(scheduled_time, actual_time)
            if delay_penalty > 0:
                apply_penalty(conn, cur, req['rider_id'], req['request_id'],
                            'Delay', delay_penalty,
                            f"Ride was {int(delay_minutes)} minutes late")
                penalties_applied.append({'request_id': req['request_id'], 'penalty': 'Delay', 'amount': delay_penalty})
        
        # Update request status
        completion_status = 'On-Time' if delay_minutes <= 5 else 'Late'
        cur.execute(f"""
            UPDATE Requests 
            SET status='Completed', actual_arrival_time={ph}, completion_status={ph}
            WHERE request_id={ph}
        """, (actual_arrival_time, completion_status, req['request_id']))
    
    # Update ride status
    cur.execute(f"UPDATE Rides SET status='Completed' WHERE ride_id={ph}", (ride_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Ride completed',
        'penalty_count': len(penalties_applied),
        'penalties': penalties_applied
    })


@app.route('/api/requests/<int:req_id>/mark-missed', methods=['PATCH'])
@login_required
def api_mark_missed(req_id):
    """Mark a rider as missed (no-show). Only driver can do this."""
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    
    cur.execute(f"""
        SELECT rq.*, r.driver_id, r.ride_id
        FROM Requests rq
        JOIN Rides r ON rq.ride_id = r.ride_id
        WHERE rq.request_id={ph}
    """, (req_id,))
    req = row_to_dict(cur.fetchone())
    
    if not req:
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    if req['driver_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403
    
    if req['status'] != 'Accepted':
        conn.close()
        return jsonify({'error': 'Request is not accepted'}), 400
    
    # Apply missed ride penalty to rider
    apply_penalty(conn, cur, req['rider_id'], req_id,
                 'Missed-Ride', PENALTY_RATES['missed_ride'],
                 "Rider did not show up for the ride")
    
    # Update request status
    cur.execute(f"""
        UPDATE Requests 
        SET status='No-Show', completion_status='Missed'
        WHERE request_id={ph}
    """, (req_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Marked as no-show',
        'penalty_applied': True,
        'penalty_amount': PENALTY_RATES['missed_ride']
    })


@app.route('/api/penalties')
@login_required
def api_get_penalties():
    """Get all penalties for the current user."""
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    
    cur.execute(f"""
        SELECT p.penalty_id, p.penalty_type, p.amount, p.reason, p.applied_at,
               r.ride_id, r.source, r.destination, r.ride_time
        FROM Penalties p
        JOIN Requests rq ON p.request_id = rq.request_id
        JOIN Rides r ON rq.ride_id = r.ride_id
        WHERE p.student_id={ph}
        ORDER BY p.applied_at DESC
    """, (session['user_id'],))
    
    penalties = rows_to_list(cur.fetchall())
    
    # Calculate total penalty amount
    cur.execute(f"SELECT COALESCE(SUM(amount), 0) AS total FROM Penalties WHERE student_id={ph}", (session['user_id'],))
    total_penalty = (row_to_dict(cur.fetchone()) or {}).get('total', 0)
    
    conn.close()
    
    return jsonify({
        'penalties': penalties,
        'total_penalty': float(total_penalty),
        'count': len(penalties)
    })


@app.route('/api/user/rating')
@login_required
def api_get_rating():
    """Get user reliability rating based on penalties and ride history."""
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    
    # Count completed rides
    cur.execute(f"""
        SELECT COUNT(*) AS completed FROM Requests 
        WHERE rider_id={ph} AND completion_status='On-Time'
    """, (session['user_id'],))
    on_time_rides = (row_to_dict(cur.fetchone()) or {}).get('completed', 0)
    
    # Count missed rides
    cur.execute(f"""
        SELECT COUNT(*) AS missed FROM Requests 
        WHERE rider_id={ph} AND completion_status='Missed'
    """, (session['user_id'],))
    missed_rides = (row_to_dict(cur.fetchone()) or {}).get('missed', 0)
    
    # Count cancelled rides
    cur.execute(f"""
        SELECT COUNT(*) AS cancelled FROM Requests 
        WHERE rider_id={ph} AND completion_status='Cancelled'
    """, (session['user_id'],))
    cancelled_rides = (row_to_dict(cur.fetchone()) or {}).get('cancelled', 0)
    
    # Get total penalties
    cur.execute(f"SELECT COALESCE(SUM(amount), 0) AS total FROM Penalties WHERE student_id={ph}", (session['user_id'],))
    total_penalties = (row_to_dict(cur.fetchone()) or {}).get('total', 0)
    
    total_rides = on_time_rides + missed_rides + cancelled_rides
    
    # Calculate reliability score (0-100)
    if total_rides > 0:
        reliability_score = max(0, 100 - (missed_rides * 20 + cancelled_rides * 10))
    else:
        reliability_score = 100
    
    conn.close()
    
    return jsonify({
        'reliability_score': float(reliability_score),
        'on_time_rides': on_time_rides,
        'missed_rides': missed_rides,
        'cancelled_rides': cancelled_rides,
        'total_penalties': float(total_penalties),
        'total_rides': total_rides
    })


@app.route('/api/my-rides')
@login_required
def api_my_rides():
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    cur.execute(f"""
        SELECT * FROM Rides WHERE driver_id={ph} ORDER BY ride_time DESC
    """, (session['user_id'],))
    rides = rows_to_list(cur.fetchall())
    conn.close()
    return jsonify(rides)


@app.route('/api/history')
@login_required
def api_history():
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    uid = session['user_id']

    # Rides as driver
    cur.execute(f"""
        SELECT 'driver' AS role, r.source, r.destination, r.ride_time,
               r.price_per_seat, r.status, r.total_seats,
               COUNT(rq.request_id) AS accepted_riders
        FROM Rides r
        LEFT JOIN Requests rq ON r.ride_id=rq.ride_id AND rq.status='Accepted'
        WHERE r.driver_id={ph}
        GROUP BY r.ride_id
        ORDER BY r.ride_time DESC
    """, (uid,))
    as_driver = rows_to_list(cur.fetchall())

    # Rides as rider
    cur.execute(f"""
        SELECT 'rider' AS role, r.source, r.destination, r.ride_time,
               r.price_per_seat, rq.status, s.name AS driver_name,
               p.amount, p.status AS payment_status
        FROM Requests rq
        JOIN Rides r    ON rq.ride_id  = r.ride_id
        JOIN Students s ON r.driver_id = s.student_id
        LEFT JOIN Payments p ON p.request_id = rq.request_id
        WHERE rq.rider_id={ph}
        ORDER BY r.ride_time DESC
    """, (uid,))
    as_rider = rows_to_list(cur.fetchall())

    conn.close()
    return jsonify({'as_driver': as_driver, 'as_rider': as_rider})


# ── Stats for dashboard ───────────────────────────────────────
@app.route('/api/stats')
@login_required
def api_stats():
    conn, cur = get_db()
    ph = '?' if not USE_MYSQL else '%s'
    uid = session['user_id']

    cur.execute(f"SELECT COUNT(*) AS c FROM Rides WHERE driver_id={ph}", (uid,))
    rides_posted = (row_to_dict(cur.fetchone()) or {}).get('c', 0)

    cur.execute(f"SELECT COUNT(*) AS c FROM Requests WHERE rider_id={ph} AND status='Accepted'", (uid,))
    rides_booked = (row_to_dict(cur.fetchone()) or {}).get('c', 0)

    cur.execute(f"SELECT COALESCE(SUM(p.amount),0) AS total FROM Payments p JOIN Requests rq ON p.request_id=rq.request_id WHERE rq.rider_id={ph} AND p.status='Paid'", (uid,))
    total_spent = (row_to_dict(cur.fetchone()) or {}).get('total', 0)

    cur.execute(f"SELECT COUNT(*) AS c FROM Requests rq JOIN Rides r ON rq.ride_id=r.ride_id WHERE r.driver_id={ph} AND rq.status='Pending'", (uid,))
    pending_reqs = (row_to_dict(cur.fetchone()) or {}).get('c', 0)
    
    # Get total penalties
    cur.execute(f"SELECT COALESCE(SUM(amount),0) AS total FROM Penalties WHERE student_id={ph}", (uid,))
    total_penalties = (row_to_dict(cur.fetchone()) or {}).get('total', 0)

    conn.close()
    return jsonify({
        'rides_posted': rides_posted,
        'rides_booked': rides_booked,
        'total_spent':  float(total_spent),
        'pending_reqs': pending_reqs,
        'total_penalties': float(total_penalties),
    })


# ── Entry Point ───────────────────────────────────────────────
if __name__ == '__main__':
    if not USE_MYSQL:
        init_db()
    app.run(debug=True, port=5000)
