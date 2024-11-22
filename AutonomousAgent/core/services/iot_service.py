from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json 
import subprocess 
import time 
from threading import Thread, Lock
from typing import Dict, Any,List


class IoT:
    """
    AWS IoT Core client handler for MQTT communication.

    Manages MQTT connections to AWS IoT Core for multiple IoT things, 
    handling pub/sub operations and device state management.

    Attributes:
        sensors_data: Current sensor data for all things
        feature_topics: Available features/topics for each thing
        iot_thing_topics: Subscribed topics for each thing
        iot_status: Current connection status to IoT devices
        aws_client_status: Current connection status to AWS
    """
    
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
        self.timer_lock:Lock                     = Lock()
        
        
           
        self.context:Dict[str:str] = {"function" : "control IoT devices, check their status, do recommendation,"} # this for the ai context 

        Thread(target=self._setup).start()   
        #self._setup()        
        Thread(target=self._update_system_status).start()  


    def _check_internet(self):
        try:
            subprocess.check_output(["ping", "-c", "1", "8.8.8.8"])   
            return True
        except : 
            return False


    def _setup_aws_client(self):
        """
        Configures and connects AWS IoT MQTT client.
        Sets up connection parameters and credentials.
        """

        # while (not self._check_internet()):
        #     time.sleep(3)
    
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
            print(f"Exception : {e}")
            

    def _aws_on_offline(self):
        """
        Callback handler for AWS client disconnect event.
        Initiates reconnection if not stopped.
        """

        self.aws_client_status = False

        if not self.stop: 
            self._reconnect_to_aws()


    def _clean_aws_client(self):
        """
        Cleans up AWS client connection.
        Unsubscribes from topics and disconnects client.
        """

        try: 
            while not self._check_internet():
                time.sleep(3)

            if self.aws_client_status :
                for iot_thing_name in self._iot_thing_names:
                    self.aws_client.unsubscribe(f"{iot_thing_name}/topics")
                    self.aws_client.unsubscribe(f"{iot_thing_name}/all/data")
                self.aws_client.disconnect()

        except Exception as e:
            print(e)  

        finally : 
            self.aws_client = None 


    def _stop_controller(self):
        """
        Stops IoT controller and cleans up connections.
        """

        self.stop = True 
        try: 
            self._clean_aws_client()
            quit()
        except Exception as e : 
            print(e)         

    def _reconnect_to_aws(self):
        """
        Handles AWS client reconnection.
        Recreates client and resubscribes to topics.
        """

        self._clean_aws_client()
        while not self.aws_client_status:
            self._setup_aws_client()
        
        for iot_thing_name in self._iot_thing_names:
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/data/all")
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/topics")


    def _aws_online(self):
        """
        Callback handler for AWS client connect event.
        """
        self.aws_client_status = True 
        print("Online")
        

    def _subscribe_on_aws(self,client, topic):
        """
        Subscribes to an AWS IoT topic.

        Args:
            client: AWS IoT client instance
            topic: Topic to subscribe to
        """

        try: 
            if self.aws_client_status :
                client.subscribe(topic, 1, self._aws_call_back)
            else : 
                self._reconnect_to_aws()
        except Exception as e: 
                print(e)
     
          

    def _publish_on_aws(self, client, topic, payload, QoS):
        """
        Publishes message to AWS IoT topic.

        Args:
            client: AWS IoT client instance
            topic: Target topic
            payload: Message content
            QoS: Quality of Service level
        """

        if (self.aws_client_status):
            try:
                client.publish(topic = topic, payload = payload, QoS = QoS)
            except Exception as e : 
                print(e)


    def _aws_call_back(self, client, userdata,message):
        """
        Callback handler for AWS messages.
        Updates internal state based on received messages.

        Args:
            client: AWS IoT client instance
            userdata: User data (unused)
            message: Received MQTT message
        """

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
        """
        Updates internal state storage based on topic.

        Args:
            msg: Message payload
            topic: Message topic
        """

        if (topic == f"{topic.split('/')[0]}/data/all"): 
            self.sensors_data[topic.split('/')[0]] = msg
  
        elif (topic == f"{topic.split('/')[0]}/topics"):
            self.feature_topics[topic.split('/')[0]] = msg
    
        else:
            pass 


    def get_state(self, topic):
        """
        Retrieves current state for a specific topic.

        Args:
            topic: Topic name to get state for

        Returns:
            Current state value or None if not found
        """
        with self.timer_lock:
            for thing in self._iot_thing_names : 
                  if topic in self.sensors_data[thing] : 
                      return self.sensors_data[thing][topic] 
      
            return None 


    def set_state(self,topic:str, state:str):
        """
        Sets state for a specific topic.

        Args:
            topic: Topic to update
            state: New state value

        Returns:
            str: "Done" if successful, "Failed" otherwise
        """
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


    def get_iot_status(self):
        """
        Returns current connection status to IoT devices.

        Returns:
            bool: True if connected, False otherwise
        """

        status = False
        with self.timer_lock:
            status = self.iot_status

        return status
        

    def _update_system_status(self):
        """
        Continuously monitors and updates system connection status.
        Runs in separate thread.
        """
        while True : 

            with self.timer_lock : 
                self.iot_status = True if ((time.time() - self.timer) <= 5 ) else False

            time.sleep(4)


    def get_feature_topics(self):
        """
        Retrieves available features/topics for all things.

        Returns:
            dict: Features and topics indexed by thing name
        """
        topics = {}
        with self.timer_lock:
          topics = self.feature_topics
        
        return topics


    def _setup(self): 
        """
        Initializes AWS client and subscribes to all required topics.
        """
        self._setup_aws_client() 

        for iot_thing_name in self._iot_thing_names:
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/data/all")
            self._subscribe_on_aws(self.aws_client,f"{iot_thing_name}/topics")   


    def get_all_data(self):
        """
        Returns current sensor data for all things.

        Returns:
            dict: Sensor data indexed by thing name
        """
        with self.timer_lock :
            return self.sensors_data
