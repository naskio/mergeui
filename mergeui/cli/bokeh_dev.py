from bokeh.io import curdoc
from core.dependencies import get_settings, get_model_service
from utils.graph_viz import GraphPlotBuilder
from web.schema import GetModelLineageInputDTO

settings = get_settings()
model_service = get_model_service()

model_id: str = "Q-bert/MetaMath-Cybertron"
graph = model_service.get_model_lineage(GetModelLineageInputDTO(
    id=model_id
))

plot = GraphPlotBuilder(settings).build(model_id, graph)
curdoc().add_root(plot)
