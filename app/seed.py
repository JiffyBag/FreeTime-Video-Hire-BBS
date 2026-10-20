from app.models import SessionLocal, User, Movie, Snack
from app.auth import hash_password

USERS = [
    ("admin", "admin@email.freetime.video", "admin123", True, 999.99),
    ("guest", "guest@freetime.video", "guest", False, 5.00),
    ("beverly", "beverly@freetime.video", "vhs4life", False, 12.50),
    ("marty", "marty@freetime.video", "1985delorean", False, 2.00),
    ("sarah", "sarah@freetime.video", "sarah1989", False, 25.00),
    ("videokid", "kid@freetime.video", "rewind", False, 0.50),
]

MOVIES = [
    ("The Goonies", 1985, "Adventure", "PG"), ("Back to the Future", 1985, "SciFi", "PG"),
    ("E.T. the Extra-Terrestrial", 1982, "SciFi", "PG"), ("Ghostbusters", 1984, "Comedy", "PG"),
    ("The Breakfast Club", 1985, "Drama", "R"), ("Pretty Woman", 1990, "Romance", "R"),
    ("Top Gun", 1986, "Action", "PG"), ("Die Hard", 1988, "Action", "R"),
    ("The Terminator", 1984, "SciFi", "R"), ("Beetlejuice", 1988, "Comedy", "PG"),
    ("Dirty Dancing", 1987, "Romance", "PG-13"), ("Gremlins", 1984, "Horror", "PG"),
    ("The Princess Bride", 1987, "Fantasy", "PG"), ("RoboCop", 1987, "SciFi", "R"),
    ("Big", 1988, "Comedy", "PG"),
]

SNACKS = [("Popcorn", 2.50, 100), ("Soda", 1.00, 200), ("Blank VHS", 5.00, 50)]


def seed():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            for username, email, pw, is_admin, balance in USERS:
                db.add(User(username=username, email=email, password_hash=hash_password(pw),
                             is_admin=is_admin, balance=balance))
        if db.query(Movie).count() == 0:
            for title, year, genre, rating in MOVIES:
                db.add(Movie(title=title, year=year, genre=genre, rating=rating, rental_price=2.0, stock=3))
        if db.query(Snack).count() == 0:
            for name, price, stock in SNACKS:
                db.add(Snack(name=name, price=price, stock=stock))
        db.commit()
    finally:
        db.close()
