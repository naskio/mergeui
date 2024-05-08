import typing as t
import fastapi as fa
from core.dependencies import get_model_service
from web.schema import DataGraph
from utils.web import api_error, models_as_partials, graph_as_data_graph
from web.schema import DisplayColumnType, ExcludeOptionType, SortByOptionType, ListModelsInputDTO, \
    GetModelLineageInputDTO, GenericRO, PartialModel, BaseValidationError

router = fa.APIRouter()


@router.get('/model_lineage')
def model_lineage(
        id_: str = fa.Query(alias='id'),
        model_service=fa.Depends(get_model_service),
) -> GenericRO[DataGraph]:
    try:
        inp = GetModelLineageInputDTO(id=id_)  # validate input
        graph = model_service.get_model_lineage(inp)
        data = graph_as_data_graph(graph)
        return GenericRO[DataGraph](data=data)  # return response
    except t.get_args(BaseValidationError) as e:
        raise api_error(e)


@router.get('/models')
def list_models(
        query: t.Optional[str] = None,
        sort_by: t.Optional[SortByOptionType] = None,
        display_columns: t.List[DisplayColumnType] = fa.Query([]),
        exclude: t.Optional[ExcludeOptionType] = None,
        license_: t.Optional[str] = fa.Query(None, alias='license'),
        base_model: t.Optional[str] = None,
        merge_method: t.Optional[str] = None,
        architecture: t.Optional[str] = None,
        model_service=fa.Depends(get_model_service),
) -> GenericRO[list[PartialModel]]:
    try:
        # validate input
        inp = ListModelsInputDTO(query=query, sort_by=sort_by, display_columns=display_columns, exclude=exclude,
                                 license=license_, base_model=base_model, merge_method=merge_method,
                                 architecture=architecture)
        data = models_as_partials(model_service.list_models(inp), display_columns, pretty=False)
        return GenericRO(data=data)  # return response
    except t.get_args(BaseValidationError) as e:
        raise api_error(e)
