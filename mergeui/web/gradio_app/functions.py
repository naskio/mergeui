import typing as t
from loguru import logger
import gradio as gr
from gradio.components import Component as BaseGradioComponent
from core.dependencies import get_model_service
from core.schema import BaseValidationError, SortByOptionType, ExcludeOptionType, DisplayColumnType
from web.schema import GenericRO, GetModelLineageInputDTO, ListModelsInputDTO, LabelFieldType, ColorFieldType, \
    DataFrameDataType
from utils.web import pretty_error, models_as_dataframe, fix_gradio_select_value
from utils.graph_viz import Plot, GraphPlotBuilder


def get_model_lineage(
        model_id: str,
        label_field: t.Optional[LabelFieldType],
        color_field: t.Optional[ColorFieldType],
) -> t.Tuple[BaseGradioComponent, BaseGradioComponent]:
    """Get the lineage of a model as gr.Plot."""
    logger.trace(f"get_model_lineage: `{model_id}`,`{label_field}`,`{color_field}`")
    try:
        inp = GetModelLineageInputDTO(
            id=fix_gradio_select_value(model_id, ""),
            label_field=fix_gradio_select_value(label_field),
            color_field=fix_gradio_select_value(color_field),
        )  # validate input
        model_service = get_model_service()
        graph = model_service.get_model_lineage(
            model_id=inp.id,
            max_depth=model_service.repository.db_conn.settings.max_graph_depth
        )
        plot = GraphPlotBuilder(
            graph=graph,
            selected_id=inp.id,
            label_field=inp.label_field,
            color_field=inp.color_field,
        ).build()
        ro = GenericRO[Plot](data=plot)
    except t.get_args(BaseValidationError) as e:
        ro = GenericRO[Plot](success=False, message=pretty_error(e))
    if not ro.success:
        return gr.Plot(visible=False), gr.Label(ro.message, visible=True, label="ERROR", show_label=True)
    return gr.Plot(ro.data, visible=True), gr.Label(visible=False)


def list_models(
        query: str,
        sort_by: SortByOptionType,
        display_columns: t.List[DisplayColumnType],
        exclude: ExcludeOptionType,
        license_: str,
        base_model: str,
        merge_method: str,
        architecture: str,
) -> t.Tuple[BaseGradioComponent, BaseGradioComponent]:
    """List models in a gr.DataFrame."""
    logger.trace(f"list_models: `{query}`,`{sort_by}`,`{display_columns}`,`{exclude}`,`{license_}`,"
                 f"`{base_model}`,`{merge_method}`,`{architecture}`")
    try:
        # validate input
        inp = ListModelsInputDTO(
            query=query,
            sort_by=fix_gradio_select_value(sort_by),
            display_columns=display_columns,
            exclude=fix_gradio_select_value(exclude),
            license=fix_gradio_select_value(license_),
            base_model=fix_gradio_select_value(base_model),
            merge_method=fix_gradio_select_value(merge_method),
            architecture=fix_gradio_select_value(architecture),
        )
        model_service = get_model_service()
        models = model_service.list_models(
            query=inp.query,
            sort_by=inp.sort_by,
            exclude=inp.exclude,
            license_=inp.license,
            merge_method=inp.merge_method,
            architecture=inp.architecture,
            base_model=inp.base_model,
            limit=model_service.repository.db_conn.settings.results_limit,
        )
        dfd: DataFrameDataType = models_as_dataframe(models, inp.display_columns, pretty=True)
        ro = GenericRO[DataFrameDataType](data=dfd)
    except t.get_args(BaseValidationError) as e:
        ro = GenericRO[DataFrameDataType](success=False, message=pretty_error(e))
    if not ro.success:
        return gr.DataFrame(visible=False), gr.Label(ro.message, visible=True, label="ERROR", show_label=True)
    if not ro.data[0]:
        return gr.DataFrame(visible=False), gr.Label(
            f"No results found, please try different keywords/filters.", visible=True, label="INFO", show_label=True)
    return gr.DataFrame(value=ro.data[0], headers=ro.data[1], datatype=ro.data[2],
                        visible=True, wrap=True, line_breaks=True,
                        label=f"Models ({len(ro.data[0])})", show_label=True), gr.Label(visible=False)
