"""EDM v2 — Web Scraper with retry/backoff & robust error handling."""

import random
import time
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup

# ── User‑agent rotation pool ──────────────────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
]


class WebScraperError(Exception):
    """Base exception for scraping failures."""


class WebScraperTimeout(WebScraperError):
    """Raised when a request times out."""


class WebScraperHTTPError(WebScraperError):
    """Raised on non‑2xx responses."""


class WebScraperConnectionError(WebScraperError):
    """Raised on network / DNS failures."""


class WebScraper:
    """Web scraping utility with retry/backoff and error classification.

    Usage::

        scraper = WebScraper("https://example.com/products")
        results = scraper.scrape(".product-card")
    """

    def __init__(
        self,
        url: str,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        max_backoff: int = 30,
    ):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.session = requests.Session()
        self._rotate_ua()

    # ── Internal helpers ──────────────────────────────────────────

    def _rotate_ua(self) -> None:
        """Pick a random User‑Agent for this session."""
        self.session.headers.update({"User-Agent": random.choice(_USER_AGENTS)})
        # Common polite headers
        self.session.headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        self.session.headers.setdefault("Accept-Language", "el-GR,en-US;q=0.7,en;q=0.3")

    def _fetch(self) -> str:
        """Download HTML with retry + exponential backoff.

        Returns:
            Raw HTML string.

        Raises:
            WebScraperTimeout: All retries exhausted due to timeouts.
            WebScraperHTTPError: Non‑2xx status after all retries.
            WebScraperConnectionError: Network-level failure.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(self.url, timeout=self.timeout)
                resp.raise_for_status()
                return resp.text

            except requests.Timeout as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    wait = min(self.backoff_factor ** attempt + random.uniform(0, 1), self.max_backoff)
                    time.sleep(wait)
                    self._rotate_ua()  # rotate UA on retry
                continue

            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                # 429 / 5xx are retryable; 4xx (other than 429) are fatal
                if status in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    wait = min(self.backoff_factor ** attempt + random.uniform(0, 1), self.max_backoff)
                    time.sleep(wait)
                    self._rotate_ua()
                    continue
                raise WebScraperHTTPError(
                    f"HTTP {status} for {self.url}: {exc}"
                ) from exc

            except requests.ConnectionError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    wait = min(self.backoff_factor ** attempt + random.uniform(0, 1), self.max_backoff)
                    time.sleep(wait)
                    continue
                raise WebScraperConnectionError(
                    f"Connection failed for {self.url} after {self.max_retries} retries"
                ) from exc

            except Exception as exc:
                raise WebScraperError(str(exc)) from exc

        # If we exhaust retries on timeouts
        raise WebScraperTimeout(
            f"Request timed out after {self.max_retries} retries (timeout={self.timeout}s)"
        ) from last_exc

    # ── Public API ────────────────────────────────────────────────

    def fetch(self) -> str:
        """Public alias for _fetch — kept for backward compatibility."""
        return self._fetch()

    def parse(self, html: str, selector: str) -> List[Dict[str, Any]]:
        """Parse *html* using CSS *selector* and return product dicts.

        Inside each matched container the scraper looks for child elements:

        - ``.title`` or ``[data-title]``  → product name
        - ``.sku`` or ``[data-sku]``      → supplier code
        - ``.price``                      → numeric price (€/$ stripped)
        - ``.image img``                  → ``src`` attribute

        Missing selectors produce ``None`` for that field — no error.
        """
        soup = BeautifulSoup(html, "html.parser")
        items: List[Dict[str, Any]] = []

        for node in soup.select(selector):
            def txt(css: str, attr: Optional[str] = None) -> Optional[str]:
                el = node.select_one(css)
                if not el:
                    return None
                return el.get(attr) if attr else el.get_text(strip=True)

            title = txt(".title") or txt("[data-title]")
            sku = txt(".sku") or txt("[data-sku]")
            price_raw = txt(".price")
            price: Optional[float] = None
            if price_raw:
                cleaned = price_raw.replace(",", "").replace("€", "").replace("$", "").strip()
                try:
                    price = float(cleaned)
                except ValueError:
                    price = None
            image = txt(".image img", "src")

            items.append({
                "title": title,
                "sku": sku,
                "price": price,
                "image_url": image,
                "source_url": self.url,
            })
        return items

    def scrape(self, selector: str) -> List[Dict[str, Any]]:
        """Convenience: fetch + parse in one call."""
        html = self._fetch()
        return self.parse(html, selector)
