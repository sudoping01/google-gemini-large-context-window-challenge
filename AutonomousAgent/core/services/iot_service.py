from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json 
import subprocess 
import time 
from threading import Thread, Lock
from typing import Dict, Any,List


class IoT:
    def __init__( self,
                  iot_endpoint:str,
                  iot_thing_names:list,
                  iot_root_cacert_path:str,
                  iot_device_cert_path:str,
                  iot_private_key_path:str,
               ):
        
        self._iot_endpoint:str         = iot_endpoint
        self._iot_thing_names:List     = iot_thing_names
        self._aws_root_ca_path:str     = iot_root_cacert_path
        self._aws_device_cert_path:str = iot_device_cert_path
        self._aws_private_key_path:str = iot_private_key_path 
        
        self.sensors_data:Dict[str:Any]     = {}
        self.feature_topics:Dict[str:Any]   = {}
        self.iot_thing_topics:Dict[str:Any] = {}   

        self.iot_status:bool                = False
        self.aws_client_status:bool         = False 
        self.stop:bool                      = False 
        self.timer:float                    = time.time()
        self.timer_lock = Lock()
           
        self.context:Dict[str:Any] = {"function" : "control IoT devices, check their status, do recommendation,"}

        Thread(target=self._setup).start()           
        Thread(target=self._update_system_status).start()  


    def _check_internet(self):
        try:
            subprocess.check_output(["ping", "-c", "1", "8.8.8.8"])   
            return True
        except : 
            return False


    def _setup_aws_client(self):

        while (not self._check_internet()):
            time.sleep(3)

        try : 
            self.aws_client = AWSIoTMQTTClient(f"Iot_Action_client{'_'.join(self._iot_thing_names)}_{time.time()}") 
            self.aws_client.configureEndpoint(self._iot_endpoint, 8883)
            self.aws_client.configureCredentials(self._aws_root_ca_path, self._aws_private_key_path, self._aws_device_cert_path)
            self.aws_client.configureOfflinePublishQueueing(-1)  
            self.aws_client.configureDrainingFrequency(2)  
            self.aws_client.configureConnectDisconnectTimeout(10)  
            self.aws_client.configureMQTTOperationTimeout(5)  
            self.aws_client.onOffline = self._aws_on_offline
            self.aws_client.onOnline  = self._aws_online
            self.aws_client.connect() 
        except Exception as e :
            pass 
            

    def _aws_on_offline(self):
        self.aws_client_status = False

        if not self.stop: 
            self._reconnect_to_aws()


    def _clean_aws_client(self):
        try: 
            while not self._check_internet():
                time.sleep(3)

            if self.aws_client_status :
                for iot_thing_name in self._iot_thing_names:
                    self.aws_client.unsubscribe(f"{iot_thing_name}/topics")
                    self.aws_client.unsubscribe(f"{iot_thing_name}/all/data")
                self.aws_client.disconnect()

        except Exception as e:
            pass  

        finally : 
            self.aws_client = None 


    def _stop_controller(self):
        self.stop = True 
        try: 
            self._clean_aws_client()
            quit()
        except Exception as e : 
            pass 
         

    def _reconnect_to_aws(self):
        self._clean_aws_client()
        while not self.aws_client_status:
            self._setup_aws_client()
        
        for iot_thing_name in self._iot_thing_names:
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/data/all")
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/topics")


    def _aws_online(self):
        self.aws_client_status = True 
        

    def _subscribe_on_aws(self,client, topic):
        try: 
            if self.aws_client_status :
                client.subscribe(topic, 1, self._aws_call_back)
            else : 
                self._reconnect_to_aws()
        except Exception as e: 
                pass 
     
          

    def _publish_on_aws(self, client, topic, payload, QoS):
        if (self.aws_client_status):
            try:
                client.publish(topic = topic, payload = payload, QoS = QoS)
            except Exception as e : 
                pass 


    def _aws_call_back(self, client, userdata,message):

        with self.timer_lock: 
            self.timer = time.time()

        try:
        
            if message.topic.split(("/"))[-1] == "topics":
                topics = list(json.loads(message.payload).values())
                self.iot_thing_topics[message.topic.split("/")[0]] = [topic for subtopics in topics for topic in subtopics ] 

            self._update_states(msg=json.loads(message.payload) , topic=message.topic) 

        except Exception as e :
            print(f"Exception {e}")
            

    def _update_states(self,msg, topic):
        if (topic == f"{topic.split('/')[0]}/data/all"): 
            self.sensors_data[topic.split('/')[0]] = msg
  
        elif (topic == f"{topic.split('/')[0]}/topics"):
            self.feature_topics[topic.split('/')[0]] = msg
    
        else:
            pass 


    def get_state(self, topic):
       for thing in self._iot_thing_names : 
            if topic in self.sensors_data[thing] : 
                return self.sensors_data[thing][topic] 
 
       return None 


    def set_state(self,topic:str, state:str):
        try :
            msg = {
                    "type" : "CMD", 
                    "topic_names" : [topic],
                    "states" : [state]
                  }
            msg = json.dumps(msg)
            check = False 
            for iot_thing_name in self._iot_thing_names: 
                if topic in self.iot_thing_topics[iot_thing_name] :
                    self._publish_on_aws(client  = self.aws_client,
                                        topic   = f"{iot_thing_name}/sub", 
                                        payload = msg, 
                                        QoS     = 0
                                        )
                    check=True 
            return "Done" if  check else "Failed"
        except Exception as e:
            return "Failed"
        

    def _update_system_status(self):
        while True : 

            with self.timer_lock : 
                self.iot_status = True if ((time.time() - self.timer) <= 5 ) else False

            time.sleep(4)


    def get_iot_status(self):
        status = False
        with self.timer_lock:
            status = self.iot_status

        return status
    
    def get_all_data(self):
        return self.sensors_data


    def _setup(self): 
        self._setup_aws_client() 

        for iot_thing_name in self._iot_thing_names:
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/data/all")
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/topics")   

