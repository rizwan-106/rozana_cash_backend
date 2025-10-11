from pydantic import BaseModel

class UpdateUPIRequest(BaseModel):
    upi_id:str
     