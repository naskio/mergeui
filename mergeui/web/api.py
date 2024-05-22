import typing as t
import fastapi as fa
from core.dependencies import get_model_service
from services import ModelService
from core.schema import SortByOptionType, DisplayColumnType, ExcludeOptionType
from web.schema import ListModelsInputDTO, GetModelLineageInputDTO, GenericRO, PartialModel, DataGraph
from utils.web import api_error, models_as_partials, graph_as_data_graph

router = fa.APIRouter()

DirectedField = GetModelLineageInputDTO.model_fields['directed']
MaxHopsField = GetModelLineageInputDTO.model_fields['max_hops']


@router.get('/model_lineage')
def model_lineage(
        id_: str = fa.Query(alias='id'),
        directed: bool = DirectedField.default,
        max_hops: int = fa.Query(MaxHopsField.default, ge=1),
        model_service: ModelService = fa.Depends(get_model_service),
) -> GenericRO[DataGraph]:
    try:
        inp = GetModelLineageInputDTO(id=id_, directed=directed, max_hops=max_hops,
                                      label_field=None, color_field=None)  # validate input
        graph = model_service.get_model_lineage(
            model_id=inp.id,
            directed=inp.directed,
            max_hops=inp.max_hops,
        )
        data = graph_as_data_graph(graph)
        return GenericRO[DataGraph](data=data)  # return response
    except (ValueError, AssertionError) as e:
        raise api_error(e)


@router.get('/models')
def list_models(
        query: t.Optional[str] = None,
        sort_by: t.Optional[SortByOptionType] = None,
        display_columns: t.List[DisplayColumnType] = fa.Query([]),
        excludes: t.List[ExcludeOptionType] = fa.Query([]),
        author: t.Optional[str] = None,
        license_: t.Optional[str] = fa.Query(None, alias='license'),
        merge_method: t.Optional[str] = None,
        architecture: t.Optional[str] = None,
        base_model: t.Optional[str] = None,
        model_service: ModelService = fa.Depends(get_model_service),
) -> GenericRO[list[PartialModel]]:
    try:
        # validate input
        inp = ListModelsInputDTO(
            query=query, sort_by=sort_by, display_columns=display_columns, excludes=excludes,
            author=author, license=license_, merge_method=merge_method,
            architecture=architecture, base_model=base_model)
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
        data = models_as_partials(models, display_columns=inp.display_columns, pretty=False)
        return GenericRO(data=data)  # return response
    except (ValueError, AssertionError) as e:
        raise api_error(e)
