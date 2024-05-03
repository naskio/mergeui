import typing as t
import fastapi as fa
from services.models import ModelService
from core.dependencies import get_model_service
from web.schema import ColumnType, ExcludeOptionType, SortByOptionType, DataGraph, ListModelsInputDTO, \
    GetModelLineageInputDTO, GenericRO, PartialModel, BaseValidationError
from utils.web import api_error, models_as_partials, graph_as_data_graph

router = fa.APIRouter()


@router.get('/model_lineage')
def model_lineage(
        id_: str = fa.Query(alias='id'),
        model_service: ModelService = fa.Depends(get_model_service),
) -> GenericRO[DataGraph]:
    try:
        inp = GetModelLineageInputDTO(id=id_)  # validate input
        data = model_service.get_model_lineage(inp)
        return GenericRO(data=graph_as_data_graph(data))  # return response
    except BaseValidationError as e:
        raise api_error(e)


@router.get('/models')
def list_models(
        query: t.Optional[str] = None,
        sort_by: t.Optional[SortByOptionType] = None,
        columns: t.List[ColumnType] = fa.Query([]),
        exclude: t.Optional[ExcludeOptionType] = None,
        license_: t.Optional[str] = fa.Query(None, alias='license'),
        base_model: t.Optional[str] = None,
        merge_method: t.Optional[str] = None,
        architecture: t.Optional[str] = None,
        model_service: ModelService = fa.Depends(get_model_service),
) -> GenericRO[list[PartialModel]]:
    try:
        # validate input
        inp = ListModelsInputDTO(query=query, sort_by=sort_by, columns=columns, exclude=exclude, license=license_,
                                 base_model=base_model, merge_method=merge_method, architecture=architecture)
        data = models_as_partials(model_service.list_models(inp), columns)
        return GenericRO(data=data)  # return response
    except BaseValidationError as e:
        raise api_error(e)
