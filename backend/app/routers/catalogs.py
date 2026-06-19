import os
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from app.services.processing_pipeline import ProcessingPipeline
from app.services.rag_service import RAGService
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/catalogs", tags=["catalogs"])

@router.post("/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    supplier_id: str = Form("9636258d-0821-4379-b1bb-202dda9573c2"),
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
):
    """Enrich a catalog product using RAG service."""
    rag_service = RAGService(db)
    # Perform a search based on the query, pretending it's for the product
    # In a real scenario, this would involve a proper LLM call with the product's data
    results = await rag_service.search(query)
    # For now, we just return the search results.
    # A full implementation would update the product in the database.
    return {"product_id": product_id, "enrichment_query": query, "rag_results": results}