from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]

class Usage(BaseModel):
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_cost_micros: int

class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    content: str
    usage: Usage
    idempotent_replay: bool = False