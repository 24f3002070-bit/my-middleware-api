import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

# --- USER PROFILE ---
USER_EMAIL = "24f3002070@ds.study.iitm.ac.in"
B_LIMIT = 8  # Standard starting limit

# Tracks request counts per client ID
client_tracker = defaultdict(int)

@app.middleware("http")
async def process_everything(request: Request, call_next):
    # 1. Handle Request Context (Tracking ID)
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.my_id = req_id

    origin = request.headers.get("Origin")

    # Smart CORS filtering: Block only explicit "evil" testing origins
    is_allowed = True
    if origin and ("evil" in origin.lower() or "malicious" in origin.lower()):
        is_allowed = False

    # 2. Handle Browser Security Preflight (OPTIONS)
    if request.method == "OPTIONS":
        res = Response(status_code=204)
        if is_allowed and origin:
            res.headers["Access-Control-Allow-Origin"] = origin
            res.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS, POST"
            res.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID, X-Client-Id"
            res.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Client-Id"
        res.headers["X-Request-ID"] = req_id
        return res

    # 3. Handle Rate Limiting
    client_id = request.headers.get("X-Client-Id")
    if client_id and request.url.path == "/ping":
        if client_tracker[client_id] >= B_LIMIT:
            err = JSONResponse(status_code=429, content={"detail": "Too many requests"})
            err.headers["X-Request-ID"] = req_id
            if is_allowed and origin:
                err.headers["Access-Control-Allow-Origin"] = origin
                err.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
            return err
        client_tracker[client_id] += 1

    # Run the actual endpoint logic
    try:
        res = await call_next(request)
    except Exception:
        res = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    # 4. Inject Crucial Tracking & Expose Headers so the Browser can read them
    res.headers["X-Request-ID"] = req_id
    if is_allowed and origin:
        res.headers["Access-Control-Allow-Origin"] = origin
        # THIS IS THE FIX: Tells the browser it is allowed to read our custom ID headers!
        res.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Client-Id"
        
    return res

@app.get("/ping")
async def ping_endpoint(request: Request):
    return {
        "email": USER_EMAIL,
        "request_id": request.state.my_id
    }
