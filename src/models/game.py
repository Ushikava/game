from pydantic import BaseModel


class GiveRequest(BaseModel):
    sender: str
    receiver: str
    plant: str
