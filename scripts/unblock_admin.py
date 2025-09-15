# scripts/unblock_admin.py
import os
import argparse
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

from app.database import SessionLocal, Base, engine
from app.models import User

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Email del usuario a desbloquear y elevar a admin")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        u = db.query(User).filter(User.email == args.email).first()
        if not u:
            print(f"[ERR] No existe usuario con email {args.email}")
            return
        u.is_blocked = False
        u.is_admin = True
        db.commit()
        print(f"[OK] {args.email} desbloqueado y hecho admin.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
