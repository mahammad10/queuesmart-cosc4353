# QueueSmart — Assignment 3 (Back-End Development & API Implementation)

Smart queue management application. This repository contains the Flask REST API
built for A3 and the Assignment 2 front end wired up to consume it.

No database is used. All state lives in memory (`backend/app/store.py`) and is
reloaded from seed data whenever the server restarts, as A3 requires.
Persistence arrives in Assignment 4, and the store module is the only file that
will need to be replaced.

---

## Quick start

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python run.py
```

Then open <http://127.0.0.1:5000>. Flask serves the front end and the API from
the same origin, so there is nothing else to start.

**Demo accounts** (created automatically at start-up):

| Role  | Email                   | Password      | Admin key          |
|-------|-------------------------|---------------|--------------------|
| User  | user@queuesmart.com     | password123   | —                  |
| Admin | admin@queuesmart.com    | password123   | QUEUE-ADMIN-2026   |

## Running the tests

```bash
cd backend
python -m pytest                 # coverage report prints automatically
```

217 tests, **98% statement coverage** (A3 target: 70–80%). The HTML report is
written to `backend/htmlcov/index.html`.

---

## Project structure

```
backend/
  run.py                      entry point
  pytest.ini                  test + coverage configuration
  app/
    __init__.py               app factory, error handlers, CORS, static serving
    store.py                  in-memory data store (the future database seam)
    validators.py             shared validation rules + error types
    modules/                  business logic, one file per required A3 module
      auth_module.py            registration, login, hashing, roles, sessions
      service_module.py         service CRUD
      queue_module.py           join / leave / view / serve, ordering rules
      wait_time.py              wait-time estimation
      notification_module.py    notification triggers and log
      history_module.py         queue participation history
    routes/                   HTTP layer, one blueprint per module
  tests/                      pytest suite (217 tests)
frontend/                     Assignment 2 UI, now backed by the API
  api.js                      the only file that talks HTTP
  script.js                   page logic
```

The logic lives in `modules/`; the `routes/` files only parse requests and
return JSON. That split is what makes the business rules unit-testable without
spinning up a web server, and most of the test suite calls the modules directly.

---

## Required modules

### 1. Authentication
Registration, login, and role handling for **user** vs **administrator**.
Passwords are stored as salted SHA-256 digests (`salt$digest`) and are never
returned by any endpoint. A successful login issues a random session token; the
front end sends it back as `Authorization: Bearer <token>`. Registering or
logging in as an administrator additionally requires the shared admin key.

### 2. Service Management
Services carry a name, description, expected duration in minutes, and a
priority level. Administrators can create, update, open/close, and delete them.
Listing is public so the login-free landing pages still work.

### 3. Queue Management
Users join and leave; administrators view the queue, serve the next person,
remove an entry, or manually reorder. Ordering is:

```
sort key = (-priority_weight, arrival_sequence)      high=3, medium=2, low=1
```

Priority wins first; inside a priority level it is strictly first-come,
first-served, because `arrival_sequence` is a global counter that only ever
increases. A queue entry inherits its service's priority unless one is passed
explicitly on join.

### 4. Wait-time estimation
Rule-based, no algorithms:

```
estimated wait (minutes) = (position - 1) x expected duration x priority multiplier
```

Position 1 waits 0 minutes — that person is next. The multiplier is 0.8 for
high, 1.0 for medium, 1.2 for low, reflecting that staff fast-track priority
cases. `describe_wait()` turns the number into the label the UI shows
("You are next", "About 45 minutes", "About 1h 35m").

### 5. Notifications
Written to an in-memory log and returned to the front end — no email or SMS.
Triggers: joining a queue, reaching position 1 or 2 (`almost_up`), being
served, leaving, and being removed by an administrator. The `almost_up` warning
fires once per entry and only re-arms if the user drops back out of the
warning band.

### 6. History
One record per queue participation. It opens as `waiting` when the user joins
and closes as `served`, `left`, or `removed`, recording the real elapsed wait.
`/api/history` also returns a summary with total visits and average wait.

---

## API reference

Base URL: `/api`. All request and response bodies are JSON.
Endpoints marked 🔒 need a bearer token; 🛡 need the administrator role.

### Authentication
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create an account, returns user + token |
| POST | `/auth/login` | Sign in, returns user + token |
| POST | `/auth/logout` 🔒 | Invalidate the current token |
| GET  | `/auth/me` 🔒 | The signed-in user |

### Services
| Method | Path | Description |
|---|---|---|
| GET | `/services` | List services (`?open=true` filters to open ones) |
| GET | `/services/{id}` | One service |
| POST | `/services` 🛡 | Create |
| PUT | `/services/{id}` 🛡 | Update (partial payloads allowed) |
| PATCH | `/services/{id}/status` 🛡 | Open or close the queue |
| DELETE | `/services/{id}` 🛡 | Delete the service and its queue |

### Queue
| Method | Path | Description |
|---|---|---|
| POST | `/services/{id}/queue/join` 🔒 | Join, returns position and wait estimate |
| DELETE | `/services/{id}/queue/leave` 🔒 | Leave |
| GET | `/queue/status` 🔒 | Every queue the caller is currently in |
| GET | `/services/{id}/wait-time` | Estimate for someone joining right now |
| GET | `/services/{id}/queue` 🛡 | Full ordered queue |
| POST | `/services/{id}/queue/serve-next` 🛡 | Serve the front of the queue |
| DELETE | `/services/{id}/queue/{entryId}` 🛡 | Remove an entry |
| PATCH | `/services/{id}/queue/{entryId}/move` 🛡 | Manual reorder (`up` / `down`) |

### Notifications & history
| Method | Path | Description |
|---|---|---|
| GET | `/notifications` 🔒 | Newest first (`?unread=true`) |
| POST | `/notifications/read` 🔒 | Mark all as read |
| GET | `/history` 🔒 | The caller's history plus a summary |
| GET | `/history/service/{id}` 🛡 | Everyone who used a service |

### Example

```bash
curl -X POST http://127.0.0.1:5000/api/services/1/queue/join \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
```

```json
{"entry": {"entry_id": 1, "service_name": "Service 1", "position": 3,
           "priority": "medium", "estimated_wait_minutes": 30,
           "wait_label": "About 30 minutes"}}
```

---

## Validation

Every rule is enforced in `app/validators.py`, server-side, regardless of what
the browser does. Invalid input never reaches the business logic.

| Rule | Applies to | Failure |
|---|---|---|
| Required field present | all modules | 400 |
| Correct type | duration must be a whole number, `is_open` boolean | 400 |
| Length limits | names ≤ 50, service name ≤ 100, description ≤ 500, email ≤ 120 | 400 |
| Email format | registration, login, password reset | 400 |
| Password length | 8–128 characters | 400 |
| Allowed values | priority ∈ {low, medium, high}, role ∈ {user, admin} | 400 |
| Numeric range | duration 1–480 minutes | 400 |

Error responses are uniform, which is what lets the front end highlight the
offending field:

```json
{"error": "Validation failed", "field": "expected_duration",
 "message": "Expected duration must be at least 1."}
```

Status codes: `400` validation, `401` missing/expired token, `403` wrong role,
`404` unknown record, `409` state conflict (joining twice, serving an empty
queue, duplicate service name).

---

## Front-end integration

The A2 pages are unchanged visually — same HTML structure and the same
`style.css`. What changed is where the data comes from. Previously every screen
read and wrote `localStorage`; now `api.js` is the single place that talks HTTP,
and `script.js` renders whatever the API returns.

| Page | Endpoints it calls |
|---|---|
| index / adminLogin | `POST /auth/login`, `POST /auth/register` |
| dashboard | `GET /queue/status`, `GET /services?open=true`, `GET /notifications` |
| joinQueue | `GET /services?open=true`, `GET /services/{id}/wait-time`, `POST .../join` |
| queueStatus | `GET /queue/status`, `DELETE .../leave` |
| history | `GET /history` |
| adminDashboard | `GET /services`, `PATCH /services/{id}/status` |
| serviceManagement | `GET/POST/PUT/DELETE /services` |
| queueManagement | `GET .../queue`, `POST .../serve-next`, `DELETE .../{entryId}`, `PATCH .../move` |

`localStorage` now holds only the session token and the cached user record.
Positions, wait times, notifications, and history are computed by the backend.
All user-supplied text is escaped before it is inserted into the DOM.

---

## Known limits (by design for A3)

- Data is lost on restart — no database until A4.
- Session tokens live in memory and have no expiry timestamp.
- SHA-256 with a per-user salt is used for hashing; a production build would use
  bcrypt or Argon2.
- The admin key is a module-level constant rather than an environment variable.
