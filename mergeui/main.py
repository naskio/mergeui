import uvicorn
import fastapi as fa
from core.dependencies import get_settings
from web.api import router as api_router

settings = get_settings()

app = fa.FastAPI(
    title=settings.project_name,
    description=f"{settings.description}",
)

app.include_router(api_router, prefix="/api", tags=["API"])


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return fa.responses.FileResponse(settings.favicon_path)


if not settings.gradio_app_disabled:
    import gradio as gr
    from web.gradio_app.main import demo

    app = gr.mount_gradio_app(app, demo, path="/", favicon_path=settings.favicon_path, show_error=True)


def start_server():
    uvicorn.run("mergeui.main:app", reload=True, port=8000, log_level="debug")
