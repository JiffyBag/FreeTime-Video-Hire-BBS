from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from app.models import init_db, SessionLocal, User, Movie, Snack, Rental
from app.seed import seed
from app.auth import create_token, create_reset_token, decode_token, get_current_user, hash_password, verify_password
from app.email_service import send_reset_email


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    yield


app = FastAPI(title="FreeTime Video Hire BBS API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "db": "connected", "vhs": "rewound"}


# ---------------- Auth ----------------

class RegisterReq(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_admin: Optional[bool] = False   # VULN: mass assignment - client can self-grant admin
    balance: Optional[float] = None    # VULN: mass assignment - client can set starting balance


@app.post("/api/v1/auth/register")
def register(req: RegisterReq, db=Depends(db_session)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="username taken")
    # VULN: Mass Assignment - is_admin/balance taken directly from request body
    # with no allowlist, letting {"is_admin": true, "balance": 9999} through.
    user = User(
        username=req.username, email=req.email,
        password_hash=hash_password(req.password),
        is_admin=bool(req.is_admin), balance=req.balance if req.balance is not None else 5.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "email": user.email}


class LoginReq(BaseModel):
    username: str
    password: str


@app.post("/api/v1/auth/login")
def login(req: LoginReq, db=Depends(db_session)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="bad credentials")
    token = create_token(user.id, user.username, user.is_admin)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "is_admin": user.is_admin}


class ForgotReq(BaseModel):
    email: EmailStr


@app.post("/api/v1/auth/forgot-password")
async def forgot_password(req: ForgotReq, db=Depends(db_session)):
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        token = create_reset_token(user.id)
        link = f"http://localhost:3000/reset.html?token={token}"
        await send_reset_email(user.email, link)
    # always 200 regardless of whether the email exists, to avoid user enumeration here
    return {"message": "If that email exists, a reset link was sent. Check the Mail Server."}


class ResetReq(BaseModel):
    token: str
    new_password: str


@app.post("/api/v1/auth/reset-password")
def reset_password(req: ResetReq, db=Depends(db_session)):
    try:
        payload = decode_token(req.token)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid or expired token")
    if payload.get("purpose") != "reset":
        raise HTTPException(status_code=400, detail="invalid token purpose")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "password reset successful"}


# ---------------- Movies / Snacks (public) ----------------

@app.get("/api/v1/movies")
def list_movies(limit: int = 50, db=Depends(db_session)):
    # VULN: BOPLA / excessive data exposure - no upper/lower bound on
    # client-supplied limit, so ?limit=9999 or ?limit=-1 dumps everything.
    q = db.query(Movie).limit(limit).all()
    return [{"id": m.id, "title": m.title, "year": m.year, "genre": m.genre,
             "stock": m.stock, "rental_price": m.rental_price, "rating": m.rating} for m in q]


@app.get("/api/v1/movies/{movie_id}")
def get_movie(movie_id: int, db=Depends(db_session)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": m.id, "title": m.title, "year": m.year, "genre": m.genre,
            "stock": m.stock, "rental_price": m.rental_price, "rating": m.rating}


@app.get("/api/v1/snacks")
def list_snacks(db=Depends(db_session)):
    rows = db.query(Snack).all()
    return [{"id": s.id, "name": s.name, "price": s.price, "stock": s.stock} for s in rows]


# ---------------- Users ----------------

@app.get("/api/v1/users/{user_id}")
def get_user(user_id: int, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN: BOLA - no check that auth['sub'] == user_id or that caller is admin,
    # so any logged-in user can view anyone's profile/email/balance by id.
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": user.id, "username": user.username, "email": user.email,
            "balance": user.balance, "is_admin": user.is_admin}


# ---------------- Rentals / Snack purchase ----------------

class RentalReq(BaseModel):
    movie_id: int
    qty: int = 1


@app.post("/api/v1/rentals")
def create_rental(req: RentalReq, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN: Unrestricted Resource Consumption - qty is never bounded (0, negative,
    # or huge). A negative qty against a naive "refund" calc can inflate balance;
    # qty: 999999 can drive movie.stock negative with no real check.
    movie = db.get(Movie, req.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="movie not found")
    movie.stock = movie.stock - req.qty
    user_id = int(auth["sub"])
    rental = Rental(user_id=user_id, movie_id=req.movie_id, qty=req.qty)
    db.add(rental)
    db.commit()
    return {"id": rental.id, "movie_id": rental.movie_id, "qty": rental.qty,
            "total_price": movie.rental_price * req.qty, "remaining_stock": movie.stock}


@app.get("/api/v1/rentals")
def list_rentals(db=Depends(db_session), auth=Depends(get_current_user)):
    user_id = int(auth["sub"])
    rows = db.query(Rental).filter(Rental.user_id == user_id).all()
    return [{"id": r.id, "movie_id": r.movie_id, "qty": r.qty} for r in rows]


class SnackPurchaseReq(BaseModel):
    snack_id: int
    qty: int = 1


@app.post("/api/v1/snacks/purchase")
def purchase_snack(req: SnackPurchaseReq, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN: Unrestricted Resource Consumption - same unbounded qty issue as rentals
    snack = db.get(Snack, req.snack_id)
    if not snack:
        raise HTTPException(status_code=404, detail="snack not found")
    snack.stock = snack.stock - req.qty
    db.commit()
    return {"snack": snack.name, "qty": req.qty, "total_price": snack.price * req.qty,
            "remaining_stock": snack.stock}


# ---------------- Admin ----------------
# VULN: BFLA - every admin route below depends only on get_current_user (proves the
# token decodes), never on a real server-side role check against auth['is_admin'].
# Combined with the JWT none-alg bug in auth.py, this is fully forgeable.

@app.get("/api/v1/admin/users")
def admin_list_users(db=Depends(db_session), auth=Depends(get_current_user)):
    rows = db.query(User).all()
    return [{"id": u.id, "username": u.username, "email": u.email,
             "balance": u.balance, "is_admin": u.is_admin} for u in rows]


class AdminAddUserReq(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_admin: bool = False
    balance: float = 5.0


@app.post("/api/v1/admin/users")
def admin_add_user(req: AdminAddUserReq, db=Depends(db_session), auth=Depends(get_current_user)):
    user = User(username=req.username, email=req.email, password_hash=hash_password(req.password),
                is_admin=req.is_admin, balance=req.balance)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}


@app.delete("/api/v1/admin/users/{user_id}")
def admin_delete_user(user_id: int, db=Depends(db_session), auth=Depends(get_current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(user)
    db.commit()
    return {"deleted": user_id}


class AdminMovieReq(BaseModel):
    title: str
    year: int
    genre: str
    stock: int = 3
    rental_price: float = 2.0
    rating: str = "PG"


@app.post("/api/v1/admin/movies")
def admin_add_movie(req: AdminMovieReq, db=Depends(db_session), auth=Depends(get_current_user)):
    m = Movie(**req.dict())
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "title": m.title}


class RestockReq(BaseModel):
    qty: int


@app.post("/api/v1/admin/movies/{movie_id}/restock")
def admin_restock_movie(movie_id: int, req: RestockReq, db=Depends(db_session), auth=Depends(get_current_user)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(status_code=404, detail="not found")
    m.stock += req.qty
    db.commit()
    return {"id": m.id, "title": m.title, "stock": m.stock}


class SnackRestockReq(BaseModel):
    snack_id: int
    qty: int


@app.post("/api/v1/admin/snacks/restock")
def admin_restock_snack(req: SnackRestockReq, db=Depends(db_session), auth=Depends(get_current_user)):
    s = db.get(Snack, req.snack_id)
    if not s:
        raise HTTPException(status_code=404, detail="not found")
    s.stock += req.qty
    db.commit()
    return {"id": s.id, "name": s.name, "stock": s.stock}
