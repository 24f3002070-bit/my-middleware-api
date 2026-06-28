import time
import uuid
import json
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

# --- 1. CONFIGURATION CONSTANTS ---
TOTAL_T = 45      # Matched to your exact catalog size requirement
LIMIT_R = 15      # Your assigned rate-limit bucket size

# Memory storage banks
idempotency_keys = {}
client_rate_tracker = defaultdict(list)

# Generate a list of items from 1 to T
catalog_data = [{"id": i, "name": f"Item-{i}"} for i in range(1, TOTAL_T + 1)]

@app.middleware("http")
async def engineering_middleware(request: Request, call_next):
    origin = request.headers.get("Origin") or "*"

    # Handle Browser Security Preflight (OPTIONS)
    if request.method == "OPTIONS":
        res = Response(status_code=204)
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Idempotency-Key, X-Client-Id"
        res.headers["Access-Control-Expose-Headers"] = "Retry-After"
        return res

    # Per-Client 10-Second Rate Limiter Window
    client_id = request.headers.get("X-Client-Id")
    if client_id and request.url.path == "/orders":
        now = time.time()
        # Clean up old tracking timestamps
        client_rate_tracker[client_id] = [t for t in client_rate_tracker[client_id] if now - t < 10]
        
        if len(client_rate_tracker[client_id]) >= LIMIT_R:
            # BULLETPROOF FIX: Use a direct raw Response so headers are NEVER stripped or altered
            error_content = json.dumps({"detail": "Too Many Requests"})
            err_res = Response(content=error_content, status_code=429, media_type="application/json")
            
            # Inject headers explicitly into the response header dictionary
            err_res.headers["Retry-After"] = "10"
            err_res.headers["retry-after"] = "10"
            err_res.headers["Access-Control-Allow-Origin"] = origin
            err_res.headers["Access-Control-Expose-Headers"] = "Retry-After, retry-after"
            return err_res
        
        client_rate_tracker[client_id].append(now)

    try:
        res = await call_next(request)
    except Exception:
        res = JSONResponse(status_code=500, content={"detail": "Internal Error"})

    res.headers["Access-Control-Allow-Origin"] = origin
    res.headers["Access-Control-Expose-Headers"] = "Retry-After, retry-after"
    return res

# 1. Idempotent order creation endpoint
@app.post("/orders", status_code=201)
async def create_order(request: Request):
    idem_key = None
    for key, value in request.headers.items():
        if key.lower() == "idempotency-key":
            idem_key = value
            break

    if not idem_key:
        idem_key = str(uuid.uuid4())

    if idem_key in idempotency_keys:
        return {"id": idempotency_keys[idem_key]}

    new_order_id = str(uuid.uuid4())
    idempotency_keys[idem_key] = new_order_id
    return {"id": new_order_id}

# 2. Cursor pagination endpoint
@app.get("/orders")
async def list_orders(limit: int = 10, cursor: str = None):
    start_index = 0
    if cursor:
        try:
            start_index = int(cursor)
        except ValueError:
            start_index = 0

    end_index = min(start_index + limit, TOTAL_T)
    items_slice = catalog_data[start_index:end_index]
    next_cursor = str(end_index) if end_index < TOTAL_T else ""

    return {
        "items": items_slice,
        "next_cursor": next_cursor
    }
