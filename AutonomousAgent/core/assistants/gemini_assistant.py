from ...interfaces import AssistantInterface
import google.generativeai as genai
from google.generativeai import protos
import google.api_core.exceptions
from typing import Dict, List, Any
import time, json, os
from pathlib import Path
from datetime import date, datetime
from threading import Thread, Lock


from ...core.services.handler import ServiceHandler
from ...config.tool_config import IOT_TOOLS, GOOGLE_TOOLS, NEWS_TOOLS
from tenacity import retry, wait_random_exponential, stop_after_attempt


class GoogleAgent(AssistantInterface):
    def __init__(self, service_config:Dict[str,Dict], api_key:str, model_name:str, videos_folder:str):
        print("Init Agent ")
        self.service_handler:ServiceHandler = ServiceHandler(service_config=service_config)
        time.sleep(60) # make sure to get all system data
        self.video_analyser: genai.GenerativeModel = None
        self.llm:genai.GenerativeModel = self.config_llm(api_key=api_key, model_name=model_name)
        self.video_flux_description:List[Dict]= []
        self.video_file_already_analyse:List[str] = []  
        self.videos_folder = videos_folder
        self.videos_path:List[str] = []

        self.video_data_lock        = Lock()
        self.iot_data_lock          = Lock()
        self.workspace_lock         = Lock()

        self.iot_data:Dict          = {}
        self.workspace_data:Dict    = {}
        self.video_flux_data:Dict   = {}

        self._update_process()
        self.run_deamon()


    def config_llm(self, api_key, model_name):
        genai.configure(api_key=api_key)
        tools = self.generate_tools(self.service_handler)
        model = genai.GenerativeModel(model_name=model_name, tools=tools)  
        self.video_analyser = genai.GenerativeModel(model_name=model_name)  
        model = model.start_chat(enable_automatic_function_calling=True)
        context = self.service_handler.get_context()
        model.send_message(context)
        return model 
    

    def get_all_mp4_files(self,parent_folder):
        mp4_files = []
        for root, dirs, files in os.walk(parent_folder):
            for file in files:
                if file.endswith('.mp4'):
                    full_path = os.path.join(root, file)
                    mp4_files.append(full_path)
        return mp4_files
    

    def _update_process(self):
        
        self.iot_data = self.service_handler.get_all_iot_data()
        self.workspace_data = self.service_handler.get_all_workspace_data()
        videos = self.get_all_mp4_files(parent_folder=self.videos_folder)
        for video in videos :
            if not video in self.video_file_already_analyse: 
                descript = self.analyse_video(path=video)
                if descript:
                    with self.video_data_lock :
                        self.video_flux_data.update(descript)
                time.sleep(1) # being kind to the server 
        time.sleep(2)


    def analyse_video(self,path: str, timeout: int = 600):
            video_path = Path(path)
            print(f"Analysing {video_path}")
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found at {path}")
        
            context = """
                        Analyse carefully this video :
                        - Detect any suspicious activities that may suggest theft or burglary.
                        - Identify humain presence or absence
                        - Act like as a security agent
                        - Your response should be short as possible, clear, concise and should contain only the result of your analyse.
                        - Note that you ouput is for an llm, then make sure it will be avaible to process it.
                        - Your ouput should contain anything else, only your analyse resultat. No additional information just your analyse result.
                    """
            try:
                
                video_file = genai.upload_file(path=str(video_path))
                start_time = time.time()
                while video_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        genai.delete_file(video_file.name)  
                        raise TimeoutError("Video processing exceeded timeout limit")
                        
                    print('.', end='', flush=True)
                    video_file = genai.get_file(video_file.name)
                
                if video_file.state.name == "FAILED":
                    raise ValueError(f"Video processing failed: {video_file.state.message}")
                
                
                response = self.video_analyser.generate_content(
                    [video_file, context],
                    request_options={"timeout": timeout}
                )
                

                try:
                    genai.delete_file(video_file.name)
                except Exception as e:
                    print(f"Warning: Failed to delete temporary file: {e}")
                
                description = {
                    "Date": date.today().isoformat(),
                    "Time": datetime.now().isoformat(),
                    "Video Description": response.text,
                    "Analysis Duration": f"{time.time() - start_time:.2f} seconds"
                }

                
                return description
                
            except Exception as e:
                try:
                    genai.delete_file(video_file.name)
                except:
                    pass
                
            return None 
    

    def run_deamon(self): # background autononous agent
        while True: 
            data = self.get_systems_data()
            print("Print getting inference")
            with open("test_data.json", "w") as file : 
                json.dump(data, file)
                file.close()

            content = f"""
                        Analyse and Decide what to do. if there is an action to do, use the necessary tool to perform that action. If there is no necessary action to do, do not do anything.

                        Data : {data}
                        """
            

            
            response = self.invoke(query=content)
            print(response)

            time.sleep(120) #2min
        

           
    def generate_tools(self, service_handler) -> list[protos.Tool]:

        TYPE_MAP = {
                    "object" : protos.Type.OBJECT, 
                    "integer" : protos.Type.INTEGER, 
                    "array": protos.Type.ARRAY, 
                    "string" : protos.Type.STRING, 
                 }
        
        
        
        TOOLS:List = []
        tools: List[protos.Tool] = []
        

        if service_handler.service_handler.iot_object:
            TOOLS = TOOLS+IOT_TOOLS

        if service_handler.service_handler.google_object:
            TOOLS = TOOLS + GOOGLE_TOOLS

        if service_handler.service_handler.webscraper : 
            TOOLS = TOOLS + NEWS_TOOLS

        if len(TOOLS) > 0:
            for tool in TOOLS:
                if not tool.parameters:
                    tools.append(protos.Tool(function_declarations=[
                        protos.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description
                        )
                    ]))
                    continue
                properties = {}
                for param in tool.parameters:
                    if param.type == "array":
                        properties[param.name] = protos.Schema(
                            type=TYPE_MAP[param.type],
                            description=param.description,
                            items=protos.Schema(
                                type=TYPE_MAP[param.items.type],
                                enum=param.items.enum if param.items.enum else None
                            )
                        )
                    else:
                        properties[param.name] = protos.Schema(
                            type=TYPE_MAP[param.type],
                            description=param.description
                        )
                tool_declaration = protos.Tool(function_declarations=[
                    protos.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=protos.Schema(
                            type=protos.Type.OBJECT,
                            properties=properties,
                            required=tool.required
                        ) if properties else None
                    )
                ])
                tools.append(tool_declaration)

            return tools
        
        return []
    

    def get_systems_data(self):
        return {
                "Iot" : self.iot_data,
                "Workspace" : self.workspace_data,
                "Video Flux Description" : self.video_flux_data
            }

        
        
    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def text_to_speech(self, text):
        return super().text_to_speech(text)
    
    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def speech_to_text(self, audio_path):
        return super().speech_to_text(audio_path)
    
    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def chat_completion(self, query, relevant_context):
        return super().chat_completion(query, relevant_context)
    
    def handle_function_calling(self, function_name, params):
        return super().handle_function_calling(function_name, params)
    

    def process_user_query(self, query: str) -> str:        
        try:
            start = time.time()
            response = self.llm.send_message(query)
            print(f"Request to Gemini: {time.time() - start}")
            
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.function_call:
                            function_name = part.function_call.name
                    
                            function_args = {}
                            
                            if part.function_call.args:
                                function_args = dict(part.function_call.args)
                            
                            print(f"Function name: {function_name}")
                            print(f"Function arguments: {function_args}")
                            
                            
                            start = time.time()
                            try:
                                function_response =  True #self.handle_function_calling(function_name, function_args)
                            except Exception as e:
                                function_response = {"Error": f"Exception in function execution: {str(e)}"}
                            
                            print(f"Function running time: {time.time() - start}")
                            
                            start = time.time()
                            try:
                                final_response = self.llm.send_message(json.dumps(function_response))
                                print(f"Second request to Gemini: {time.time() - start}")
                                response_content = final_response.text
                            except google.api_core.exceptions.GoogleAPIError as e:
                                response_content = f"Error processing function result: {str(e)}"
                        else:
                            response_content = part.text
                else:
                    response_content = "No content in the response."
            else:
                response_content = "No response generated."
        
        except google.api_core.exceptions.GoogleAPIError as e:
            response_content = f"An error occurred while processing your request: {str(e)}. Please try again later."
        except Exception as e:
            response_content = f"An unexpected error occurred: {str(e)}. Please try again later."
        
        try:
            return json.dumps(json.loads(response_content.strip('`').lstrip('json\n')))
        except json.JSONDecodeError:
            return response_content
        

        

    def invoke(self,query=None): 
        response = self.process_user_query(query=query)
        return response
    
