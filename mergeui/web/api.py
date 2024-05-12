import typing as t
import fastapi as fa
import core.settings
from core.dependencies import get_model_service, get_settings
from services import ModelService
from core.schema import SortByOptionType, DisplayColumnType, ExcludeOptionType
from web.schema import ListModelsInputDTO, GetModelLineageInputDTO, GenericRO, PartialModel, DataGraph
from utils.web import api_error, models_as_partials, graph_as_data_graph

router = fa.APIRouter()


@router.get('/model_lineage')
def model_lineage(
        id_: str = fa.Query(alias='id'),
        model_service: ModelService = fa.Depends(get_model_service),
        settings: 'core.settings.Settings' = fa.Depends(get_settings),
) -> GenericRO[DataGraph]:
    try:
        inp = GetModelLineageInputDTO(id=id_, label_field=None, color_field=None)  # validate input
        graph = model_service.get_model_lineage(
            model_id=inp.id,
            max_depth=settings.max_graph_depth,
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
        exclude: t.Optional[ExcludeOptionType] = None,
        license_: t.Optional[str] = fa.Query(None, alias='license'),
        base_model: t.Optional[str] = None,
        merge_method: t.Optional[str] = None,
        architecture: t.Optional[str] = None,
        model_service: ModelService = fa.Depends(get_model_service),
        settings: 'core.settings.Settings' = fa.Depends(get_settings),
) -> GenericRO[list[PartialModel]]:
    try:
        # validate input
        inp = ListModelsInputDTO(query=query, sort_by=sort_by, display_columns=display_columns, exclude=exclude,
                                 license=license_, base_model=base_model, merge_method=merge_method,
                                 architecture=architecture)
        models = model_service.list_models(
            query=inp.query,
            sort_by=inp.sort_by,
            exclude=inp.exclude,
            license_=inp.license,
            merge_method=inp.merge_method,
            architecture=inp.architecture,
            base_model=inp.base_model,
            limit=settings.results_limit,
        )
        data = models_as_partials(models, display_columns=inp.display_columns, pretty=False)
        return GenericRO(data=data)  # return response
    except (ValueError, AssertionError) as e:
        raise api_error(e)
