# Guide: Image → Container → Docker Hub

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
