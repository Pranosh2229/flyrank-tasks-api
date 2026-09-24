from pydantic import BaseModel, Field, HttpUrl


class BookRecord(BaseModel):
    # --- extracted fields ---
    title: str
    price_gbp: float = Field(gt=0)
    availability_text: str
    in_stock: bool
    rating: int = Field(ge=1, le=5)
    upc: str
    category: str
    image_url: HttpUrl

    # --- identity / provenance (not scraped content, added by the pipeline) ---
    canonical_url: HttpUrl  # dedup key
    source_page: HttpUrl    # catalogue page this book was discovered on
    fetched_at: str         # ISO 8601 UTC timestamp of the detail-page fetch
