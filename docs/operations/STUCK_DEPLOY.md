# Runbook: Render deploy never finishes (no error)

**Symptom:** a deploy sits at "In progress" / "Deploying" for many minutes. The build step
(`pip install`) succeeded, the *previous* instance keeps answering `/api/health`, and nothing in
the logs says why. Eventually the deploy is cancelled or times out.

**Most likely cause:** the start command is `alembic upgrade head && uvicorn ...`. If a migration
needs a table lock (any `ALTER TABLE`, e.g. changing a column type) and *another database session
is holding a conflicting lock*, PostgreSQL waits **forever** and prints nothing. The new instance
never reaches `uvicorn`, so it never opens its port, so Render never marks it healthy.

Who typically holds the lock:

- a session left **idle in transaction** (a leaked connection from the running app),
- a long-running job connected to the database (e.g. the sleeve-fetch GitHub workflow),
- the stuck `ALTER TABLE` of an **earlier, cancelled deploy** that Postgres hasn't cleaned up yet.

While the migration waits, new queries on the same table queue up behind it, so the live site can
also start to hang on those tables.

## 1. Confirm it (2 minutes)

Open the database shell (Render dashboard → the Postgres instance → **Connect** → *PSQL command*)
and run:

```sql
-- Everything connected to this database, oldest transaction first
SELECT pid,
       state,
       wait_event_type,
       now() - xact_start  AS xact_age,
       now() - query_start AS query_age,
       application_name,
       left(query, 90)     AS query
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
ORDER BY xact_start NULLS LAST;
```

What to look for:

| You see | Meaning |
|---|---|
| a row whose `query` starts `ALTER TABLE` and `wait_event_type = Lock` | the migration is **waiting** for a lock — confirmed |
| rows with `state = idle in transaction` and a large `xact_age` | those sessions are the likely **blockers** |

To see exactly who blocks the migration:

```sql
SELECT a.pid AS waiting_pid,
       left(a.query, 60) AS waiting_query,
       pg_blocking_pids(a.pid) AS blocked_by
FROM pg_stat_activity a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0;
```

## 2. Unblock it

Terminate the **blocker** (the pid(s) in `blocked_by`), *not* your own session:

```sql
SELECT pg_terminate_backend(<blocking_pid>);
```

If the only thing waiting is a leftover `ALTER TABLE` from a cancelled deploy, terminate that pid
instead. Then trigger a fresh deploy (**Manual Deploy → Deploy latest commit**). Terminating an
idle-in-transaction session is safe: SQLAlchemy reconnects on the next request (`pool_pre_ping`).

## 3. Prevent it (already built in)

- Migrations run with a **`lock_timeout`** (default 30 s, `MIGRATION_LOCK_TIMEOUT_SECONDS`). A
  blocked migration now **fails fast with a clear error** (`canceling statement due to lock
  timeout`) in the deploy log instead of hanging, and the previous instance stays live.
- The app and the migration set `application_name` (`mana-meeples-api`, `alembic-migration`) so
  they are easy to spot in `pg_stat_activity`.
- App connections set `idle_in_transaction_session_timeout` (default 60 s,
  `DB_IDLE_IN_TX_TIMEOUT_SECONDS`) so a leaked, idle transaction is closed by the database instead
  of blocking migrations indefinitely, and `lock_timeout` (default 10 s,
  `DB_LOCK_TIMEOUT_SECONDS`) so requests fail fast rather than pile up behind a waiting `ALTER`.
- Cache warming at startup is time-boxed and can no longer delay the server opening its port.

## Other things that make a deploy look stuck

| Check | Where |
|---|---|
| A *newer* commit cancelled the in-flight deploy (`Deploy cancelled` in the log) | Render → Events. Not an error — wait for the newest deploy. |
| The log you are reading is the **old** instance's runtime log | Open the specific deploy (Events → the deploy) and read *its* log, not the service's live log. |
| Build step itself | `pip install` takes ~1–3 min; verify it completed ("Build successful"). |
| A persistent disk is attached | See below. |

## A different cause: a persistent disk blocks the new instance from ever starting

If the service has a disk (`disk:` in `render.yaml`, or a volume shown on the service page),
Render **cannot** run the old and new instances at the same time — only one instance can have the
disk mounted. So a disk forces a non-zero-downtime deploy: Render has to stop the old instance and
detach the disk before the new instance can even start its container.

This looks different from the migration-lock case above: the build finishes ("Build successful"),
and then there is **no further log output at all** — not even the start command's first line
(`alembic upgrade head`, `Uvicorn running`, `No open ports detected`). That is because the new
instance's container hasn't started yet; it isn't waiting on a database lock, it's waiting on the
disk. Meanwhile the old instance keeps answering `/api/health`, exactly as if nothing were wrong,
for as long as Render leaves it running — this can be many minutes with no error at any layer.

**How to tell the difference**: search the deploy's logs for the start command actually running
(e.g. `alembic`, `Uvicorn running`). If it's a lock, you'll see `alembic upgrade head` begin and
then wait. If it's the disk, you'll see nothing after the build at all.

**Fix**: remove the disk if nothing on it is actually used (check what the app writes to the
mount path — e.g. `grep` the codebase for the mount path and the env var that points at it). If
the disk is genuinely needed, this is an inherent Render limitation for disked services: deploys
of that service will never be zero-downtime, and a slow/hung instance swap has to be handled
manually from the dashboard (cancel the deploy, or wait it out).
