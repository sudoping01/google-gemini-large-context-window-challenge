from abc import abstractmethod, ABC
from typing import List, Dict, Optional, Any

class ServiceInterface(ABC):
    @abstractmethod
    def iot_get_states(self,topics:List[str]) -> Dict[str,  str]:
        pass 

    @abstractmethod
    def iot_set_states(self, topics:List[str], states:List[str]) -> Dict[str, int]:
        pass 

    @abstractmethod
    def get_mails(self,id:Optional[int]=None, number_of_mail:Optional[int]=None) -> Dict[str,Any]:
        pass 

    @abstractmethod
    def send_mail(self, to:str, subject:str, body:str) -> Dict[str,Any] :
        pass 

    @abstractmethod
    def get_events(self) -> Dict[Any,Any] :
        pass 

    @abstractmethod
    def set_event(self, summary:str, start_time:str, end_time:str, location:Optional[str] = None, description:Optional[str] = None) -> Dict[str,Any]:
        pass 

    @abstractmethod
    def get_context(self)->Dict:
        pass 
    
    @abstractmethod
    def invoke(self,function_name:str, params:Dict)-> Dict[str,Any]:
        pass 
