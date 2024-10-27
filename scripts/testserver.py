# /// script
# dependencies = ["fastapi[standard]"]
# ///

import argparse

import uvicorn
from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
@app.post("/")
async def root_get(request: Request):
    return {"METHOD": request.method, "headers": request.headers, "body": await request.body()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
