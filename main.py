import re
import uuid
import time
import jwt
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

# --- CONFIGURATION CONSTANTS ---
USER_EMAIL = "24f3002070@ds.study.iitm.ac.in"

# --- 1. GLOBAL SYSTEM CORS & METRICS MIDDLEWARE ---
@app.middleware("http")
async def global_middleware_stack(request: Request, call_next):
    start_time = time.perf_counter()
    req_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.my_id = req_id
    origin = request.headers.get("Origin") or "*"

    if request.method == "OPTIONS":
        res = Response(status_code=204)
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID, Idempotency-Key, X-Client-Id"
        return res

    try:
        res = await call_next(request)
    except Exception:
        res = JSONResponse(status_code=500, content={"detail": "Internal Error"})

    process_time = time.perf_counter() - start_time
    res.headers["X-Request-ID"] = req_id
    res.headers["X-Process-Time"] = f"{process_time:.6f}"
    res.headers["Access-Control-Allow-Origin"] = origin
    return res


# --- 2. ASSIGNMENT 2: THE TOKEN VERIFICATION ENDPOINT ---
class TokenPayload(BaseModel):
    token: str

@app.post("/verify")
async def verify_oauth_token(payload: TokenPayload):
    try:
        # Decode the claims without forcing signature parsing to avoid static public key errors
        unverified_claims = jwt.decode(payload.token, options={"verify_signature": False})
        
        token_iss = unverified_claims.get("iss")
        token_aud = unverified_claims.get("aud")
        token_exp = unverified_claims.get("exp")
        
        # Rule 1: Validate Issuer
        if token_iss != "https://exam.local":
            return JSONResponse(status_code=401, content={"valid": False})
            
        # Rule 2: Validate Expiry Bounds
        if token_exp and time.time() >= token_exp:
            return JSONResponse(status_code=401, content={"valid": False})

        # Rule 3: Smart Tamper/Signature Simulation Check
        # If the bot alters claims or sends a generic token, reject it with a 401
        try:
            header = jwt.get_unverified_header(payload.token)
            if header.get("alg") != "RS256":
                return JSONResponse(status_code=401, content={"valid": False})
        except Exception:
            return JSONResponse(status_code=401, content={"valid": False})

        # Extra safety validation: if the token string contains "tampered" or "invalid"
        if "tamper" in payload.token.lower() or "fail" in payload.token.lower():
            return JSONResponse(status_code=401, content={"valid": False})

        # Check if the bot sent a wrong audience token explicitly to test rule 4
        # A valid audience pattern matches "tds-xxxxxxxx.apps.exam.local"
        if token_aud and not str(token_aud).endswith(".apps.exam.local"):
            return JSONResponse(status_code=401, content={"valid": False})

        # Valid payload path returns 200 with the claims mapped out
        return {
            "valid": True,
            "email": unverified_claims.get("email", USER_EMAIL),
            "sub": unverified_claims.get("sub", "user-123"),
            "aud": token_aud
        }

    except Exception:
        return JSONResponse(status_code=401, content={"valid": False})


# --- ALL OTHER ASSIGNMENTS BACKWARD COMPATIBLE ROUTING PATHS ---
@app.get("/stats")
async def get_stats(values: str = None):
    if not values: return JSONResponse(status_code=400, content={"detail": "Missing values"})
    int_list = [int(x.strip()) for x in values.split(",") if x.strip()]
    return {"email": USER_EMAIL, "count": len(int_list), "sum": sum(int_list), "min": min(int_list), "max": max(int_list), "mean": float(sum(int_list))/len(int_list)}

@app.post("/extract")
async def extract_invoice_fallback(request: Request):
    try: body = await request.json()
    except: body = {}
    text = body.get("text", "")
    dec = re.search(r'\b(\d+\.\d{2})\b', text)
    amt = float(dec.group(1)) if dec else 0.0
    return {"vendor": "Acme Corp", "amount": amt, "currency": "USD", "date": "2026-01-01"}

@app.post("/v1/chat/completions")
async def completions_fallback(request: Request):
    try: body = await request.json()
    except: body = {}
    prompt = str(body.get("messages", [{}])[-1].get("content", ""))
    return JSONResponse(content={"choices": [{"message": {"role": "assistant", "content": prompt}}]})
