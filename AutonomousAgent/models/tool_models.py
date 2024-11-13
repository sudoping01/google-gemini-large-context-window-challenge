from dataclasses import dataclass,field
from typing import List

@dataclass
class ItemConfig:
    type : str 
    enum: List[str] = field(default_factory=list)

@dataclass
class ParamConfig:
    name:str
    type:str
    description:str 
    items: ItemConfig

@dataclass
class ToolConfig:
    name: str
    description: str
    parameters: list[ParamConfig]
    required: List[str]