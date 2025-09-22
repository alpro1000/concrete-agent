from fastapi import APIRouter, HTTPException
from agents.concrete_agent import analyze_concrete

router = APIRouter()

@router.post("/concrete")
async def analyze_concrete_endpoint(doc_paths: list[str], smeta_path: str):
    try:
        result = analyze_concrete(doc_paths, smeta_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
