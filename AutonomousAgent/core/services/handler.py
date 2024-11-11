from ...interfaces import ServiceInterface
from typing import Dict, Any, List, Optional, Callable
from itertools import islice 
from datetime import datetime

from .service_handler import Handler


class ServiceHandler(ServiceInterface):
    def __init__(self, service_config:Dict[str,Dict[str,str]]):
        super().__init__()
        self.service_handler:Handler = Handler(config=service_config)

        self.FUNCTION_MAP:Dict[str,Callable] = {
                                                    "iot_get_states" : self.iot_get_states, 
                                                    "iot_set_states": self.iot_set_states,
                                                    "get_mails": self.get_mails, 
                                                    "send_mail": self.send_mail, 
                                                    "get_events": self.get_events, 
                                                    "set_event": self.set_event, 
                                                    "get_news": self.get_news
                                                }
        
    def iot_set_states(self, topics:List[str], states:List[str]) -> Dict[str,str]:
       
        response: Dict[str, str] = {}
        if self.service_handler.iot_object.get_iot_status():
            for topic in topics:
                response[topic] = self.service_handler.iot_object.set_state(topic=topic, state=states[topics.index(topic)])
            return response

        return {"Operation" : "Failed", "Raison" : "Iot System is disconnected"}

    

    def iot_get_states(self,topics:List[str]) -> Dict[str,Any]:
        response: Dict[str, Any] = {}
        if self.service_handler.iot_object.get_iot_status():
            for topic in topics:
                response[topic] = self.service_handler.iot_object.get_state(topic=topic)
            return response
        return {"states" : "Unvalable", "Raison" : "IoT System is disconnected"}


    def get_news(self) -> str:
        return {"Source" : self.service_handler.get_news_source(), "News" :self.service_handler.get_news()}
    

    def get_mails(self,id:Optional[int]=None, number_of_mail:Optional[int]=None) -> Dict[str,Any]:
        emails = self.service_handler.get_mails()
        response: Dict[str, Any] = {"Total Mails": len(emails)}

        if not emails:
            response["Emails"] = {"content": "empty (No Mail)"}
            return response

        if number_of_mail : 
                response["Emails"] = dict(islice(emails.items(), min(len(emails), number_of_mail)))
        elif id:
            response["Emails"] = self.service_handler.get_mails()[int(id)]
        else : 
            response["Emails"] = dict(islice(emails.items(), min(len(emails), 5)))

        return response    


    def send_mail(self, to:str, subject:str, body:str) -> Dict[str,Any] :
        action = self.service_handler.google_object.send_email(to=to, subject=subject, body=body)
        return {"mail status": "sent"} if action else {"mail status": "failed"}
    

    def get_events(self) -> Dict[int, Dict[str, str]]:
        return self.service_handler.get_events()


    def set_event(self, summary:str, start_time:str, end_time:str, location:Optional[str] = None, description:Optional[str] = None) -> Dict[str,Any]:

        link = self.service_handler.google_object.set_event(
            summary=summary,
            location=location,
            description=description,
            start_time=datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'),
            end_time=datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        )
        return {"event": "created", "link": link} if link else {"event": "failed"}
    
    def get_all_iot_data(self):
        return self.service_handler.iot_object.get_all_data()
    

    def get_context(self):
        return self.service_handler.get_context()
    

    def invoke(self,function_name:str, params:Dict[str,Any])-> Dict[str,Any]:
        if function_name in self.FUNCTION_MAP :
            return self.FUNCTION_MAP[function_name](**params)
        return {"Error" : f" {function_name} does't not find"}


