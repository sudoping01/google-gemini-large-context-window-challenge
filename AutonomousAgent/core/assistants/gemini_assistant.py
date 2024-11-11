
from ...interfaces import AssistantInterface
import google.generativeai as genai
from google.generativeai import protos
import google.api_core.exceptions
from typing import Dict, List, Any
import time, json
from ...core.services.handler import ServiceHandler
from ...config.tool_config import IOT_TOOLS, GOOGLE_TOOLS, NEWS_TOOLS
from tenacity import retry, wait_random_exponential, stop_after_attempt


class GoogleAgent(AssistantInterface):
    def __init__(self, service_config:Dict[str,Dict], api_key:str, model_name:str):
        self.service_handler:ServiceHandler = ServiceHandler(service_config=service_config)
        
        self.llm:genai.GenerativeModel = self.config_llm(api_key=api_key, model_name=model_name)


    def config_llm(self, api_key, model_name):
        genai.configure(api_key=api_key)
        tools = self.generate_tools(self.service_handler)
        model  = genai.GenerativeModel(model_name=model_name, tools=tools)
        model = model.start_chat(enable_automatic_function_calling=True)
        context = self.service_handler.get_context()
        model.send_message(context)
        return model 
    

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
        data:Dict[str, Any] = {}

        iot_data = {"IoT_System_Data" : self.service_handler.get_all_iot_data()}
        data.update(iot_data)

        worspace_data = {"Worspace" : 
            self.service_handler.service_handler.google_data
        }

        data.update(worspace_data)

        return data
    
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
        

    def entry_point(self,query): 
        data = self.get_systems_data()


        prompt = f"""
                        Analyse and Decide what to do. If there is not necessary action to do, do nothing

                         Data: {data}, 

                         Video: {query} 

                    """
        response = self.process_user_query(query=prompt)
        return response
    
