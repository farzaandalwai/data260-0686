from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from hw7_bike_agent import analyze_bike
from hw7_bike_tools import PRICE_URL


router = APIRouter(prefix="/api/hw7/bike")


@router.post("/analyze")
async def analyze(csv_file: UploadFile = File(...), pricing_url: str = Form(PRICE_URL)):
    if not csv_file.filename or not csv_file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file")
    content = await csv_file.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV file exceeds 1 MB")
    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8") from None
    return analyze_bike(csv_text, pricing_url)
