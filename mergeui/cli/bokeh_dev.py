from bokeh.io import curdoc
from core.settings import Settings
from core.dependencies import get_settings, get_model_service
from utils.graph_viz import GraphPlotBuilder
from core.schema import Graph
from web.schema import LabelFieldType, ColorFieldType

settings: Settings = get_settings()
model_service = get_model_service()

# model_id: str = "X/Y"  # empty graph
# model_id: str = "mistralai/Mistral-7B-v0.1"  # 1 node graph
model_id: str = "Q-bert/MetaMath-Cybertron"  # full graph

graph: Graph = model_service.get_model_lineage(
    model_id=model_id,
    max_depth=settings.max_graph_depth,
)

selected_id = model_id
# selected_id = None
label_field: LabelFieldType = "id"
# label_field = None
color_field: ColorFieldType = "average_score"
# color_field = None

plot = GraphPlotBuilder(
    graph=graph,
    selected_id=selected_id,
    label_field=label_field,
    color_field=color_field,
).build()

curdoc().add_root(plot)
