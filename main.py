from fastapi import FastAPI, Request
import uvicorn
from summary import response
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

@app.post("/predict")
async def predict(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    from summary import response
    result = response(prompt)
    return {"summary": result}

# Optional for direct run
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
