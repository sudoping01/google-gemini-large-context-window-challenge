from .iot_service import IoT 
from .google_service import Google
from .news_service import WebScraper
from threading import Thread, Lock
from queue import Queue
from  typing import Any 
import json, time

from typing import Dict, Any, AnyStr


class Handler:
    """
    Service integration handler managing IoT, Google, and news services.

    Coordinates multiple services and manages their data flows:
    - IoT devices monitoring and control
    - Google services (Gmail, Calendar)
    - Web scraping for news updates

    Attributes:
        iot_object: IoT service connection manager
        google_object: Google APIs service manager
        webscraper: News website scraper
        context: Application context data
        news: Latest scraped news content
        google_data: Latest Google services data
    """


    def __init__(self, config: dict) -> None:
        """
        Initializes handler with provided configuration.

        Args:
            config: Configuration dictionary containing:
                - document_path: Path to RAG document
                - iot: IoT connection settings
                - google: Google API credentials
                - news: News source settings
                - user: User information
        """
        
        self.iot_object: IoT            = None 
        self.google_object: Google      = None
        self.webscraper:WebScraper      = None 
        self.context: Dict              = None 
        self.news:str                   = None 
        self.google_data:Dict[str,Any]  = None

        self.config:Dict[str,Any]       = config
        self.context_lock:Lock          = Lock()
        self.workspace_lock:Lock        = Lock()
        self.update_queue:Queue         = Queue()
        
        self.Document = None 
        self._load_document(path=config["document_path"])
        self._initialize_services()
        self._upload_context()

        Thread(target=self._iot_update_loop, daemon=True).start()
        Thread(target=self._google_update_loop, daemon=True).start()
        Thread(target=self._process_updates, daemon=True).start()
        Thread(target=self._update_news, daemon=True).start()

        del self.config #clean 


    def _initialize_services(self) -> None:
        if "iot" in self.config:
            iotConfig:Dict = self.config["iot"]
            self.iot_object = IoT(
                iot_endpoint=iotConfig["iot_endpoint"],
                iot_thing_names=iotConfig["iot_thing_names"],
                iot_root_cacert_path=iotConfig["iot_root_cacert"],
                iot_device_cert_path=iotConfig["iot_device_cert"],
                iot_private_key_path=iotConfig["iot_private_key"]
            )
        
        if "google" in self.config:
            self.google_object = Google(client_credentials_file_path=self.config["google"]["client_credentials"])

        if "news" in self.config:
            self.webscraper = WebScraper(reference_website=self.config["news"]["reference"])


    def _upload_context(self)->Dict:
        """
        Loads and initializes the context [prompt template].
        Includes user information and IoT system configuration.
        """
        try:
            with open(self.config["base_context"], "r") as file:
                self.context = json.load(file)
                
                if "user" in self.config:
                     UserInfo = self.config["user"]
                     UserInfo["Description"] = self.Document
                     
                     self.context["Context"]["Owner"] = UserInfo

                     time.sleep(5)
                     self.context["IoTSystemAvailable"] = self.iot_object.feature_topics
 
                file.close()

        except Exception as e: 
            print(f"Failed to load the context. Exception: {e}")
            quit()

    def _load_document(self,path)-> AnyStr:
        """
        Loads document from specified path.

        Args:
            path: Path to document file
        """
        with open(path, "r") as file :
            self.Document = file.readlines()
            file.close()


    def merge_dicts(self, dict1:Dict, dict2:Dict)->Dict:
        """
        Merges two dictionaries with special handling for list values.

        Args:
            dict1: First dictionary
            dict2: Second dictionary

        Returns:
            dict: Merged dictionary
        """

        if not dict1:
            return dict2.copy()
        if not dict2:
            return dict1.copy()

        merged:Dict = dict1.copy()
        
        for key, value in dict2.items():
            if key in merged:
                if isinstance(merged[key], list) and isinstance(value, list):
                    merged[key] = merged[key] + value
                elif isinstance(merged[key], list):
                    merged[key].append(value)
                elif isinstance(value, list):
                    merged[key] = [merged[key]] + value
                else:
                    merged[key] = [merged[key], value]
            else:
                merged[key] = value
                
        return merged


    def _iot_update_loop(self)->None:
        """
        Background task for updating IoT system topics and data.
        Runs continuously in separate thread.
        """
        
        while True:

            all_topics = {}

            if self.iot_object:
                for thing in self.iot_object.get_feature_topics():
                    all_topics = self.merge_dicts(all_topics, self.iot_object.get_feature_topics()[thing])

            iot_data = {
                            "Available Topics": all_topics
                           }
            self.update_queue.put(("iot", iot_data))
            time.sleep(4)   

    


    def _google_update_loop(self)->None:
        """
        Background task for updating Google services data.
        Updates mail and calendar data every minute.
        """

        while True:
            if self.google_object :
                time.sleep(60) #1min 
                with self.workspace_lock : 
                    self.google_data = {
                                        "mail": self.google_object.get_emails(max_results=1000),
                                        "calendar": self.google_object.get_events(max_results=1000)
                                      }
               
    def get_worspace_data(self)->Dict:
        with self.workspace_lock : 
            return self.google_data


    def _update_news(self)->AnyStr:
        """
        Background task for updating news content.
        Updates every 10 minutes.
        """
        if self.webscraper : 
            while True : 
                self.news = self.webscraper.get_news()
                time.sleep(600)

    def _process_updates(self)->None:
        """
        Processes queued updates from various services.
        Updates context with new data.
        """

        while True:
            update_type, data = self.update_queue.get()
            with self.context_lock:
                if update_type == "iot":
                    self.context["IoTSystemTopics"] = data       
            self.update_queue.task_done()


    def get_mails(self)->Dict:
        """
        Retrieves latest emails from Gmail.

        Returns:
            dict: Email
        """
        return self.google_data["mail"]
    

    def get_events(self)->Dict:
        """
        Retrieves calendar events.

        Returns:
            dict: Calendar events data
        """
        return self.google_data["calendar"]
    
    
    def get_news(self)->AnyStr:
        """
        Gets latest scraped news content.

        Returns:
            str: News content text
        """
        return self.news
    

    def get_news_source(self)->str:
        """
        Gets news source URL.

        Returns:
            str: Source website URL
        """
        return self.webscraper.source


    def get_context(self)->Dict:
        """
        Gets current (updated) context.

        Returns:
            str: JSON string of context data
        """
        with self.context_lock:
            return json.dumps(self.context.copy())
