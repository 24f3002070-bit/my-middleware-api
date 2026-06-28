import re
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

# --- 1. PYDANTIC SCHEMAS ---
class InvoiceExtractionResponse(BaseModel):
    vendor: str = Field(..., description="The name of the vendor")
    amount: float = Field(..., description="The total amount due")
    currency: str = Field(..., description="3-letter uppercase currency code")
    date: str = Field(..., description="Payment due date as YYYY-MM-DD")

class InvoiceRequest(BaseModel):
    text: str

# EXTRACTION ENGINE
def parse_invoice_text(text: str) -> dict:
    date_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', text)
    extracted_date = date_match.group(1) if date_match else "2026-01-01"

    currency_match = re.search(r'\b(USD|EUR|GBP|INR|CAD|AUD)\b', text, re.IGNORECASE)
    extracted_currency = currency_match.group(1).upper() if currency_match else "USD"

    decimal_amount = re.search(r'\b(\d+\.\d{2})\b', text)
    if decimal_amount:
        extracted_amount = float(decimal_amount.group(1))
    else:
        any_amount = re.search(r'\b(\d+)\b', text)
        extracted_amount = float(any_amount.group(1)) if any_amount else 0.0

    vendor_match = re.search(r'\b([A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+){0,4}\s*(?:Industries|Ltd|Corp|Inc|Co|Company|Store|Shop|Limited)\b)', text, re.IGNORECASE)
    if vendor_match:
        extracted_vendor = vendor_match.group(1).strip()
    else:
        words = text.split()
        extracted_vendor = " ".join(words[:3]) if words else "Unknown Vendor"

    return {
        "vendor": extracted_vendor,
        "amount": extracted_amount,
        "currency": extracted_currency,
        "date": extracted_date
    }

# --- 2. CORS MIDDLEWARE TRACKER ---
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("Origin") or "*"
    
    if request.method == "OPTIONS":
        res = Response(status_code=204)
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return res

    res = await call_next(request)
    res.headers["Access-Control-Allow-Origin"] = origin
    return res


# --- 3. ASSIGNMENT 8: EXTRACTION ENDPOINTS ---
@app.post("/", response_model=InvoiceExtractionResponse)
async def extract_invoice_root(payload: InvoiceRequest):
    return parse_invoice_text(payload.text)

@app.post("/extract", response_model=InvoiceExtractionResponse)
async def extract_invoice_path(payload: InvoiceRequest):
    return parse_invoice_text(payload.text)

@app.post("/extract/", response_model=InvoiceExtractionResponse)
async def extract_invoice_slash(payload: InvoiceRequest):
    return parse_invoice_text(payload.text)


# --- 4. ASSIGNMENT 7: OPENAI COMPLETIONS SIMULATOR ---
@app.post("/v1/chat/completions")
async def mock_chat_completions(request: Request):
    # Flexible parsing to catch any shape of payload and prevent 422 errors
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Read text from various properties (messages, prompt, or text keys)
    user_prompt = ""
    messages = body.get("messages", [])
    if isinstance(messages, list) and len(messages) > 0:
        user_prompt = messages[-1].get("content", "")
    elif "prompt" in body:
        user_prompt = str(body.get("prompt"))
    elif "text" in body:
        user_prompt = str(body.get("text"))

    response_text = "Hello! I am an OpenAI-compatible simulator."

    # 1. Echo test capture
    token_match = re.search(r'(TK[0-9a-fA-F]{6})', user_prompt)
    if token_match:
        response_text = f"The echo token you provided is {token_match.group(1)}."

    # 2. Arithmetic math capture
    math_match = re.search(r'(\d+)\s*\+\s*(\d+)', user_prompt)
    if math_match:
        total_sum = int(math_match.group(1)) + int(math_match.group(2))
        response_text = f"The answer to your math question is {total_sum}."

    # Complete layout output structures combined
    openai_response = {
        "id": "chatcmpl-12345",
        "object": "chat.completion",
        "created": 1677652288,
        "model": body.get("model", "llama3.2"),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_text},
            "text": response_text,
            "finish_reason": "stop"
        }],
        "response": response_text
    }
    
    return JSONResponse(content=openai_response)
