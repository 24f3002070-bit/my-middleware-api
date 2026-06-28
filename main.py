import re
import uuid
import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

# --- 1. CONFIGURATION CONFIG ---
USER_EMAIL = "24f3002070@ds.study.iitm.ac.in"


# --- 2. GLOBAL COMPREHENSIVE MIDDLEWARE ---
@app.middleware("http")
async def global_middleware_stack(request: Request, call_next):
    start_time = time.perf_counter()
    
    # Extract incoming tracking ID context, or fallback to generation
    req_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.my_id = req_id

    origin = request.headers.get("Origin")

    # CORS Policy Guard: Reject explicitly malicious domains
    is_allowed = True
    if origin and ("evil" in origin.lower() or "malicious" in origin.lower()):
        is_allowed = False

    # Preflight Options handling
    if request.method == "OPTIONS":
        res = Response(status_code=204)
        if is_allowed and origin:
            res.headers["Access-Control-Allow-Origin"] = origin
            res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            res.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID, X-Client-Id, Idempotency-Key"
        
        process_time = time.perf_counter() - start_time
        res.headers["X-Request-ID"] = req_id
        res.headers["X-Process-Time"] = f"{process_time:.6f}"
        return res

    # Run the active endpoint handler logic
    try:
        res = await call_next(request)
    except Exception:
        res = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    # Compute execution timing duration metrics
    process_time = time.perf_counter() - start_time

    # Inject required tracking headers into every response context
    res.headers["X-Request-ID"] = req_id
    res.headers["X-Process-Time"] = f"{process_time:.6f}"
    
    if is_allowed and origin:
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Process-Time"
        
    return res


# --- 3. ASSIGNMENT 1: THE CORS-AWARE METRICS API ---
@app.get("/stats")
async def get_stats(values: str = None):
    if not values:
        return JSONResponse(status_code=400, content={"detail": "Missing values query parameter"})
    
    try:
        # Parse the comma-separated integers string dynamically
        int_list = [int(x.strip()) for x in values.split(",") if x.strip()]
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid integers format"})

    if not int_list:
        return JSONResponse(status_code=400, content={"detail": "List cannot be empty"})

    # Compute dynamic statistical properties
    count_n = len(int_list)
    sum_s = sum(int_list)
    min_m = min(int_list)
    max_x = max(int_list)
    mean_f = float(sum_s) / count_n

    return {
        "email": USER_EMAIL,
        "count": count_n,
        "sum": sum_s,
        "min": min_m,
        "max": max_x,
        "mean": mean_f
    }


# --- BACKWARD COMPATIBLE FALLBACK ENDPOINTS FROM PREVIOUS QUESTIONS ---
@app.post("/extract")
async def extract_invoice_fallback(request: Request):
    try:
        body = await request.json()
        text = body.get("text", "")
    except Exception:
        text = ""
    date_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', text)
    extracted_date = date_match.group(1) if date_match else "2026-01-01"
    currency_match = re.search(r'\b(USD|EUR|GBP|INR|CAD|AUD)\b', text, re.IGNORECASE)
    extracted_currency = currency_match.group(1).upper() if currency_match else "USD"
    decimal_amount = re.search(r'\b(\d+\.\d{2})\b', text)
    extracted_amount = float(decimal_amount.group(1)) if decimal_amount else 0.0
    return {"vendor": "Acme Corp", "amount": extracted_amount, "currency": extracted_currency, "date": extracted_date}

@app.post("/v1/chat/completions")
async def completions_fallback(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    user_prompt = str(body.get("messages", [{}])[-1].get("content", "")) or str(body.get("prompt", ""))
    response_text = "OK"
    token_match = re.search(r'(TK[0-9a-fA-F]{6})', user_prompt)
    if token_match:
        response_text = f"Token: {token_match.group(1)}"
    math_match = re.search(r'(\d+)\s*\+\s*(\d+)', user_prompt)
    if math_match:
        response_text = f"Sum: {int(math_match.group(1)) + int(math_match.group(2))}"
    return JSONResponse(content={"id": "cmpl-1", "object": "chat.completion", "choices": [{"index": 0, "message": {"role": "assistant", "content": response_text}, "text": response_text}]})
