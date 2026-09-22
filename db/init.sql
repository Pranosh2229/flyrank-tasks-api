-- Runs once, automatically, the first time the Postgres container starts
-- with an empty data volume (Postgres's own docker-entrypoint-initdb.d
-- mechanism — this file is never re-run against an existing volume).

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO tasks (title, done)
SELECT * FROM (VALUES
    ('Buy milk', FALSE),
    ('Write README', FALSE),
    ('Push to GitHub', FALSE)
) AS seed(title, done)
WHERE NOT EXISTS (SELECT 1 FROM tasks);
