from fastapi import FastAPI

from routes import router as api_router
from database import Base, engine
import models

app = FastAPI()
app.include_router(api_router)


# https://stackoverflow.com/questions/75732232/async-sqlalchemy-cannot-create-tables-in-the-database
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
