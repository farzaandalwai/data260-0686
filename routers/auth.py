import time
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)

USERNAME = "farzaan"
PASSWORD = "rental260"
DISPLAY_NAME = "Farzaan"
SESSION_IDLE_SECONDS = 60


def session_is_active(request):
    if not request.session.get("username"):
        return False

    last_activity = request.session.get("last_activity")
    now = time.time()
    if last_activity is None or now - float(last_activity) > SESSION_IDLE_SECONDS:
        request.session.clear()
        return False

    request.session["last_activity"] = now
    return True


@router.get("/")
def home(request: Request):
    logged_in = session_is_active(request)
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "logged_in": logged_in,
            "name": request.session.get("name", ""),
        },
    )


@router.get("/login")
def login_page(request: Request):
    if session_is_active(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": ""},
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(),
    password: str = Form(),
):
    if username == USERNAME and password == PASSWORD:
        request.session["username"] = USERNAME
        request.session["name"] = DISPLAY_NAME
        request.session["last_activity"] = time.time()
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password."},
        status_code=401,
    )


@router.get("/dashboard")
def dashboard(request: Request):
    if not session_is_active(request):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"name": request.session.get("name", DISPLAY_NAME)},
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
