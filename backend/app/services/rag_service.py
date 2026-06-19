# EDM v2 — Retrieval-Augmented Generation service
#
# Uses your FreeLLM API endpoint (embeddings + chat) for semantic search
# and structured data enrichment.  Falls back to PostgreSQL full-text search
# when the API is unreachable.

import json
import math
import logging
from typing import List, Dict, Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import class_mapper

from app import models
from app.config import settings

logger = logging.getLogger("edm.rag")


def _prod_to_dict(prod: models.Product) -> Dict[str, Any]:
    """Convert a Product SQLAlchemy model to a plain dict."""
    columns = [c.key for c in class_mapper(models.Product).columns]
    result = {}
    for col in columns:
        val = getattr(prod, col)
        # Convert UUID, datetime, Decimal to serializable types
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        elif hasattr(val, "hex"):
            val = str(val)
        result[col] = val
    return result


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors (skips zero-vector edge cases)."""
    dot = sum(va * vb for va, vb in zip(a, b))
    na = math.sqrt(sum(v * v for v in a))
    nb = math.sqrt(sum(v * v for v in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class RAGService:
    """Retrieval-Augmented Generation service backed by the FreeLLM API.

    The same endpoint provides both *embeddings* (for semantic product search)
    and *chat completions* (for structured enrichment).  Everything degrades
    gracefully — no API, no problem → falls back to PostgreSQL full‑text.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._api_key = settings.FREELLM_API_KEY or ""
        self._base_url = (settings.FREELLM_BASE_URL or "").rstrip("/")
        self._embed_model = settings.FREELLM_EMBEDDING_MODEL or "auto"
        self._chat_model = settings.FREELLM_CHAT_MODEL or "deepseek-ai/deepseek-v4-pro"
        self._enabled = bool(self._api_key and self._base_url)

    # ── helpers ───────────────────────────────────────────────────────────

    async def _embed(self, text: str) -> Optional[List[float]]:
        """Call FREELLM_BASE_URL/embeddings and return a vector or None."""
        if not self._enabled:
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._base_url}/embeddings",
                    json={"model": self._embed_model, "input": text},
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if resp.is_success:
                    data = resp.json()
                    return data.get("data", [{}])[0].get("embedding")
                logger.warning("Embedding API returned %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("Embedding API call failed: %s", exc)
        return None

    async def _chat(self, system: str, user: str, max_tokens: int = 512, temperature: float = 0.0) -> Optional[str]:
        """Call FREELLM_BASE_URL/chat/completions and return the text reply."""
        if not self._enabled:
            return None
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    json={
                        "model": self._chat_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if resp.is_success:
                    data = resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content")
                logger.warning("Chat API returned %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("Chat API call failed: %s", exc)
        return None

    # ── public API ────────────────────────────────────────────────────────

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Semantic product search using embeddings.

        1. Generate an embedding for the query.
        2. Fetch all products that *have* an embedding stored.
        3. Rank by cosine similarity → return top *limit*.
        4. If fewer results than *limit*, pad with full‑text search results.
        5. If the API is unavailable, fall back to plain full‑text.
        """
        # ── try semantic search ────────────────────────────────────────
        query_vec = await self._embed(query)
        if query_vec is not None:
            try:
                # Load every product that has an embedding
                stmt = select(models.Product).where(
                    models.Product.embedding.isnot(None)
                )
                result = await self.db.execute(stmt)
                products = result.scalars().all()

                if products:
                    # Decode + rank
                    scored: List[tuple[float, models.Product]] = []
                    for prod in products:
                        emb = prod.embedding
                        if emb and isinstance(emb, list) and len(emb) == len(query_vec):
                            sim = _cosine_similarity(query_vec, emb)
                            scored.append((sim, prod))
                    scored.sort(key=lambda x: x[0], reverse=True)

                    top: List[models.Product] = [p for _, p in scored[:limit]]

                    # Return whichever we found
                    result_dicts = [_prod_to_dict(p) for p in top]

                    # If we have fewer than limit, pad with full-text
                    if len(result_dicts) < limit:
                        pad_count = limit - len(result_dicts)
                        existing_ids = {p.id for p in top}
                        fallback = await self._fulltext_search(
                            query, limit=pad_count, exclude_ids=existing_ids
                        )
                        result_dicts.extend(fallback)

                    return result_dicts

            except Exception as exc:
                logger.warning("Semantic search failed, falling back to full-text: %s", exc)

        # ── fallback: PostgreSQL full‑text ─────────────────────────────
        return await self._fulltext_search(query, limit=limit)

    async def enrich(self, product_id: str, context: str) -> Dict[str, Any]:
        """Enrich a product using the FreeLLM chat API + generate an embedding.

        1. Find the product.
        2. Use chat completions to extract structured JSON (description,
           key_attributes, brand, category_hint).
        3. Generate an embedding for the enriched description.
        4. Persist both ``rag_context`` and ``embedding``.

        Falls back to storing raw context if the chat API is unavailable.
        """
        stmt = select(models.Product).where(models.Product.id == product_id)
        result = await self.db.execute(stmt)
        prod = result.scalar_one_or_none()
        if not prod:
            raise ValueError(f"Product {product_id} not found")

        structured = None

        if self._enabled:
            system = (
                "You are a JSON data extractor. You MUST respond with ONLY a raw JSON object, no explanation, no markdown."
            )
            user = (
                'Extract product info from this supplier text. Return JSON with: description, key_attributes (list), brand, category_hint.\n\n'
                'Example input: "MAKITA 18V DRILL 2-SPEED"\n'
                'Example output: {"description":"18V cordless drill 2-speed","key_attributes":["18V","2-speed","cordless"],"brand":"Makita","category_hint":"power_drills"}\n\n'
                f'Input: {context[:3000]}\nOutput:'
            )
            reply = await self._chat(system, user)
            if reply:
                try:
                    # Strip possible markdown fences
                    text = reply.strip()
                    if text.startswith("```"):
                        lines = text.splitlines()
                        if len(lines) > 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
                            text = "\n".join(lines[1:-1])
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end != -1:
                        structured = json.loads(text[start:end + 1])
                    if not isinstance(structured, dict):
                        structured = {}
                except json.JSONDecodeError:
                    logger.warning("Chat API returned non-JSON; storing raw")
                    structured = None

        if structured:
            structured["source"] = "LLM_enrichment"
            prod.rag_context = json.dumps(structured)
            # Build a text to embed from the extracted description
            embed_text = structured.get("description") or context[:500]
        else:
            prod.rag_context = json.dumps({"source": "RAG", "text": context})
            embed_text = context[:500]

        # Generate and store embedding
        vec = await self._embed(embed_text)
        if vec is not None:
            prod.embedding = vec  # stored as JSON‑array of floats
        else:
            prod.embedding = None  # clear stale embedding

        await self.db.commit()
        await self.db.refresh(prod)
        return _prod_to_dict(prod)

    async def reembed_all(self, batch_size: int = 50) -> Dict[str, Any]:
        """Regenerate embeddings for every product that has ``rag_context``.

        Useful when first enabling the API or after changing the model.
        Returns a summary dict.
        """
        if not self._enabled:
            return {"status": "disabled", "processed": 0, "errors": 0}

        stmt = select(models.Product).where(
            models.Product.rag_context.isnot(None)
        )
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        processed = 0
        errors = 0
        for prod in products:
            try:
                # Derive text from rag_context
                raw = prod.rag_context
                if isinstance(raw, str):
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        parsed = {"text": raw}
                elif isinstance(raw, dict):
                    parsed = raw
                else:
                    continue

                text = parsed.get("description") or parsed.get("text") or str(raw)[:500]
                vec = await self._embed(text[:500])
                if vec is not None:
                    prod.embedding = vec
                    processed += 1
                else:
                    errors += 1

                if processed % batch_size == 0:
                    await self.db.commit()

            except Exception:
                errors += 1
                logger.exception("reembed_all failed for product %s", prod.id)

        await self.db.commit()
        return {"status": "ok", "processed": processed, "errors": errors}

    # ── internal ─────────────────────────────────────────────────────────

    async def _fulltext_search(
        self, query: str, limit: int = 5, exclude_ids: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """PostgreSQL full‑text search fallback."""
        stmt = (
            select(models.Product)
            .where(func.to_tsvector("english", models.Product.description).match(query))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        candidates = result.scalars().all()
        if exclude_ids:
            candidates = [p for p in candidates if p.id not in exclude_ids]
        return [_prod_to_dict(p) for p in candidates[:limit]]
