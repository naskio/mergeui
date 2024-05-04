from bokeh.io import curdoc
from core.settings import Settings
from web.gradio_app.main import model_service
from web.schema import GetModelLineageInputDTO
from utils.graph_viz import GraphPlotBuilder

settings = Settings()
model_id: str = "Q-bert/MetaMath-Cybertron"
graph = model_service.get_model_lineage(GetModelLineageInputDTO(
    id=model_id
))

plot = GraphPlotBuilder(settings).build(model_id, graph)
curdoc().add_root(plot)
