from pydantic import BaseModel, RootModel
from rid_lib.ext import Event
from rid_lib.ext.pydantic_adapter import RIDField

    
EventArrayModel = RootModel[list[Event]]

class PollEvents(BaseModel):
    rid: RIDField
    limit: int = 0
    
class RetrieveRids(BaseModel):
    contexts: list[str] = []
    
class RetrieveManifests(BaseModel):
    contexts: list[str] = []
    rids: list[str] = []
    
class RetrieveBundles(BaseModel):
    rids: list[RIDField]
    
