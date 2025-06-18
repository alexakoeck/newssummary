from fastapi import FastAPI, Request
import uvicorn
from summary import final
app = FastAPI()

# ✅ Register CORS middleware FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_data(data: str | None = None):
    print(data)
    response= final(data)
    return {'summary': response}


# Optional for direct run
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
