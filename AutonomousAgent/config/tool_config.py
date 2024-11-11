from caytu_ai.models.tool_models import ParamConfig, ItemConfig, ToolConfig
from typing import List, Dict, Any
from google.generativeai import protos

IOT_TOOLS = [
    ToolConfig(
        name="iot_get_states",
        description="Get the current states of specified IoT devices. Use this when you need to know the status of one or more IoT devices.",
        parameters= [
            ParamConfig(
                name="topics", 
                type="array",
                description="List of topic names representing IoT devices to query",
                items = ItemConfig(
                    type="string", 
                    enum=[]
                )
            )

        ], 
        
        required=["topics"]
    ),

     ToolConfig(
        name="iot_set_states",
        description="Set the states of specified IoT devices. Use this when you need to change the status of one or more IoT devices.",
        parameters=[
            ParamConfig(
                name="topics", 
                type="array",
                description= "List of topic names representing IoT devices to control. Note that the topic that control a device, is ended by /command, example caytu/light/command",
                items= ItemConfig(
                    type="string", 
                    enum=[]

                )
            ), 
     

            ParamConfig(
                name = "states", 
                type = "array", 
                description="List of states to set for the corresponding topics. Must be either 'ON' or 'OFF'.", 
                items=ItemConfig(
                    type="string",
                    enum=["ON", "OFF"]
                )

            )

        ],
        
        required=["topics", "states"]
        )
]



GOOGLE_TOOLS = [
    ToolConfig(
        name="get_mails",
        description="Retrieve recent emails from the user's inbox. Use this when the user asks about their recent emails or messages.",
        parameters=[
            ParamConfig(
                name="id",
                type="integer",
                description="The id of the mail to return for example 0 for the lastest message, 1 for the second one. If you want all the mails, don't need to set id it can be optional [Optional]. If there are many mails, please ask the user to specify the one they want.",
                items=ItemConfig(type="integer", enum=[])
            ),
            ParamConfig(
                name="number_of_mail",
                type="integer",
                description="The number of mail to return [Optional]",
                items=ItemConfig(type="integer", enum=[])
            )
        ],
        required=[]
    ),
    ToolConfig(
        name="send_mail",
        description="Send an email on behalf of the user. Use this when the user wants to compose and send an email.",
        parameters=[
            ParamConfig(
                name="to",
                type="string",
                description="Email address of the recipient",
                items=ItemConfig(type="string")
            ),
            ParamConfig(
                name="subject",
                type="string",
                description="Subject line of the email",
                items=ItemConfig(type="string")
            ),
            ParamConfig(
                name="body",
                type="string",
                description="Main content of the email",
                items=ItemConfig(type="string")
            )
        ],
        required=["to", "subject", "body"]
    ),
    ToolConfig(
        name="get_events",
        description="Retrieve upcoming calendar events. Use this when the user asks about their schedule or upcoming appointments.",
        parameters=[],
        required=[]
    ),
    ToolConfig(
        name="set_event",
        description="Create a new calendar event. Use this when the user wants to schedule a new appointment or add an event to their calendar.",
        parameters=[
            ParamConfig(
                name="summary",
                type="string",
                description="Brief title or description of the event",
                items=ItemConfig(type="string")
            ),
            ParamConfig(
                name="start_time",
                type="string",
                description="Start time of the event in YYYY-MM-DD HH:MM:SS format",
                items=ItemConfig(type="string")
            ),
            ParamConfig(
                name="end_time",
                type="string",
                description="End time of the event in YYYY-MM-DD HH:MM:SS format",
                items=ItemConfig(type="string")
            ),
            ParamConfig(
                name="location",
                type="string",
                description="Location of the event (optional)",
                items=ItemConfig(type="string")
            ),
            ParamConfig(
                name="description",
                type="string",
                description="Detailed description of the event (optional)",
                items=ItemConfig(type="string")
            )
        ],
        required=["summary", "start_time", "end_time"]
    )
]


NEWS_TOOLS = [
    ToolConfig(
        name="get_news",
        description="Fetch the latest news articles. Use this when the user asks for current news or updates on recent events",
        parameters=[],
        required=[]
    )
]


def convert_tools_to_google_genai_format(TOOLS:List[ToolConfig]) -> list[protos.Tool]:
    TYPE_MAP = {
                "object" : protos.Type.OBJECT, 
                "integer" : protos.Type.INTEGER, 
                "array": protos.Type.ARRAY, 
                "string" : protos.Type.STRING, 
              }
    
    tools: List[protos.Tool] = []
    
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



def convert_tools_to_openai_format(TOOLS:List[List] = []) -> List[Dict[str, Any]]:
    tools = []

    for tool_list in TOOLS:
        if not tool_list:
            continue
            
        for tool in tool_list:
            properties = {}
            
            if tool.parameters:

                for param in tool.parameters:
                    property_dict = {
                        "type": param.type,
                        "description": param.description
                    }
                    
                    if param.type == "array" and param.items:
                        property_dict["items"] = {
                            "type": param.items.type
                        }
                        
                        if param.items.enum:
                            property_dict["items"]["enum"] = param.items.enum
                    
                    if param.type == "integer":
                        if param.name == "id":
                            property_dict["minimum"] = 0
                        elif param.name == "number_of_mail":
                            property_dict["minimum"] = 1
                    
                    properties[param.name] = property_dict
            else:
                
                properties["execute"] = {
                    "type": "boolean",
                    "description": "Set to true to execute this function",
                }
                tool.required = ["execute"]  
            
            function_dict = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": tool.required,
                        "additionalProperties": False
                    }
                }
            }
            
            tools.append(function_dict)
    
    for tool in tools:
        tool["function"]["parameters"]["strict"] = True
    
    return tools
