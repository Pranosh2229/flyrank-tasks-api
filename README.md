# Tasks API

A tiny CRUD API for managing a to-do list. FlyRank Backend Engineering Internship — Assignment A1 (in-memory), extended in Assignment A2 with a SQLite-backed storage layer.

## Run it

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Endpoints

| Method | Path          | Behaviour                                  |
|--------|---------------|---------------------------------------------|
| GET    | `/tasks`      | List all tasks                              |
| GET    | `/tasks/{id}` | Get one task, `404` if it doesn't exist     |
| POST   | `/tasks`      | Create a task, `400` if `title` is missing  |
| PUT    | `/tasks/{id}` | Update a task, `404`/`400` as above         |
| DELETE | `/tasks/{id}` | Delete a task, `404` if it doesn't exist    |

## Database

Data lives in `tasks.db`, a SQLite database file created automatically next to `main.py` the first time the app runs. Restarting the server no longer wipes your tasks.

**Why SQLite:** no separate database server to install or run — the whole database is one file. That's exactly right for a small task API: zero setup, and the file itself is the backup. If this grew into a multi-service production app, the same SQL would move to Postgres with minimal code change (that separation between API and storage is the point of this assignment).

**Where the file lives:** `tasks.db`, next to `main.py`. It's git-ignored, so a fresh clone starts with no database file — running `uvicorn main:app --reload` once creates it and seeds three example tasks (`Buy milk`, `Write README`, `Push to GitHub`). Restarting again does not duplicate them; the seed only runs when the table is empty.

## SQL explored by hand (Stage 4)

Ran directly against `tasks.db` with the server live, no restart, and confirmed through the running API:

```sql
UPDATE tasks SET done = 1 WHERE id = 2;
```

Before: `GET /tasks/2` → `{"id":2,"title":"Write README","done":false}`
Ran that `UPDATE` directly against the database file (same thing DB Browser does).
After, same running server, no restart: `GET /tasks/2` → `{"id":2,"title":"Write README","done":true}` — the API reflected the change instantly, because it and the database viewer read the exact same file.

**Still needed from me:** open `tasks.db` in [DB Browser for SQLite](https://sqlitebrowser.org/), run the query above (or any of the Stage 4 queries) there instead, and drop a screenshot here — the assignment specifically wants the GUI viewer, not just this log.

`![DB Browser screenshot](TODO-add-screenshot.png)`
