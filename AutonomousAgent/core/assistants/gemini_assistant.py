import google.generativeai as genai
from google.generativeai import protos
import google.api_core.exceptions
from typing import Dict, List, Any, Optional
import time
import json
import os
from pathlib import Path
from datetime import date, datetime
from tenacity import retry, wait_random_exponential, stop_after_attempt

from ...core.services.handler import ServiceHandler
from ...config import IOT_TOOLS, GOOGLE_TOOLS, NEWS_TOOLS
from ...utils import DataManager


class GoogleAgent:
    def __init__(self, 
                 service_config: Dict[str, Dict], 
                 api_key: str, 
                 model_name: str, 
                 videos_folder: str) -> None:
        """
        Initialize the Google Agent with necessary configurations and services.
        
        Args:
            service_config: Configuration for various services
            api_key: Google API key
            model_name: Name of the model to use
            videos_folder: Path to folder containing videos
        """
        print("Initializing Google Agent")
        
        # Service initialization
        self.service_handler = ServiceHandler(service_config=service_config)
        
        # Model configuration
        self.llm, self.video_analyser = self._config_models(api_key=api_key, 
                                                           model_name=model_name)
        
        # Video processing configuration
        self.videos_folder = Path(videos_folder)
        self.videos_folder.mkdir(parents=True, exist_ok=True)
        
        # Initialize the DataManager
        self.data_manager = DataManager(self)
        
    def _config_models(self, api_key: str, model_name: str):
        """Configure and initialize the models."""
        genai.configure(api_key=api_key)
        
        # Configure main LLM with tools
        tools = self._generate_tools(self.service_handler)
        model = genai.GenerativeModel(model_name=model_name, tools=tools)
        model = model.start_chat(enable_automatic_function_calling=True)
        
        # Set initial context
        context = self.service_handler.get_context()
        model.send_message(context)
        
        # Configure video analyzer
        video_analyser = genai.GenerativeModel(model_name=model_name)
        
        return model, video_analyser

    def _generate_tools(self, service_handler) -> List[protos.Tool]:
        """Generate tool configurations for the model."""
        TYPE_MAP = {
            "object": protos.Type.OBJECT,
            "integer": protos.Type.INTEGER,
            "array": protos.Type.ARRAY,
            "string": protos.Type.STRING,
        }
        
        # Collect all applicable tools
        TOOLS = []
        if service_handler.service_handler.iot_object:
            TOOLS.extend(IOT_TOOLS)
        if service_handler.service_handler.google_object:
            TOOLS.extend(GOOGLE_TOOLS)
        if service_handler.service_handler.webscraper:
            TOOLS.extend(NEWS_TOOLS)
            
        if not TOOLS:
            return []

        # Generate tool declarations
        tools = []
        for tool in TOOLS:
            tool_declaration = self._create_tool_declaration(tool, TYPE_MAP)
            tools.append(tool_declaration)
            
        return tools

    def _create_tool_declaration(self, tool, TYPE_MAP) -> protos.Tool:
        """Create a tool declaration with proper schema."""
        if not tool.parameters:
            return protos.Tool(function_declarations=[
                protos.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description
                )
            ])

        properties = {}
        for param in tool.parameters:
            if param.type == "array":
                properties[param.name] = protos.Schema(
                    type=TYPE_MAP[param.type],
                    description=param.description,
                    items=protos.Schema(
                        type=TYPE_MAP[param.items.type],
                        enum=param.items.enum if hasattr(param.items, 'enum') else None
                    )
                )
            else:
                properties[param.name] = protos.Schema(
                    type=TYPE_MAP[param.type],
                    description=param.description
                )

        return protos.Tool(function_declarations=[
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

    @retry(wait=wait_random_exponential(multiplier=1, max=40), 
           stop=stop_after_attempt(3))
    def analyse_video(self, path: str, timeout: int = 600) -> Optional[Dict]:
        """
        Analyze a video file and generate a description.
        
        Args:
            path: Path to the video file
            timeout: Maximum time to wait for processing
            
        Returns:
            Dictionary containing video analysis results or None if failed
        """
        video_path = Path(path)
        print(f"Analysing {video_path}")
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at {path}")

        context = """
            Analyse carefully this video:
            - Detect any suspicious activities that may suggest theft or burglary.
            - Identify human presence or absence
            - Act like as a security agent
            - Your response should be short as possible, clear, concise and should contain only the result of your analyse.
            - Note that your output is for an LLM, then make sure it will be available to process it.
            - Your output should contain anything else, only your analyse result.
        """

        try:
            video_file = genai.upload_file(path=str(video_path))
            start_time = time.time()
            
            # Wait for processing
            while video_file.state.name == "PROCESSING":
                if time.time() - start_time > timeout:
                    genai.delete_file(video_file.name)
                    raise TimeoutError("Video processing exceeded timeout limit")
                print('.', end='', flush=True)
                time.sleep(1)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file.state.message}")

            response = self.video_analyser.generate_content(
                [video_file, context],
                request_options={"timeout": timeout}
            )

            # Clean up
            try:
                genai.delete_file(video_file.name)
            except Exception as e:
                print(f"Warning: Failed to delete temporary file: {e}")

            # Prepare response
            description = {
                "Date": date.today().isoformat(),
                "Time": datetime.now().isoformat(),
                "Video Description": response.text,
                "Analysis Duration": f"{time.time() - start_time:.2f} seconds"
            }

            return {str(path): description}

        except Exception as e:
            print(f"Error analyzing video: {e}")
            try:
                genai.delete_file(video_file.name)
            except:
                pass
            return None

    def process_user_query(self, query: str) -> str:
        """Process a user query and handle function calls."""
        try:
            start_time = time.time()
            response = self.llm.send_message(query)
            print(f"Request to Gemini: {time.time() - start_time:.2f}s")
            
            if not response.candidates:
                return "No response generated."
                
            candidate = response.candidates[0]
            if not candidate.content.parts:
                return "No content in the response."
                
            for part in candidate.content.parts:
                if part.function_call:
                    return self._handle_function_call(part.function_call)
                else:
                    return part.text
                    
        except google.api_core.exceptions.GoogleAPIError as e:
            return f"API error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _handle_function_call(self, function_call) -> str:
        """Handle a function call from the model."""
        function_name = function_call.name
        function_args = dict(function_call.args) if function_call.args else {}
        
        print(f"Function call: {function_name}")
        print(f"Arguments: {function_args}")
        
        try:
            start_time = time.time()
            function_response = self.service_handler.invoke(function_name, function_args)
            print(f"Function execution: {time.time() - start_time:.2f}s")
            
            start_time = time.time()
            final_response = self.llm.send_message(json.dumps(function_response))
            print(f"Final Gemini request: {time.time() - start_time:.2f}s")
            
            return final_response.text
            
        except Exception as e:
            return f"Function execution error: {str(e)}"


    def get_all_mp4_files(self, parent_folder: str) -> List[str]:
        """Get all MP4 files in a directory."""
        mp4_files = []
        for root, _, files in os.walk(parent_folder):
            for file in files:
                if file.endswith('.mp4'):
                    mp4_files.append(str(Path(root) / file))
        return mp4_files

    def get_iot_data(self) -> Dict:
        """Get IoT system data."""
        return self.service_handler.get_all_iot_data()

    def get_workspace_data(self) -> Dict:
        """Get workspace data."""
        try:
            data = self.service_handler.get_all_workspace_data()
            if data is None:
                return {"email": {}, "calendar": {}}
            return data
        except Exception as e:
            print(f"Error getting workspace data: {e}")
            return {"email": {}, "calendar": {}}

    def get_news_data(self) -> Dict:
        """Get news data."""
        return self.service_handler.get_news()

    def invoke(self, query: str = None) -> str:
        """Main entry point for processing queries."""
        if query is None:
            return "No query provided"
        
        prompt = f"""
                    Analyse and Decide what to do. if there is an action to do, use the necessary tool to perform that action. If there is no necessary action to do, do not do anything.
                    Data : {query}
                """
        
        return self.process_user_query(query=query)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        if hasattr(self, 'data_manager'):
            self.data_manager.stop()

