from typing import Dict, Any, List, Optional, Callable
from itertools import islice 
from datetime import datetime

from .service_handler import Handler


class ServiceHandler:
    """
    High-level service interface for IoT, Google services and news handling.

    Provides unified interface for interacting with multiple services:
    - IoT device control and monitoring
    - Email management (Gmail)
    - Calendar events management
    - News retrieval

    Attributes:
        service_handler: Core service handler instance
        FUNCTION_MAP: Mapping of function names to their implementations
    """

    def __init__(self, service_config:Dict[str,Dict[str,str]]):
        """
        Initializes service handler with configuration.

        Args:
            service_config: Configuration for all services
        """

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
        """
        Sets states for multiple IoT topics.

        Args:
            topics: List of topics to update
            states: Corresponding state values

        Returns:
            dict: Operation status for each topic
        """
       
        response: Dict[str, str] = {}
        if self.service_handler.iot_object.get_iot_status():
            for topic in topics:
                response[topic] = self.service_handler.iot_object.set_state(topic=topic, state=states[topics.index(topic)])
            return response

        return {"Operation" : "Failed", "Raison" : "Iot System is disconnected"}

    

    def iot_get_states(self,topics:List[str]) -> Dict[str,Any]:
        """
        Retrieves states for multiple IoT topics.

        Args:
            topics: List of topics to query

        Returns:
            dict: Current states or error message
        """

        response: Dict[str, Any] = {}
        if self.service_handler.iot_object.get_iot_status():
            for topic in topics:
                response[topic] = self.service_handler.iot_object.get_state(topic=topic)
            return response
        return {"states" : "Unvalable", "Raison" : "IoT System is disconnected"}


    def get_news(self) -> str:
        """
        Retrieves latest news content.

        Returns:
            dict: News source and content
        """
        return {"Source" : self.service_handler.get_news_source(), "News" :self.service_handler.get_news()}
    

    def get_mails(self,id:Optional[int]=None, number_of_mail:Optional[int]=None) -> Dict[str,Any]:
        """
        Retrieves emails with optional filtering.

        Args:
            id: Specific email ID to retrieve
            number_of_mail: Maximum number of emails to return

        Returns:
            dict: Email data and total count
        """

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
        """
        Sends an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email content

        Returns:
            dict: Send status
        """

        action = self.service_handler.google_object.send_email(to=to, subject=subject, body=body)
        return {"mail status": "sent"} if action else {"mail status": "failed"}
    

    def get_events(self) -> Dict[int, Dict[str, str]]:
        """
        Retrieves calendar events.

        Returns:
            dict: Calendar events indexed by number
        """
        return self.service_handler.get_events()


    def set_event(self, summary:str, start_time:str, end_time:str, location:Optional[str] = None, description:Optional[str] = None) -> Dict[str,Any]:
        """
        Creates a calendar event.

        Args:
            summary: Event title
            start_time: Start time (format: 'YYYY-MM-DD HH:MM:SS')
            end_time: End time (format: 'YYYY-MM-DD HH:MM:SS')
            location: Optional event location
            description: Optional event description

        Returns:
            dict: Event creation status and link
        """
        
        link = self.service_handler.google_object.set_event(
            summary=summary,
            location=location,
            description=description,
            start_time=datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'),
            end_time=datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        )
        return {"event": "created", "link": link} if link else {"event": "failed"}
    

    def get_all_iot_data(self):
        """
        Retrieves all IoT device data.

        Returns:
            dict: Complete IoT system data
        """

        return self.service_handler.iot_object.get_all_data()
    

    def get_all_workspace_data(self):
        """
        Retrieves all Google Workspace data.

        Returns:
            dict: Combined email and calendar data
        """

        return self.service_handler.get_worspace_data()
    
    

    def get_context(self):
        """
        Retrieves current service context.

        Returns:
            str: JSON string of context data
        """

        return self.service_handler.get_context()
    

    def invoke(self,function_name:str, params:Dict[str,Any])-> Dict[str,Any]:
        """
        Dynamically invokes a service function by name.

        Args:
            function_name: Name of the function to call
            params: Parameters to pass to the function

        Returns:
            dict: Function result or error message
        """

        if function_name in self.FUNCTION_MAP :
            return self.FUNCTION_MAP[function_name](**params)
        return {"Error" : f" {function_name} does't not find"}


