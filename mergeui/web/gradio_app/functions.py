import typing as t

import gradio as gr
from gradio.components import Component as BaseGradioComponent
from loguru import logger

from services.models import ModelService
from utils.graph_viz import Plot, GraphPlotBuilder
from utils.web import pretty_error, models_as_partials
from web.schema import ColumnType, ExcludeOptionType, SortByOptionType, GenericRO, \
    GetModelLineageInputDTO, ListModelsInputDTO, PartialModel


def inject_model_service(model_service: ModelService):
    def decorator(func):
        setattr(func, 'model_service', model_service)
        return func

    return decorator


def get_model_service(func: t.Callable) -> ModelService:
    return getattr(func, "model_service")


def get_model_lineage(model_id: str) -> t.Tuple[BaseGradioComponent, BaseGradioComponent]:
    logger.trace(f"call: {model_id}")
    try:
        inp = GetModelLineageInputDTO(id=model_id)  # validate input
        model_service = get_model_service(get_model_lineage)
        settings = model_service.repository.db_conn.settings
        graph = model_service.get_model_lineage(inp)
        plot = GraphPlotBuilder(settings).build(inp.id, graph)
        ro = GenericRO[Plot](data=plot)
    except Exception as e:
        ro = GenericRO[Plot](success=False, message=pretty_error(e))
    if not ro.success:
        return gr.Plot(visible=False), gr.Label(ro.message, visible=True, label="ERROR")
    return gr.Plot(ro.data, visible=True), gr.Label(visible=False)


def list_models(query: str, sort_by: SortByOptionType, columns: t.List[ColumnType], exclude: ExcludeOptionType,
                license_: str, base_model: str, merge_method: str, architecture: str) \
        -> t.Tuple[BaseGradioComponent, BaseGradioComponent]:
    logger.trace(f"call: {query},{sort_by},{columns},{exclude},{license_},{base_model},{merge_method},{architecture}")
    try:
        # validate input
        inp = ListModelsInputDTO(query=query, sort_by=sort_by, columns=columns, exclude=exclude, license=license_,
                                 base_model=base_model, merge_method=merge_method, architecture=architecture)
        model_service = get_model_service(list_models)
        data = models_as_partials(model_service.list_models(inp), inp.columns)
        ro = GenericRO[list[PartialModel]](data=data)
    except Exception as e:
        ro = GenericRO[list[PartialModel]](success=False, message=pretty_error(e))
    if not ro.success:
        return gr.DataFrame(visible=False), gr.Label(ro.message, visible=True, label="ERROR")
    return gr.DataFrame(ro.data, visible=True), gr.Label(visible=False)
