# 🚗 NextRide — College Ride Sharing System
### B.Tech DBMS Mini Project

---

## 📁 Project Structure

```
nextride/
├── backend/
│   └── app.py              ← Flask backend (all APIs)
├── templates/
│   ├── base.html            ← Shared navbar + sidebar layout
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── post_ride.html
│   ├── search.html          ← Main search page with filters + map
│   ├── my_bookings.html
│   ├── driver_requests.html
│   └── history.html
├── static/
│   ├── css/style.css        ← Complete design system
│   └── js/main.js           ← Utilities (API, Toast, Format)
├── database/
│   ├── schema_mysql.sql     ← MySQL schema + triggers + sample data
│   └── schema_sqlite.sql    ← SQLite fallback schema
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start (SQLite — No MySQL needed)

```bash
# 1. Install dependencies
pip install flask werkzeug

# 2. Run the server
cd backend
python app.py

# 3. Open browser
http://localhost:5000
```

## 🗄️ With MySQL

```bash
# 1. Create database
mysql -u root -p < database/schema_mysql.sql

# 2. Edit backend/app.py
USE_MYSQL = True
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',
    'database': 'nextride',
}

# 3. Install MySQL connector
pip install mysql-connector-python flask werkzeug

# 4. Run
python backend/app.py
```

---

## 🔑 Demo Accounts

| Email | Password |
|-------|----------|
| arjun@college.edu | arjun123 |
| priya@college.edu | priya123 |
| rohan@college.edu | rohan123 |
| sneha@college.edu | sneha123 |
| vikram@college.edu | vikram123 |

---

## 🧱 Database Schema (Normalized to BCNF)

### Students
| Column | Type | Constraint |
|--------|------|-----------|
| student_id | INT | PK, AUTO_INCREMENT |
| name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(150) | UNIQUE, NOT NULL |
| phone | VARCHAR(15) | |
| password | VARCHAR(255) | NOT NULL (hashed) |

### Rides
| Column | Type | Constraint |
|--------|------|-----------|
| ride_id | INT | PK |
| driver_id | INT | FK → Students |
| source | VARCHAR(150) | NOT NULL |
| destination | VARCHAR(150) | NOT NULL |
| ride_time | DATETIME | NOT NULL |
| total_seats | INT | CHECK > 0 |
| available_seats | INT | CHECK ≥ 0, ≤ total |
| price_per_seat | DECIMAL(8,2) | CHECK ≥ 0 |
| status | ENUM | Open/Full/Cancelled/Completed |

### Requests
| Column | Type | Constraint |
|--------|------|-----------|
| request_id | INT | PK |
| ride_id | INT | FK → Rides |
| rider_id | INT | FK → Students |
| status | ENUM | Pending/Accepted/Rejected/Cancelled |
| UNIQUE | (ride_id, rider_id) | No duplicate booking |

### Payments
| Column | Type | Constraint |
|--------|------|-----------|
| payment_id | INT | PK |
| request_id | INT | FK → Requests, UNIQUE |
| amount | DECIMAL(8,2) | |
| status | ENUM | Pending/Paid/Refunded |

---

## ⚙️ Key DBMS Features Demonstrated

1. **Normalization** — BCNF (no transitive dependencies)
2. **Foreign Keys** — Referential integrity across all tables
3. **UNIQUE constraints** — No duplicate bookings `(ride_id, rider_id)`
4. **CHECK constraints** — `available_seats ≥ 0`, `price ≥ 0`
5. **Triggers** (MySQL) — Auto-decrement seats on acceptance
6. **JOIN queries** — Multi-table SELECTs with aliases
7. **Aggregate functions** — COUNT, SUM for stats
8. **Subqueries** — Nested in filters
9. **Transaction management** — commit/rollback on errors

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/register | Register student |
| POST | /api/login | Login |
| POST | /api/logout | Logout |
| GET | /api/rides | Search available rides (with filters) |
| POST | /api/rides | Post a new ride |
| DELETE | /api/rides/:id | Cancel a ride |
| POST | /api/requests | Request a ride |
| PATCH | /api/requests/:id | Accept/Reject request |
| PATCH | /api/requests/:id/cancel | Cancel booking |
| GET | /api/my-bookings | My ride bookings |
| GET | /api/driver-requests | Requests for my rides |
| GET | /api/my-rides | My posted rides |
| GET | /api/history | Full ride history |
| GET | /api/stats | Dashboard statistics |
