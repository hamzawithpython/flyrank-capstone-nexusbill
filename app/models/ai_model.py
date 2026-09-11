from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class AIModel(SQLModel, table=True):
    __tablename__ = "models"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    slug: str = Field(unique=True)
    display_name: str
    input_price_per_1m_micros: int
    cached_input_price_per_1m_micros: int
    output_price_per_1m_micros: int
    reasoning_price_per_1m_micros: int
    is_active: bool = True