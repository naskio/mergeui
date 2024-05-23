import random
from bokeh.io import curdoc
from mergeui.core.settings import Settings
from mergeui.core.dependencies import get_settings, get_model_service
from mergeui.utils.graph_viz import GraphPlotBuilder
from mergeui.core.schema import Graph
from mergeui.web.schema import LabelFieldType, ColorFieldType

settings: Settings = get_settings()
model_service = get_model_service()

# model_id: str = "X/Y"  # empty graph
# model_id: str = "mistralai/Mistral-7B-v0.1"  # 1 node graph
model_id: str = "Q-bert/MetaMath-Cybertron"  # full graph

graph: Graph = model_service.get_model_lineage(
    model_id=model_id,
    directed=False,
    max_hops=min(random.choice(range(1, settings.max_hops + 1)), 2),
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
