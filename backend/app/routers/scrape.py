from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from ..services.web_scraper import (
    WebScraper,
    WebScraperError,
    WebScraperTimeout,
    WebScraperHTTPError,
    WebScraperConnectionError,
)

router = APIRouter(prefix="/api/v1/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    url: HttpUrl
    selector: str


@router.post("/", response_model=list)
async def scrape(request: ScrapeRequest):
    try:
        scraper = WebScraper(str(request.url))
        results = scraper.scrape(request.selector)
        return results
    except WebScraperTimeout:
        raise HTTPException(
            status_code=504,
            detail="Το αίτημα scraping έληξε (timeout) μετά από πολλαπλές προσπάθειες. "
                   "Δοκίμασε μικρότερο URL ή αύξησε το timeout.",
        )
    except WebScraperHTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Ο server προορισμού επέστρεψε σφάλμα: {e}",
        )
    except WebScraperConnectionError:
        raise HTTPException(
            status_code=502,
            detail="Αδυναμία σύνδεσης στον server προορισμού. Έλεγξε τη διεύθυνση URL ή τη σύνδεση δικτύου.",
        )
    except WebScraperError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Μη αναμενόμενο σφάλμα scraping: {e}")
