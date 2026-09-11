from pydantic import BaseModel

class EstimateRequest(BaseModel):
    model: str
    daily_requests: int
    avg_input_tokens: int
    avg_cached_input_tokens: int = 0
    avg_output_tokens: int
    avg_reasoning_tokens: int = 0
    days: int = 30