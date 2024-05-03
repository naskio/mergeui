import typing as t
import fastapi as fa
from services.models import ModelService, ListModelsInputDTO, GenericRO
from core.schema import ColumnType, ExcludeOptionType, SortByOptionType
from core.dependencies import get_model_service
from web.utils import api_error

router = fa.APIRouter()


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
) -> GenericRO[list[dict]]:
    try:  # validate input
        inp = ListModelsInputDTO(query=query, sort_by=sort_by, columns=columns, exclude=exclude, license=license_,
                                 base_model=base_model, merge_method=merge_method, architecture=architecture)
        ro = model_service.list_models(inp)
        if not ro.success:
            raise api_error(ro.message)
        return ro  # return response
    except Exception as e:
        raise api_error(e)
