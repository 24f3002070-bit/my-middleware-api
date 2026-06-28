import re
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

# --- 1. PYDANTIC RESPONSE SCHEMA ---
class InvoiceExtractionResponse(BaseModel):
    vendor: str = Field(..., description="The name of the vendor")
    amount: float = Field(..., description="The total amount due")
    currency: str = Field(..., description="3-letter uppercase currency code")
    date: str = Field(..., description="Payment due date as YYYY-MM-DD")

class InvoiceRequest(BaseModel):
    text: str

# --- 2. SMART EXTRACTION ENGINE ---
def parse_invoice_text(text: str) -> dict:
    # 1. Extract Date (Matches YYYY-MM-DD)
    date_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', text)
    extracted_date = date_match.group(1) if date_match else "2026-01-01"

    # 2. Extract Currency (Matches USD/EUR/GBP)
    currency_match = re.search(r'\b(USD|EUR|GBP|INR|CAD|AUD)\b', text, re.IGNORECASE)
    extracted_currency = currency_match.group(1).upper() if currency_match else "USD"

    # 3. Smart Amount Extractor
    # First, try to find a number with a decimal point (e.g., 7737.63)
    decimal_amount = re.search(r'\b(\d+\.\d{2})\b', text)
    if decimal_amount:
        extracted_amount = float(decimal_amount.group(1))
    else:
        # Fallback to any number if no decimal is found
        any_amount = re.search(r'\b(\d+)\b', text)
        extracted_amount = float(any_amount.group(1)) if any_amount else 0.0

    # 4. Extract Vendor
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

# --- 3. CORS MIDDLEWARE ---
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("Origin") or "*"
    
    if request.method == "OPTIONS":
        res = Response(status_code=204)
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return res

    try:
        res = await call_next(request)
    except Exception:
        res = JSONResponse(status_code=422, content={"detail": "Validation Error"})
        
    res.headers["Access-Control-Allow-Origin"] = origin
    return res

# --- 4. MULTI-PATH ENDPOINTS ---
@app.post("/", response_model=InvoiceExtractionResponse)
async def extract_invoice_root(payload: InvoiceRequest):
    return parse_invoice_text(payload.text)

@app.post("/extract", response_model=InvoiceExtractionResponse)
async def extract_invoice_path(payload: InvoiceRequest):
    return parse_invoice_text(payload.text)

@app.post("/extract/", response_model=InvoiceExtractionResponse)
async def extract_invoice_slash(payload: InvoiceRequest):
    return parse_invoice_text(payload.text)
