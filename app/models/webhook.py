from pydantic import BaseModel, ConfigDict, Field


class WAProfile(BaseModel):
    name: str


class WAContact(BaseModel):
    wa_id: str
    profile: WAProfile


class WAText(BaseModel):
    body: str


class WAMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    timestamp: str
    type: str
    text: WAText | None = None


class WAStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: str
    timestamp: str
    recipient_id: str


class WAValue(BaseModel):
    messaging_product: str
    contacts: list[WAContact] = []
    messages: list[WAMessage] = []
    statuses: list[WAStatus] = []


class WAChange(BaseModel):
    value: WAValue
    field: str


class WAEntry(BaseModel):
    id: str
    changes: list[WAChange]


class WAWebhookPayload(BaseModel):
    object: str
    entry: list[WAEntry]
