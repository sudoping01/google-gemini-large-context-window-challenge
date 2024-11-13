from .iot_service import IoT 
from .google_service import Google
from .news_service import WebScraper
from threading import Thread, Lock
from queue import Queue
from  typing import Any 
import json, time

from ...interfaces.service_interface import ServiceInterface
from typing import Dict, Any, List, Optional, Callable
from itertools import islice 
from datetime import datetime

class Handler:
    def __init__(self, config: dict) -> None:
        self.iot_object: IoT            = None 
        self.google_object: Google      = None
        self.webscraper:WebScraper      = None 
        self.context: dict              = None 
        self.news:str                   = None 
        self.google_data:dict[str:Any]  = None

        self.config:dict[str:Any]       = config
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


    def _initialize_services(self):
        if "iot" in self.config:
            iotConfig = self.config["iot"]
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


    def _upload_context(self):
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

    def _load_document(self,path):
        with open(path, "r") as file :
            self.Document = file.readlines()
            file.close()


    def _iot_update_loop(self):
        while True:
            if self.iot_object:
                if self.iot_object.get_iot_status():
                    self.update_queue.put(("iot", self.iot_object.feature_topics))
            time.sleep(3)  


    def _google_update_loop(self):
        while True:
            if self.google_object :
                time.sleep(60) #1min 
                with self.workspace_lock : 
                    self.google_data = {
                                        "mail": self.google_object.get_emails(max_results=1000),
                                        "calendar": self.google_object.get_events(max_results=1000)
                                      }
               
    def get_worspace_data(self):
        with self.workspace_lock : 
            return self.google_data


    def _update_news(self):
        if self.webscraper : 
            while True : 
                self.news = self.webscraper.get_news()
                time.sleep(600)

    def _process_updates(self):
        while True:
            update_type, data = self.update_queue.get()
            with self.context_lock:
                if update_type == "iot":
                    self.context["IoTSystemTopics"] = data       
            self.update_queue.task_done()

    def get_mails(self):
        return self.google_data["mail"]
    
    def get_events(self):
        return self.google_data["calendar"]
    
    def get_news(self):
        return self.news
    
    def get_news_source(self):
        return self.webscraper.source

    def get_context(self):
        with self.context_lock:
            return json.dumps(self.context.copy())
