import asyncio
import httpx
from fastapi import FastAPI, Request

LIMIT = 16  # tiny for testing

class BodyCap:
    def __init__(self, app, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        cl = next((v for k, v in scope.get("headers", []) if k == b"content-length"), None)
        if cl is not None and int(cl) > self.limit:
            return await self._reject(send)

        seen = 0
        async def wrapped_receive():
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > self.limit:
                    raise _TooLarge()
            return msg

        try:
            await self.app(scope, wrapped_receive, send)
        except _TooLarge:
            await self._reject(send)

    async def _reject(self, send):
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b'{"error":"body_too_large"}'})

class _TooLarge(Exception): ...

app = FastAPI()

@app.post("/echo")
async def echo(req: Request):
    body = await req.body()
    return {"len": len(body)}

app.add_middleware(BodyCap, limit=LIMIT)

async def main():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r1 = await c.post("/echo", content=b"x" * 10)
        print("under:", r1.status_code, r1.json())
        r2 = await c.post("/echo", content=b"x" * 100)
        print("over:", r2.status_code, r2.text)
        # Lying content-length: still rejected by streaming counter
        r3 = await c.post("/echo", content=b"x" * 100,
                          headers={"content-length": "5"})
        print("lying CL:", r3.status_code, r3.text)

asyncio.run(main())
