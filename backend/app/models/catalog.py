from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Auction(Base):
    __tablename__ = "auctions"
    __table_args__ = (UniqueConstraint("source_id", "catalog_id", name="uq_auctions_source_catalog"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(255), index=True)
    catalog_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    region: Mapped[str] = mapped_column(String(64))
    tax_label: Mapped[str] = mapped_column(String(16))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    buyer_premium_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    per_item_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cc_processing_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    items: Mapped[list[Item]] = relationship(back_populates="auction")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("auction_id", "item_id", name="uq_items_auction_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    auction_id: Mapped[int] = mapped_column(
        ForeignKey("auctions.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[str] = mapped_column(String(255))
    raw_title: Mapped[str] = mapped_column(String(1000))
    current_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )

    auction: Mapped[Auction] = relationship(back_populates="items")