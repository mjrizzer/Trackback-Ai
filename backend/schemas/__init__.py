from typing import Literal
from pydantic import BaseModel, Field, field_validator, EmailStr


class InputModel(BaseModel):
    model_config = {'extra': 'forbid'}

    @field_validator('*', mode='before')
    @classmethod
    def trim_text(cls, value, info):
        if (
            isinstance(value, str)
            and info.field_name in ('password', 'current_password', 'new_password')
            and not value.strip()
        ):
            raise ValueError('Password cannot consist only of whitespace')
        if isinstance(value, str) and info.field_name not in (
            'password',
            'current_password',
            'new_password',
        ):
            return value.strip()
        return value


class Login(InputModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Register(Login):
    password: str = Field(min_length=10, max_length=128)
    name: str = Field(min_length=2, max_length=100)
    organization: str = Field(min_length=2, max_length=200)


class IncidentInput(InputModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=8000)
    category: Literal['contamination', 'quality', 'shipment', 'records', 'other']
    severity: Literal['low', 'medium', 'high', 'critical']
    lot_id: int | None = Field(default=None, gt=0)
    batch_id: int | None = Field(default=None, gt=0)


class Decision(InputModel):
    decision: Literal['approved', 'rejected', 'revision_requested']
    comment: str = Field(min_length=3, max_length=2000)
    verification_confirmed: bool = False


class AgentOutput(BaseModel):
    summary: str = Field(min_length=10, max_length=6000)
    evidence_references: list[str] = Field(min_length=1, max_length=200)
    uncertainties: list[str] = Field(default_factory=list, max_length=50)


class ToolArguments(BaseModel):
    model_config = {'extra': 'forbid'}
    query: str = Field(default='', max_length=200)


class ProposalInput(InputModel):
    investigation_id: int
    kind: Literal[
        'inventory_hold',
        'inventory_release',
        'supplier_escalation',
        'customer_notification',
        'corrective_assignment',
    ]
    justification: str = Field(min_length=10, max_length=4000)


class UserInput(Login):
    password: str = Field(min_length=10, max_length=128)
    name: str = Field(min_length=2, max_length=100)
    role: Literal['admin', 'reviewer', 'analyst']


class RoleInput(InputModel):
    role: Literal['admin', 'reviewer', 'analyst']


class RevisionInput(InputModel):
    justification: str = Field(min_length=10, max_length=4000)


class PasswordInput(InputModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
