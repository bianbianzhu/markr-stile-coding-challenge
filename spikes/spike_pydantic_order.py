from pydantic import BaseModel


class Agg(BaseModel):
    mean: float
    stddev: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    count: int


m = Agg(mean=65.0, stddev=0.0, min=65.0, max=65.0, p25=65.0, p50=65.0, p75=65.0, count=1)
print(m.model_dump_json())
