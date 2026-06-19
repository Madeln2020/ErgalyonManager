#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('/home/admin/edm-v2/backend'))

from app.database import async_session_factory
from app.services.rag_service import RAGService

async def main():
    async with async_session_factory() as db:
        service = RAGService(db)
        result = await service.reembed_all(batch_size=10)
        print("Re-embed result:", result)

if __name__ == "__main__":
    asyncio.run(main())