from dataclasses import dataclass


@dataclass
class EndpointModel:
    pnml_content: str
    dot_content: str
