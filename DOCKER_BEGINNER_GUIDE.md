# Docker Beginner Guide

Using the `new_session` project (Todo API) as the example.

| Value | Yours |
|---|---|
| Project folder | `~/Documents/new_session` |
| Local image name | `new_session-web` (built by Compose) or `my-session` (built manually) |
| Docker Hub name | `sukant3011/todo-api` |
| App file | `main.py` |

---

## Step 1: Go to your project folder

```bash
cd ~/Documents/new_session
```

## Step 2: Check your required files exist

```bash
ls
```
Must include: `Dockerfile`, `requirements.txt`, `main.py`, `.dockerignore`

## Step 3: Build the image

**Option A — plain Docker** (one container, no database managed for you):
```bash
docker build -t my-session .
```

**Option B — Docker Compose** (recommended: builds `web` AND starts Postgres together):
```bash
docker compose up -d --build
```
This single command does **build + run** in one step for both services (`web` and `db`).

## Step 4: Check the image exists

```bash
docker images | grep session
```

## Step 5: Run a container (only needed if you used Option A)

```bash
docker run -d --name my-session-container \
  --add-host=host.docker.internal:host-gateway \
  -p 8003:8000 \
  -e DATABASE_URL="postgresql://postgres:2424@host.docker.internal:5432/todo_db" \
  my-session
```
(If you used Compose in Step 3, skip this — your containers are already running.)

## Step 6: Check it's running and test it

```bash
docker ps
curl http://localhost:8003/
curl http://localhost:8003/todos
```

## Step 7: Log in to Docker Hub (once per computer)

```bash
docker login
```

## Step 8: Tag your image with your Docker Hub username

Only tag the image **you built** (`web`), never `postgres` — that image isn't yours, it's already public on Docker Hub:
```bash
docker tag new_session-web sukant3011/todo-api:latest
```
(If you used Option A, tag `my-session` instead of `new_session-web`.)

## Step 9: Push it

```bash
docker push sukant3011/todo-api:latest
```

## Step 10: Confirm it on Docker Hub

Open `https://hub.docker.com/r/sukant3011/todo-api` in your browser.

---

## Everything in one block

```bash
cd ~/Documents/new_session
docker compose up -d --build
docker compose ps
curl http://localhost:8003/

docker login
docker tag new_session-web sukant3011/todo-api:latest
docker push sukant3011/todo-api:latest
```

---

## Important things to remember

### Only push images YOU built
`docker-compose.yml` has two services: `db` (`image: postgres:16-alpine`, downloaded from Docker Hub) and `web` (`build: .`, built from your own code). You only ever push `web`. `postgres:16-alpine` already exists on Docker Hub, owned by the Postgres team — pushing it would be pointless and isn't yours to push.

### `docker-compose.yml` never goes inside the image
`.dockerignore` includes `docker-compose*.yml`, so when `COPY . .` runs during `docker build`, that file is skipped. Proof:
```bash
docker run --rm --entrypoint sh sukant3011/todo-api:latest -c 'ls -a /app'
```
`docker-compose.yml` will **not** appear in the list — only `main.py`, `requirements.txt`, `Dockerfile`, `.dockerignore`, `.env.example`.

### Pushing a new name creates a new Docker Hub repo automatically
You never need to create the repo on the Docker Hub website first. The first `docker push` with a name you haven't used before creates it, as a **public** repo by default (free plan allows 1 private repo).

### The database lives fully inside Docker, separate from your computer
With `image: postgres:16-alpine` in Compose, Postgres runs in its own container with its own storage (the `pgdata` volume) — completely separate from any Postgres installed directly on your computer. Your app's `DATABASE_URL` points to `db:5432` (the container's service name), not `localhost:5432`. Proof:
```bash
# Your computer's real Postgres — no table here
psql -h localhost -U postgres -d todo_db -c "\dt"

# Inside the db container — table exists here
docker compose exec db psql -U postgres -d todo_db -c "\dt"
```

### `docker-compose.yml` only handles infrastructure, never your data/logic
| What | Who | Where |
|---|---|---|
| Start Postgres, set user/password/db name, keep data safe, connect `web` to `db` | `docker-compose.yml` | the compose file |
| Create the `todos` table, insert rows, read rows | `main.py` (your Python code) | `get_conn()` and the API endpoints |

Compose sets up **where things run**; your code decides **what the app actually does**.

---

## Topic 11: Restart Policies & Healthchecks

### 11.1 Restart Policies

**Idea:** a restart policy tells Docker "if this container stops, should you start it again?" Without one, the default is `no`, so nothing comes back by itself after a crash or a computer restart.

| Option | App crashes | Computer restarts | You stop it yourself (`docker stop`) |
|---|---|---|---|
| `no` (default) | ❌ not restarted | ❌ not restarted | stays stopped |
| `always` | ✅ restarted | ✅ restarted | ⚠️ comes back anyway |
| `unless-stopped` | ✅ restarted | ✅ restarted | stays stopped ✅ |
| `on-failure` | ✅ restarted | ❌ not restarted | stays stopped |

➡️ **Use `unless-stopped`** for web apps and databases.

```yaml
    restart: unless-stopped
```
```bash
docker run -d --restart unless-stopped myimage
docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' todo-api-web-1   # check it
docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' todo-api-db-1
```

### 11.2 Healthchecks

**Idea:** `Up` (running) only means the program is running. `(healthy)` means Docker **checked** and the app really answers. A healthcheck is a small test Docker runs repeatedly to tell the difference. States: `starting` → `healthy` / `unhealthy`.

`db` (Postgres):
```yaml
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5
```

`web` (FastAPI):
```yaml
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
```

| Setting | Meaning |
|---|---|
| `test` | The check to run (opens the home page, from inside the container) |
| `interval` | How often to run it |
| `timeout` | How long to wait for an answer before counting it as failed |
| `retries` | Failures in a row before marking `unhealthy` |
| `start_period` | Startup time where failures don't count yet |

```bash
docker compose ps                                              # shows (healthy) / (unhealthy)
docker inspect -f '{{json .State.Health}}' todo-api-web-1       # full details
```

### 11.3 `depends_on` + `service_healthy`

```yaml
  web:
    depends_on:
      db:
        condition: service_healthy
```
Means: **don't start `web` until `db` is healthy**, not just started — needed because the app connects to Postgres immediately on startup.

| | Waits until | Safe? |
|---|---|---|
| `depends_on: - db` | `db` has **started** | ❌ |
| `condition: service_healthy` | `db` is **healthy** | ✅ |

### 11.4 Restart policy vs healthcheck

| | Restart policy | Healthcheck |
|---|---|---|
| Job | **Acts** — starts the container again | **Watches** — checks if it really works |
| When | Only when the container **stops (exits)** | Every few seconds, while it runs |

⚠️ **An `unhealthy` container is NOT restarted automatically** by plain Docker/Compose — it's only marked. Restart policies only react to the container actually **exiting**.

### 11.5 `HEALTHCHECK` inside the Dockerfile

**Idea:** so far, the healthcheck lived only in `docker-compose.yml` — it only applies when **this specific compose file** is used. A `HEALTHCHECK` written **inside the Dockerfile** gets baked into the **image itself**, so it works no matter how the image is run: `docker compose up`, plain `docker run`, or pulled by someone else on Docker Hub who writes their own setup.

**How to write it — the code:**
```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1
```

| Part | Meaning |
|---|---|
| `HEALTHCHECK` | The Dockerfile instruction that defines a healthcheck |
| `--interval=10s` | How often to run the check |
| `--timeout=5s` | How long to wait for an answer |
| `--start-period=10s` | Startup grace period — failures here don't count |
| `--retries=3` | Failures in a row before `unhealthy` |
| `CMD python -c "..."` | The actual command to run **inside the container** |
| `|| exit 1` | If the Python command throws an error (can't reach the app), exit with code 1 — Docker treats a non-zero exit as "failed" |

**Where it goes — in the Dockerfile**, placed after `EXPOSE` and before `CMD`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**How to implement it — rebuild, then test:**
```bash
docker build -t todo-api .
docker run -d --name hc-test \
  --add-host=host.docker.internal:host-gateway \
  -e DATABASE_URL="postgresql://postgres:2424@host.docker.internal:5432/todo_db" \
  todo-api
sleep 12
docker ps --filter name=hc-test
```
Expected: `Up ... (healthy)` — **even though this `docker run` never mentioned `healthcheck:` anywhere.** The check came from inside the image.

```bash
docker rm -f hc-test     # cleanup
```

### Dockerfile `HEALTHCHECK` vs Compose `healthcheck:`

| | Dockerfile `HEALTHCHECK` | Compose `healthcheck:` |
|---|---|---|
| Lives in | The image itself | `docker-compose.yml` only |
| Works with plain `docker run`? | ✅ Yes | ❌ No |
| Works with `docker compose up`? | ✅ Yes | ✅ Yes |
| If both are written | **Compose's `healthcheck:` wins** — it overrides the Dockerfile's | — |

**Rule of thumb:** write it in the **Dockerfile** if you want the check to always exist, for anyone who ever runs this image, anywhere. Write (or override) it in **`docker-compose.yml`** if a particular project needs a different interval/timeout/test than the image's default.

### My final `docker-compose.yml` (with restart + healthchecks on both services)

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    restart: unless-stopped
    ports:
      - "8003:8000"
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```
