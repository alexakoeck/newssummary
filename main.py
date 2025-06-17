from fastapi import FastAPI, Request
import uvicorn
from summary import final
app = FastAPI()

@app.post("/")
def read_data(data: str | None = None):
    print(data)
    response= final(data)
    return  response


# Optional for direct run
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
