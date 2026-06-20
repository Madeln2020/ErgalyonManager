import os
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.processing_pipeline import ProcessingPipeline
from app.services.rag_service import RAGService
from app.database import get_db
from app.auth import require_role, Role
from app.models import User

router = APIRouter(prefix="/api/v1/catalogs", tags=["catalogs"])

@router.post("/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    supplier_id: str = Form("9636258d-0821-4379-b1bb-202dda9573c2"),
    current_user: User = Depends(require_role(Role.USER)),
):
    """Upload a catalog (PDF or image) and run vision parser.
    Returns the list of extracted product specs.
    """
    temp_dir = "/tmp/catalogs"
    os.makedirs(temp_dir, exist_ok=True)

    temp_path = os.path.join(temp_dir, f"{uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    pipeline = ProcessingPipeline()
    result = pipeline._process_file(temp_path, "catalog")

    try:
        os.remove(temp_path)
    except Exception:
        pass

    if not result or "catalog_specs" not in result:
        raise HTTPException(status_code=500, detail="Vision parsing failed")

    return {"specs": result["catalog_specs"], "confidence": result.get("confidence", 0.0)}


@router.post("/{product_id}/rag-enrich")
async def rag_enrich_catalog_product(
    product_id: str,
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.USER)),
):
    """Enrich a catalog product using RAG service."""
    rag_service = RAGService(db)
    results = await rag_service.search(query)
    return {"product_id": product_id, "enrichment_query": query, "rag_results": results}
