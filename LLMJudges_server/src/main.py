import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from LLMJudges_server.src.routers import llm_judges_router

# from fastapi.responses import FileResponse
# from fastapi.staticfiles import StaticFiles


app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    llm_judges_router.router,
    tags=["LLM Judges"],
    responses={404: {"description": "Not found"}},
)

# app.mount("/", StaticFiles(directory="./LLMJudges_server/static/build", html=True), name="static")


# # If url not found in backend, pass to frontend.
# @app.exception_handler(404)
# async def not_found_exception_handler(request, exc):
#     return FileResponse("./LLMJudges_server/static/build/index.html")


if __name__ == "__main__":
    uvicorn.run("LLMJudges_server.src.main:app", port=5000, host="0.0.0.0", log_level="info")
