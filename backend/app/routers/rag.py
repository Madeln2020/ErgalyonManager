from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.rag_service import RAGService

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class EnrichRequest(BaseModel):
    product_id: str
    context: str

@router.post("/search")
async def rag_search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    service = RAGService(db)
    results = await service.search(req.query, req.limit)
    return {"results": results}

@router.post("/enrich")
async def rag_enrich(req: EnrichRequest, db: AsyncSession = Depends(get_db)):
    service = RAGService(db)
    try:
        prod = await service.enrich(req.product_id, req.context)
        return {"product": prod}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
