import os

import uvicorn


if __name__ == "__main__":
    for key in ("DATABASE_URL", "MONGO_URI", "MONGODB_URI"):
        if key in os.environ:
            os.environ[key] = os.environ[key].replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal")
    print("HW8 FastAPI published at http://127.0.0.1:8686", flush=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8686)
