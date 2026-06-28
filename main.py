import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

# --- CHANGE ONLY THESE TWO LINES TO MATCH YOUR EXAM SCREEN ---
ALLOWED_ORIGIN = "https://your-panel-origin.com"  # Put your assigned origin here!
USER_EMAIL = "your-email@example.com"             # Put your real email here!
B_LIMIT = 8                                       # Put your assigned bucket size number here!

# This keeps track of how many times a user visits
client_tracker = defaultdict(int)

@app.middleware("http")
async def process_everything(request: Request, call_next):
    # 1. Handle the Tracking ID
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = str(uuid.uuid4())
    request.state.my_id = req_id

    origin = request.headers.get("Origin")

    # 2. Handle the Browser Security Preflight (OPTIONS)
    if request.method == "OPTIONS":
        res = Response(status_code=204)
        if origin == ALLOWED_ORIGIN:
            res.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            res.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            res.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID, X-Client-Id"
        res.headers["X-Request-ID"] = req_id
        return res

    # 3. Handle the Limit Counting
    client_id = request.headers.get("X-Client-Id")
    if client_id and request.url.path == "/ping":
        if client_tracker[client_id] >= B_LIMIT:
            err = JSONResponse(status_code=429, content={"detail": "Too many requests"})
            err.headers["X-Request-ID"] = req_id
            if origin == ALLOWED_ORIGIN:
                err.headers["Access-Control-Allow-Origin"] = origin
            return err
        client_tracker[client_id] += 1

    # Run the actual request
    try:
        res = await call_next(request)
    except Exception:
        res = JSONResponse(status_code=500, content={"detail": "Error"})

    # Inject final tracking receipts
    res.headers["X-Request-ID"] = req_id
    if origin == ALLOWED_ORIGIN:
        res.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    return res

@app.get("/ping")
async def ping_endpoint(request: Request):
    return {
        "email": USER_EMAIL,
        "request_id": request.state.my_id
    }
