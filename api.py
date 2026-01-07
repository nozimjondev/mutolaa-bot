from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, func, or_
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# ==============================
# BASE
# ==============================
Base = declarative_base()

# ==============================
# DATABASE MODELS
# ==============================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    status = Column(String, default="active")  # active/admin/banned
    daily_goal = Column(Integer, default=50)
    monthly_goal = Column(Integer, default=1500)
    reminder_time = Column(String, default="20:00")  # HH:MM local time
    timezone = Column(String, default="GMT+5")
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    books_completed = Column(Integer, default=0)
    join_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ReadingLog(Base):
    __tablename__ = "reading_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, index=True)
    pages = Column(Integer)

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    message_type = Column(String, default="general")
    target_audience = Column(String, default="all")
    pin_message = Column(Integer, default=0)      # 0/1
    notify_all = Column(Integer, default=1)       # 0/1
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at = Column(DateTime, nullable=True)     # ✅ yangi ustun

# ==============================
# PYDANTIC MODELS
# ==============================
class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    status: str
    total_pages: int
    current_streak: int
    books_completed: int
    join_date: datetime
    class Config:
        from_attributes = True

class ReadingLogCreate(BaseModel):
    date: datetime
    pages: int
    book_id: Optional[int] = None  # not used but kept for compatibility

class ReadingLogUpdate(BaseModel):
    pages: int

class UpdateFields(BaseModel):
    daily_goal: Optional[int] = None
    monthly_goal: Optional[int] = None
    reminder_time: Optional[str] = None  # HH:MM
    timezone: Optional[str] = None

# ==============================
# DATABASE SETUP
# ==============================
DATABASE_URL = "sqlite:///./mutolaa.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================
# FASTAPI APP
# ==============================
app = FastAPI(title="Mutolaa Bot API", version="1.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# HELPERS
# ==============================
def get_month_range(dt: datetime):
    start = dt.replace(day=1)
    next_month = (start + timedelta(days=32)).replace(day=1)
    end = next_month - timedelta(days=1)
    return start.date(), end.date()

def get_week_saturday_to_friday(today: datetime):
    delta_to_saturday = (today.weekday() - 5) % 7
    start = (today - timedelta(days=delta_to_saturday)).date()
    end = start + timedelta(days=6)
    return start, end

# ==============================
# ROOT
# ==============================
@app.get("/")
async def root():
    return {"message": "Mutolaa Bot API", "version": "1.2.0", "status": "running"}

# ==============================
# USERS
# ==============================
@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if existing:
        return existing
    new_user = User(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/api/users/by-telegram/{telegram_id}", response_model=UserResponse)
async def get_user_by_telegram(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/api/users/{telegram_id}/update")
async def update_user_fields(telegram_id: int, fields: UpdateFields, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = fields.dict(exclude_unset=True)
    for key, value in data.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    db.commit()
    return {"message": "User updated"}

@app.get("/api/users")
async def list_users(
    search: str = "",
    status: str = "",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(User)
    if search:
        q = q.filter(or_(User.first_name.contains(search), User.username.contains(search)))
    if status:
        q = q.filter(User.status == status)
    users = q.order_by(User.id.desc()).limit(limit).all()
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "first_name": u.first_name,
            "status": u.status,
            "total_pages": u.total_pages
        } for u in users
    ]

@app.put("/api/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    status: str = Query(..., description="New status: active/admin/banned"),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = status
    db.commit()
    return {"message": "Status updated"}

@app.get("/api/users/need-reminder")
async def get_users_need_reminder(db: Session = Depends(get_db)):
    # Compare server local time HH:MM with reminder_time
    now_hhmm = datetime.now().strftime("%H:%M")
    users = db.query(User).filter(User.reminder_time == now_hhmm).all()
    return [{"telegram_id": u.telegram_id, "first_name": u.first_name} for u in users]
# ==============================
# READING LOGS
# ==============================
@app.post("/api/reading-logs")
async def create_reading_log(log: ReadingLogCreate, telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_log = ReadingLog(user_id=user.id, date=log.date, pages=log.pages)
    db.add(new_log)
    user.total_pages += log.pages
    user.last_active = datetime.now(timezone.utc)
    # streak calculation (simplified): if log for today exists, increment current_streak else reset
    # Optional: implement advanced streak logic here
    db.commit()
    return {"message": "Reading log created", "pages": log.pages, "total_pages": user.total_pages}

@app.put("/api/reading-logs/{date}")
async def update_reading_log(date: str, update: ReadingLogUpdate, telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    log_date = datetime.strptime(date, "%Y-%m-%d").date()
    log = db.query(ReadingLog).filter(ReadingLog.user_id == user.id, func.date(ReadingLog.date) == log_date).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    user.total_pages = user.total_pages - log.pages + update.pages
    log.pages = update.pages
    db.commit()
    return {"message": "Reading log updated", "pages": update.pages}

@app.delete("/api/reading-logs/{date}")
async def delete_reading_log(date: str, telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    log_date = datetime.strptime(date, "%Y-%m-%d").date()
    log = db.query(ReadingLog).filter(ReadingLog.user_id == user.id, func.date(ReadingLog.date) == log_date).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    user.total_pages -= log.pages
    db.delete(log)
    db.commit()
    return {"message": "Reading log deleted"}


# ==============================
# LEADERBOARD
# ==============================
@app.get("/api/leaderboard")
async def leaderboard(period: str = "week", limit: int = 10, db: Session = Depends(get_db)):
    """
    Returns a list of {rank, name, pages, books} for the selected period.
    - period: "week", "month", or "all"
    """
    today = datetime.now()
    if period == "week":
        start_date, end_date = get_week_saturday_to_friday(today)
        date_filter = (func.date(ReadingLog.date) >= start_date, func.date(ReadingLog.date) <= end_date)
    elif period == "month":
        start_date, end_date = get_month_range(today)
        date_filter = (func.date(ReadingLog.date) >= start_date, func.date(ReadingLog.date) <= end_date)
    else:
        date_filter = None

    q = db.query(
        User.first_name.label("name"),
        func.sum(ReadingLog.pages).label("pages"),
        User.books_completed.label("books")
    ).join(ReadingLog, User.id == ReadingLog.user_id)

    if date_filter:
        q = q.filter(*date_filter)

    results = q.group_by(User.id).order_by(func.sum(ReadingLog.pages).desc()).limit(limit).all()

    resp = []
    for idx, row in enumerate(results, start=1):
        # row may be tuple depending on SQLAlchemy version
        name = row[0] if isinstance(row, tuple) else getattr(row, "name", "")
        pages = int((row[1] if isinstance(row, tuple) else getattr(row, "pages", 0)) or 0)
        books = int((row[2] if isinstance(row, tuple) else getattr(row, "books", 0)) or 0)
        resp.append({"rank": idx, "name": name, "pages": pages, "books": books})
    return resp

# ==============================
# REPORTS
# ==============================

@app.get("/api/report/week")
async def weekly_report(db: Session = Depends(get_db)):
    """
    Haftalik report (Shanba–Juma).
    Winner flag for users who read 500+ pages in the week.
    """
    today = datetime.now()
    start_date, end_date = get_week_saturday_to_friday(today)

    results = (
        db.query(User.first_name.label("name"), func.sum(ReadingLog.pages).label("pages"))
        .join(ReadingLog, User.id == ReadingLog.user_id)
        .filter(func.date(ReadingLog.date) >= start_date, func.date(ReadingLog.date) <= end_date)
        .group_by(User.id)
        .order_by(func.sum(ReadingLog.pages).desc())
        .all()
    )

    report = []
    for idx, row in enumerate(results, start=1):
        name = row[0] if isinstance(row, tuple) else getattr(row, "name", "")
        pages = int((row[1] if isinstance(row, tuple) else getattr(row, "pages", 0)) or 0)
        report.append({"rank": idx, "name": name, "pages": pages, "winner": pages >= 500})
    return report

@app.get("/api/report/month")
async def monthly_report(db: Session = Depends(get_db)):
    """
    Oylik report (1-sanadan oxirgi sanagacha).
    """
    today = datetime.now()
    start_date, end_date = get_month_range(today)

    results = (
        db.query(User.first_name.label("name"), func.sum(ReadingLog.pages).label("pages"))
        .join(ReadingLog, User.id == ReadingLog.user_id)
        .filter(func.date(ReadingLog.date) >= start_date, func.date(ReadingLog.date) <= end_date)
        .group_by(User.id)
        .order_by(func.sum(ReadingLog.pages).desc())
        .all()
    )

    report = []
    for idx, row in enumerate(results, start=1):
        name = row[0] if isinstance(row, tuple) else getattr(row, "name", "")
        pages = int((row[1] if isinstance(row, tuple) else getattr(row, "pages", 0)) or 0)
        report.append({"rank": idx, "name": name, "pages": pages})
    return report


# ==============================
# STATS (ADMIN DASHBOARD)
# ==============================

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    active_today = db.query(User).filter(func.date(User.last_active) == datetime.now().date()).count()
    total_pages = db.query(func.sum(User.total_pages)).scalar() or 0
    books_completed = db.query(func.sum(User.books_completed)).scalar() or 0

    one_week_ago = datetime.now() - timedelta(days=7)
    new_users = db.query(User).filter(User.join_date >= one_week_ago).count()
    weekly_growth = (new_users / total_users * 100) if total_users > 0 else 0.0

    seven_days_ago = datetime.now() - timedelta(days=7)
    pages_last_week = db.query(func.sum(ReadingLog.pages)).filter(ReadingLog.date >= seven_days_ago).scalar() or 0
    avg_pages_per_day = (pages_last_week / 7.0) if pages_last_week else 0.0

    return {
        "total_users": total_users,
        "weekly_growth": weekly_growth,
        "active_today": active_today,
        "total_pages": int(total_pages),
        "avg_pages_per_day": avg_pages_per_day,
        "books_completed": int(books_completed or 0)
    }

# ==============================
# WEEKLY ACTIVITY (ADMIN DASHBOARD)
# ==============================

@app.get("/api/activity/weekly")
async def weekly_activity(db: Session = Depends(get_db)):
    today = datetime.now().date()
    start_date = today - timedelta(days=6)
    data = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        pages = db.query(func.sum(ReadingLog.pages)).filter(func.date(ReadingLog.date) == day).scalar() or 0
        users = db.query(ReadingLog.user_id).filter(func.date(ReadingLog.date) == day).distinct().count()
        data.append({"Day": day.strftime("%a"), "Pages": int(pages), "Users": int(users)})
    return data


# ==============================
# ANNOUNCEMENTS (ADMIN DASHBOARD)
# ==============================
@app.post("/api/announcements")
async def create_announcement(data: Dict[str, Any], admin_id: int, db: Session = Depends(get_db)):
    ann = Announcement(
        message=data.get("message", ""),
        message_type=data.get("message_type", "general"),
        target_audience=data.get("target_audience", "all"),
        pin_message=1 if data.get("pin_message") else 0,
        notify_all=1 if data.get("notify_all") else 0
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return {"message": "Announcement created", "id": ann.id}

@app.get("/api/announcements")
async def list_announcements(db: Session = Depends(get_db)):
    anns = db.query(Announcement).order_by(Announcement.created_at.desc()).limit(20).all()
    return [
        {
            "id": a.id,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
            "sent_at": a.sent_at.isoformat() if a.sent_at else None
        } for a in anns
    ]

# ✅ Qo‘shimcha endpoint: e’lonni yuborilgan deb belgilash
@app.put("/api/announcements/{announcement_id}/mark-sent")
async def mark_announcement_sent(announcement_id: int, db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    ann.sent_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Announcement marked as sent", "id": ann.id}

# ==============================
# DEV SERVER
# ==============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
