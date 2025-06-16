from fastapi import FastAPI, Request
import uvicorn
from summary import response
app = FastAPI()

@app.get("/")
def read_data(data: str | None = None):
    response= response(data)
    return {"summary": response}


# Optional for direct run
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
