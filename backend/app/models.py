from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rightmove_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    link: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    sqm: Mapped[float | None] = mapped_column(Float)
    price: Mapped[int | None] = mapped_column(Integer)
    price_per_sqm: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(Text)
    property_listing_type: Mapped[str | None] = mapped_column(Text)
    preview_data: Mapped[dict | None] = mapped_column(JSONB)
    preview_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    query_url: Mapped[str] = mapped_column(Text, nullable=False)
    search_type: Mapped[str] = mapped_column(Text, nullable=False, default="Sale")
    label: Mapped[str | None] = mapped_column(Text)
    sqm_min: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    sqm_max: Mapped[float] = mapped_column(Float, nullable=False, default=999)
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SearchProperty(Base):
    __tablename__ = "search_properties"

    search_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("searches.id", ondelete="CASCADE"),
        primary_key=True,
    )
    property_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("properties.id", ondelete="CASCADE"),
        primary_key=True,
    )


class PropertyStatus(Base):
    __tablename__ = "property_statuses"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    property_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("properties.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="unreviewed")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
