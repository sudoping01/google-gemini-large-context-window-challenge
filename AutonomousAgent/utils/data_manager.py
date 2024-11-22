
from threading import Thread, Lock
from typing import Dict
from datetime import datetime
import time
from queue import Queue
import json

class DataManager:
    def __init__(self, google_agent):
        self.agent = google_agent
        self.data_queue = Queue()
        
        # Locks for thread safety
        self.iot_lock = Lock()
        self.workspace_lock = Lock()
        self.video_lock = Lock()
        self.state_lock = Lock()  # New lock for state updates
        
        # State storage with timestamp tracking
        self.current_state = {
            "iot": {"data": {}, "last_update": None},
            "workspace": {
                "email": {"data": {}, "last_update": None},
                "calendar": {"data": {}, "last_update": None}
            },
            "video": {"data": {}, "last_update": None}
        }
        
        # Initialize update processes
        self.running = True
        self.threads = []
        self._init_update_processes()

    def _init_update_processes(self):
        """Initialize all update processes"""
        processes = [
            (self._iot_update_process, 1),     # IOT updates every 1 second
            (self._workspace_update_process, 60),  # Workspace updates every 60 seconds
            (self._video_update_process, 5),    # Video updates every 5 seconds
            (self._data_processor, 2)           # Process consolidated data every 2 seconds
        ]
        
        for process, interval in processes:
            thread = UpdateThread(process, interval)
            thread.start()
            self.threads.append(thread)

    def _update_state(self, category: str, subcategory: str = None, data: Dict = None):
        """Thread-safe state update with timestamp"""
        with self.state_lock:
            timestamp = datetime.now().isoformat()
            if subcategory:
                self.current_state[category][subcategory]["data"] = data
                self.current_state[category][subcategory]["last_update"] = timestamp
            else:
                self.current_state[category]["data"] = data
                self.current_state[category]["last_update"] = timestamp

    def _iot_update_process(self):
        """Monitor and update IOT data"""
        try:
            new_iot_data = self.agent.get_iot_data()
            with self.iot_lock:
                if new_iot_data != self.current_state["iot"]["data"]:
                    diff = self._get_dict_diff(self.current_state["iot"]["data"], new_iot_data)
                    if diff:
                        self._update_state("iot", data=new_iot_data)
                        self.data_queue.put(("iot", diff))
                        print(f"New IOT data detected: {json.dumps(diff, indent=2)}")
        except Exception as e:
            print(f"IOT update error: {e}")

    def _workspace_update_process(self):
        """Monitor and update workspace data"""
        try:
            new_workspace_data = self.agent.get_workspace_data()
            
            # Check if we got valid data
            if new_workspace_data is None:
                print("Warning: Workspace data returned None")
                return
                
            with self.workspace_lock:
                # Initialize email and calendar data if they don't exist
                if "email" not in new_workspace_data:
                    new_workspace_data["email"] = {}
                if "calendar" not in new_workspace_data:
                    new_workspace_data["calendar"] = {}
                
                # Check emails
                current_emails = self.current_state["workspace"]["email"].get("data", {})
                new_emails = self._get_dict_diff(
                    current_emails,
                    new_workspace_data["email"]
                )
                if new_emails:
                    self._update_state("workspace", "email", new_workspace_data["email"])
                    self.data_queue.put(("workspace_email", new_emails))
                    print(f"New emails detected: {len(new_emails)} items")
                
                # Check calendar
                current_calendar = self.current_state["workspace"]["calendar"].get("data", {})
                new_calendar = self._get_dict_diff(
                    current_calendar,
                    new_workspace_data["calendar"]
                )
                if new_calendar:
                    self._update_state("workspace", "calendar", new_workspace_data["calendar"])
                    self.data_queue.put(("workspace_calendar", new_calendar))
                    print(f"New calendar events detected: {len(new_calendar)} items")
                    
        except Exception as e:
            print(f"Workspace update error: {e}")
            # Log the current state for debugging
            print(f"Current state: {self.current_state['workspace']}")
            print(f"New workspace data: {new_workspace_data if 'new_workspace_data' in locals() else 'Not received'}")


    def _video_update_process(self):
        """Monitor and update video data"""
        try:
            current_videos = set(self.agent.get_all_mp4_files(self.agent.videos_folder))
            processed_videos = set(self.current_state["video"]["data"].keys())
            
            new_videos = current_videos - processed_videos
            if new_videos:
                with self.video_lock:
                    for video_path in new_videos:
                        video_data = self.agent.analyse_video(video_path)
                        if video_data:
                            self._update_state("video", data={
                                **self.current_state["video"]["data"],
                                **video_data
                            })
                            self.data_queue.put(("video", video_data))
                            print(f"New video analysis: {json.dumps(video_data, indent=2)}")
        except Exception as e:
            print(f"Video update error: {e}")

    def _data_processor(self):
        """Process and consolidate updates from all sources"""
        updates = {}
        update_summary = []
        
        # Process all available updates in the queue
        while not self.data_queue.empty():
            update_type, data = self.data_queue.get()
            if update_type not in updates:
                updates[update_type] = {}
                
            updates[update_type].update(data)
            update_summary.append(f"- {update_type}: {len(data)} new items")
        
        # If we have updates, send them to the model
        if updates:
            print(f"\nProcessing updates:\n" + "\n".join(update_summary))
            
            consolidated_data = {
                "timestamp": datetime.now().isoformat(),
                "updates": updates,
                "current_state": self._get_formatted_state()
            }
            
            # Send to model for processing
            #self._send_to_model(consolidated_data)

    def _get_formatted_state(self) -> Dict:
        """Get a clean version of the current state for the model"""
        with self.state_lock:
            return {
                "iot": {
                    "data": self.current_state["iot"]["data"],
                    "last_update": self.current_state["iot"]["last_update"]
                },
                "workspace": {
                    "email": {
                        "data": self.current_state["workspace"]["email"]["data"],
                        "last_update": self.current_state["workspace"]["email"]["last_update"]
                    },
                    "calendar": {
                        "data": self.current_state["workspace"]["calendar"]["data"],
                        "last_update": self.current_state["workspace"]["calendar"]["last_update"]
                    }
                },
                "video": {
                    "data": self.current_state["video"]["data"],
                    "last_update": self.current_state["video"]["last_update"]
                }
            }

    def _send_to_model(self, data: Dict):
        """Send consolidated updates to the model"""
        context = {
            "timestamp": data["timestamp"],
            "updates": data["updates"],
            "current_state": data["current_state"]
        }
        
        message = f"""
        New system updates detected at {context['timestamp']}.
        
        Recent Updates:
        {json.dumps(context['updates'], indent=2)}
        
        Current System State:
        {json.dumps(context['current_state'], indent=2)}
        
        Please analyze these updates and determine appropriate actions:
        1. Review all changes for security concerns or required responses
        2. Evaluate the significance of each update
        3. If action is needed, use available tools to respond
        4. If no action is needed, continue monitoring
        
        Provide a clear summary of your analysis and any actions taken.
        """
        
        try:
            response = self.agent.invoke(message)
            print(f"\nModel Analysis:")
            print(response)
        except Exception as e:
            print(f"Error sending to model: {e}")

    @staticmethod
    def _get_dict_diff(old_dict: Dict, new_dict: Dict) -> Dict:
        """Calculate the difference between two dictionaries"""
        diff = {}
        for key, value in new_dict.items():
            if key not in old_dict or old_dict[key] != value:
                diff[key] = value
        return diff

    def get_current_state(self) -> Dict:
        """Get the current state of all systems"""
        with self.state_lock:
            return self._get_formatted_state()

    def stop(self):
        """Stop all update processes"""
        print("Stopping data manager...")
        self.running = False
        for thread in self.threads:
            thread.stop()
            thread.join()
        print("Data manager stopped")


class UpdateThread(Thread):
    """Thread class with a stop() method"""
    def __init__(self, target, interval):
        super().__init__()
        self.target = target
        self.interval = interval
        self.stopped = False
        
    def run(self):
        while not self.stopped:
            self.target()
            time.sleep(self.interval)
            
    def stop(self):
        self.stopped = True