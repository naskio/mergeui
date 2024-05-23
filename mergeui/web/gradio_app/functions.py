import typing as t
from loguru import logger
import gradio as gr
from gradio.components import Component as BaseGradioComponent
from mergeui.core.dependencies import get_model_service
from mergeui.core.schema import BaseValidationError, SortByOptionType, ExcludeOptionType, DisplayColumnType
from mergeui.web.schema import GenericRO, GetModelLineageInputDTO, ListModelsInputDTO, LabelFieldType, ColorFieldType, \
    DataFrameDataType
from mergeui.utils.web import pretty_error, models_as_dataframe, fix_gradio_select_value
from mergeui.utils.graph_viz import Plot, GraphPlotBuilder


def get_model_lineage(
        model_id: str,
        directed: bool,
        max_hops: int,
        label_field: t.Optional[LabelFieldType],
        color_field: t.Optional[ColorFieldType],
) -> t.Tuple[BaseGradioComponent, BaseGradioComponent]:
    """Get the lineage of a model as gr.Plot."""
    logger.trace(f"get_model_lineage: `{model_id}`,`{directed}`,`{max_hops}`,`{label_field}`,`{color_field}`")
    try:
        # validate input
        inp = GetModelLineageInputDTO(
            id=fix_gradio_select_value(model_id, ""),
            directed=directed,
            max_hops=max_hops,
            label_field=fix_gradio_select_value(label_field),
            color_field=fix_gradio_select_value(color_field),
        )
        model_service = get_model_service()
        graph = model_service.get_model_lineage(
            model_id=inp.id,
            directed=inp.directed,
            max_hops=inp.max_hops,
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
        query: t.Optional[str],
        sort_by: t.Optional[SortByOptionType],
        display_columns: t.List[DisplayColumnType],
        excludes: t.List[ExcludeOptionType],
        author: t.Optional[str],
        license_: t.Optional[str],
        merge_method: t.Optional[str],
        architecture: t.Optional[str],
        base_model: t.Optional[str],
) -> t.Tuple[BaseGradioComponent, BaseGradioComponent]:
    """List models in a gr.DataFrame."""
    logger.trace(f"list_models: `{query}`,`{sort_by}`,`{display_columns}`,`{excludes}`,`{author}`,`{license_}`,"
                 f"`{merge_method}`,`{architecture}`,`{base_model}`")
    try:
        # validate input
        inp = ListModelsInputDTO(
            query=query,
            sort_by=fix_gradio_select_value(sort_by),
            display_columns=display_columns,
            excludes=excludes,
            author=fix_gradio_select_value(author),
            license=fix_gradio_select_value(license_),
            merge_method=fix_gradio_select_value(merge_method),
            architecture=fix_gradio_select_value(architecture),
            base_model=fix_gradio_select_value(base_model),
        )
        model_service = get_model_service()
        models = model_service.list_models(
            query=inp.query,
            sort_by=inp.sort_by,
            excludes=inp.excludes,
            author=inp.author,
            license_=inp.license,
            merge_method=inp.merge_method,
            architecture=inp.architecture,
            base_model=inp.base_model,
            limit=inp.limit,
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
    # noinspection PyTypeChecker
    return gr.DataFrame(value=ro.data[0], headers=ro.data[1], datatype=ro.data[2],
                        visible=True, wrap=True, line_breaks=True,
                        label=f"Models ({len(ro.data[0])})", show_label=True), gr.Label(visible=False)
