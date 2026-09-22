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

Storage is currently in-memory — restarting the server resets the task list back to the three seeded examples. See Assignment A2 for the SQLite-backed version.
