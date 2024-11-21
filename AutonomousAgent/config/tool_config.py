from ..models.tool_models import ParamConfig, ItemConfig, ToolConfig

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

DOCUMENT_TOOL = [
    ToolConfig(
        name="get_document_content",
        description="use this to get the describtive document about the OpenIoT",
        parameters=[],
        required=[]
    )
]
