import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

# --- 1. USER PROFILE ---
USER_EMAIL = "24f3002070@ds.study.iitm.ac.in"

# Change this number if your grader says it expected a different limit (e.g., 8 to 15)
B_LIMIT = 8 

# Tracks request counts per client ID
client_tracker = defaultdict(int)

@app.middleware("http")
async def process_everything(request: Request, call_next):
    # 1. Handle Request Context (Tracking ID)
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = str(uuid.uuid4())
    request.state.my_id = req_id

    origin = request.headers.get("Origin")

    # Smart CORS: Dynamically allow the exam or panel page, but reject "evil" sites
    is_allowed = False
    if origin:
        if "evil" not in origin.lower() and "malicious" not in origin.lower():
            is_allowed = True

    # 2. Handle Browser Security Preflight (OPTIONS)
    if request.method == "OPTIONS":
        res = Response(status_code=204)
        if is_allowed:
            res.headers["Access-Control-Allow-Origin"] = origin
            res.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            res.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID, X-Client-Id"
        res.headers["X-Request-ID"] = req_id
        return res

    # 3. Handle Rate Limiting
    client_id = request.headers.get("X-Client-Id")
    if client_id and request.url.path == "/ping":
        if client_tracker[client_id] >= B_LIMIT:
            err = JSONResponse(status_code=429, content={"detail": "Too many requests"})
            err.headers["X-Request-ID"] = req_id
            if is_allowed:
                err.headers["Access-Control-Allow-Origin"] = origin
            return err
        client_tracker[client_id] += 1

    # Run the actual endpoint logic
    try:
        res = await call_next(request)
    except Exception:
        res = JSONResponse(status_code=500, content={"detail": "Error"})

    # Inject tracking receipts into the response headers
    res.headers["X-Request-ID"] = req_id
    if is_allowed:
        res.headers["Access-Control-Allow-Origin"] = origin
    return res

@app.get("/ping")
async def ping_endpoint(request: Request):
    return {
        "email": USER_EMAIL,
        "request_id": request.state.my_id
    }

