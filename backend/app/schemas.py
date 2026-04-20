from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

BucketStatus = Literal["unreviewed", "shortlisted", "rejected"]
SearchStatus = Literal["pending", "scraping", "complete", "failed"]
ListingType = Literal["Sale", "Rental"]


class SearchCreate(BaseModel):
    query_url: str
    search_type: ListingType = "Sale"
    label: str | None = None
    sqm_min: float = 0
    sqm_max: float = 999
    max_pages: int = Field(default=10, ge=1, le=42)


class SearchOut(BaseModel):
    id: int
    query_url: str
    search_type: str
    label: str | None
    sqm_min: float
    sqm_max: float
    max_pages: int
    status: str
    progress: int
    error_message: str | None
    total_found: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyOut(BaseModel):
    id: int
    rightmove_id: int
    link: str
    full_url: str
    sqm: float | None
    price: int | None
    price_per_sqm: float | None
    address: str | None
    property_listing_type: str | None
    status: BucketStatus


class CountsOut(BaseModel):
    unreviewed: int
    shortlisted: int
    rejected: int


class StatusUpdate(BaseModel):
    status: BucketStatus


class PreviewOut(BaseModel):
    id: int
    url: str
    address: str
    postcode: str
    price: str
    bedrooms: int | None = None
    bathrooms: int | None = None
    property_type: str | None = None
    tenure: str | None = None
    sqm: float | None = None
    price_per_sqm: float | None = None
    description: str
    features: list[str]
    images: list[dict[str, Any]]
    floorplans: list[str]
    stations: list[dict[str, Any]]
    agent: str | None = None
