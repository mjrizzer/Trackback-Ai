from pydantic import Field
from typing import Literal
from backend.schemas import InputModel


class SupplierInput(InputModel):
    name: str = Field(min_length=2, max_length=200)
    status: Literal['approved', 'watchlist'] = 'approved'


class LotInput(InputModel):
    code: str = Field(pattern=r'^[A-Z0-9][A-Z0-9_-]{2,59}$')
    supplier_id: int = Field(gt=0)
    material: str = Field(min_length=2, max_length=100)
    quantity: float = Field(gt=0, le=100000000, allow_inf_nan=False)


class MaterialUsageInput(InputModel):
    lot_id: int = Field(gt=0)
    quantity: float = Field(gt=0, le=100000000, allow_inf_nan=False)


class BatchInput(InputModel):
    code: str = Field(pattern=r'^[A-Z0-9][A-Z0-9_-]{2,59}$')
    product: str = Field(min_length=2, max_length=100)
    quantity: int = Field(gt=0, le=100000000)
    materials: list[MaterialUsageInput] = Field(min_length=1, max_length=20)


class CustomerInput(InputModel):
    name: str = Field(min_length=2, max_length=200)
    region: str = Field(min_length=2, max_length=100)


class ShipmentItemInput(InputModel):
    batch_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100000000)


class ShipmentInput(InputModel):
    code: str = Field(pattern=r'^[A-Z0-9][A-Z0-9_-]{2,59}$')
    customer_id: int = Field(gt=0)
    items: list[ShipmentItemInput] = Field(min_length=1, max_length=20)


class InspectionInput(InputModel):
    batch_id: int = Field(gt=0)
    document_id: int = Field(gt=0)
    test: str = Field(min_length=2, max_length=100)
    result: Literal['pass', 'fail']
