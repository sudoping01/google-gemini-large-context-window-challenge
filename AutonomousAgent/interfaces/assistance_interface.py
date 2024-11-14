from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class AssistantInterface(ABC):

    @abstractmethod
    def config_llm(self, api_key, model_name) -> Any:
        pass

    @abstractmethod
    def generate_tools(self, service_handler: Any) -> List[Dict|Any]:
        pass  
    

    @abstractmethod
    def process_user_query(self,query:str)-> str:
        pass 


    @abstractmethod
    def speech_to_text(self,audio_path)-> str:
        pass 

    @abstractmethod
    def text_to_speech(self,text:str) -> Any : 
        pass 
    
    @abstractmethod
    def chat_completion(self, query:Optional[str] = None , relevant_context:Optional[str]=None, tools:Optional[List]=None) -> str:
        pass 

    @abstractmethod
    def handle_function_calling(self,function_name, params:Dict[str, Any])-> Dict[str,Any]:
        return self.service_handler.invoke(function_name=function_name, params=params)
    

