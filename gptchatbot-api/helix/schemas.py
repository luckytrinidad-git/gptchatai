from ninja import Schema

class QueryRequest(Schema):
    question: str
    mode: str = "data"