"""CBSA (Core Based Statistical Area) metadata model."""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


class Cbsa(Base):
    __tablename__ = "cbsa"

    cbsa_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    koppen: Mapped[str | None] = mapped_column(String(16), nullable=True)
