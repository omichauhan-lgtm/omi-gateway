import inspect
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

def test_func():
    @limiter.limit("10/minute")
    async def submit_reliability_feedback(request: Request):
        pass
    print("Success without type annotations or extra args")

try:
    @limiter.limit("10/minute")
    async def submit_reliability_feedback(request: Request, feedback: str):
        pass
    print("Success with multiple args")
except Exception as e:
    print("Failed:", e)
