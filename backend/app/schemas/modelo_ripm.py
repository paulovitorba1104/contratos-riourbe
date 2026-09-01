import uuid

from pydantic import BaseModel, Field


class ModeloRipmCriar(BaseModel):
    codigo: str = Field(..., max_length=20)
    nome: str = Field(..., max_length=255)
    itens_checklist: list[str] | None = None
    ativo: bool = True


class ModeloRipmSaida(BaseModel):
    id: uuid.UUID
    codigo: str
    nome: str
    itens_checklist: list[str] | None
    ativo: bool

    model_config = {"from_attributes": True}
