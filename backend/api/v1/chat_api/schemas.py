from pydantic import BaseModel


class CreateConversationBody(BaseModel):
    title: str | None = None
    folder_id: str | None = None


class UpdateConversationBody(BaseModel):
    title: str | None = None
    folder_id: str | None = None


class SendMessageBody(BaseModel):
    text: str
    attachment_ids: list[str] = []
    model: str | None = None
    client_date: str | None = None
    client_time: str | None = None
    client_timezone: str | None = None
    client_location: str | None = None
