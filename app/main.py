from fastapi import FastAPI, APIRouter, Depends, HTTPException, BackgroundTasks, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging

app = FastAPI()

# Structured logger setup
logger = logging.getLogger("feedback_logger")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s %(message)s | %(extra)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def structured_log(message: str, **extra):
    logger.info(message, extra={"extra": extra})

### In-memory storage (simulating DB)
feedback_storage: Dict[str, Dict[str, Any]] = {}

### Profanity List (very basic for demo)
PROFANE_WORDS = {"badword", "nasty"}

def contains_profanity(text: str) -> Optional[str]:
    for word in PROFANE_WORDS:
        if word.lower() in text.lower():
            return word
    return None

# Simulated user authentication w/ roles
class User(BaseModel):
    username: str
    role: str  # 'user' or 'moderator'

def get_current_user(request: Request) -> User:
    # Simulate auth via X-User and X-Role headers
    username = request.headers.get("x-user")
    role = request.headers.get("x-role")
    if not username or not role:
        raise HTTPException(status_code=401, detail="Missing or invalid authentication headers.")
    if role not in ("user", "moderator"):
        raise HTTPException(status_code=403, detail="Invalid role.")
    return User(username=username, role=role)

def moderator_required(user: User = Depends(get_current_user)):
    if user.role != "moderator":
        raise HTTPException(status_code=403, detail="Moderator role required.")
    return user

# Models
class FeedbackStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class FeedbackBase(BaseModel):
    content: constr(min_length=5, max_length=500)

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackOut(FeedbackBase):
    id: str
    status: str
    author: str
    created_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    moderator: Optional[str] = None

class FeedbackStatusUpdate(BaseModel):
    status: str  # 'approved' or 'rejected'

# Routers
feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])
moderation_router = APIRouter(prefix="/moderate", tags=["Moderation"])

@feedback_router.post("/", response_model=FeedbackOut, status_code=201)
def submit_feedback(
    feedback: FeedbackCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    profane = contains_profanity(feedback.content)
    if profane:
        structured_log(
            "Rejected feedback for profanity",
            user=user.username,
            reason=f"Profane word detected: {profane}"
        )
        raise HTTPException(
            status_code=400, 
            detail=f"Profanity detected: '{profane}' in feedback."
        )
    feedback_id = str(uuid.uuid4())
    now = datetime.utcnow()
    item = {
        "id": feedback_id,
        "content": feedback.content,
        "status": FeedbackStatus.PENDING,
        "author": user.username,
        "created_at": now,
        "approved_at": None,
        "rejected_at": None,
        "moderator": None,
    }
    feedback_storage[feedback_id] = item
    structured_log("Feedback submitted", user=user.username, feedback_id=feedback_id)
    return item

@moderation_router.get("/feedbacks", response_model=List[FeedbackOut])
def list_feedbacks(
    status: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(moderator_required),
):
    items = list(feedback_storage.values())
    if status:
        items = [f for f in items if f["status"] == status]
    if q:
        items = [f for f in items if q.lower() in f["content"].lower()]
    items = sorted(items, key=lambda x: x["created_at"], reverse=True)
    structured_log("Moderator list feedbacks", moderator=user.username, total=len(items))
    return items[skip: skip+limit]

@moderation_router.post("/feedbacks/{feedback_id}/status", response_model=FeedbackOut)
def update_feedback_status(
    feedback_id: str,
    status_update: FeedbackStatusUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(moderator_required),
):
    item = feedback_storage.get(feedback_id)
    if not item:
        structured_log(
            "Moderator failed feedback status update", 
            moderator=user.username, feedback_id=feedback_id, reason="not found"
        )
        raise HTTPException(status_code=404, detail="Feedback not found")
    if item["status"] != FeedbackStatus.PENDING:
        structured_log(
            "Moderator attempted re-statusing",
            moderator=user.username,
            feedback_id=feedback_id,
            reason=f"Already {item['status']}"
        )
        raise HTTPException(status_code=400, detail=f"Already {item['status']}.")
    if status_update.status not in [FeedbackStatus.APPROVED, FeedbackStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Invalid status update")
    now = datetime.utcnow()
    item["status"] = status_update.status
    item["moderator"] = user.username
    if status_update.status == FeedbackStatus.APPROVED:
        item["approved_at"] = now
        item["rejected_at"] = None
    else:
        item["rejected_at"] = now
        item["approved_at"] = None
    background_tasks.add_task(notify_status_change, item)
    structured_log(
        "Moderator changed feedback status",
        moderator=user.username,
        feedback_id=feedback_id,
        new_status=status_update.status
    )
    return item

# Below is the background notification task (logging only for demo)
def notify_status_change(item: Dict[str, Any]):
    structured_log(
        "Notification: Feedback status changed",
        feedback_id=item["id"],
        new_status=item["status"],
        user=item["author"],
        moderator=item.get("moderator")
    )

# Register
app.include_router(feedback_router)
app.include_router(moderation_router)

# Structured error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    structured_log(
        "HTTPException",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
