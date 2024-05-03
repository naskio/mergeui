import typing as t
import pydantic as pd
import fastapi as fa
from core.schema import Model, Graph
from web.schema import ColumnType, PartialModel, DataGraph, BaseValidationError


def pretty_error(error: t.Union[BaseValidationError, str]) -> str:
    if isinstance(error, pd.ValidationError):
        errs = error.errors()
        if errs:
            first_err = errs[0]
            loc = ','.join(first_err.get('loc', []))
            if first_err.get('type') in ['missing', 'string_too_short']:
                return f"{loc}: Field required"
            return f"{loc}: {first_err.get('msg')}"
        return str(error)
    return str(error)


def api_error(error: t.Union[BaseValidationError, str]) -> fa.exceptions.RequestValidationError:
    if isinstance(error, pd.ValidationError):
        return fa.exceptions.RequestValidationError(error.errors())
    return fa.exceptions.RequestValidationError(pretty_error(error))


def models_as_partials(models: t.List[Model], columns: t.Optional[t.List[ColumnType]] = None) -> t.List[PartialModel]:
    """Convert list of Model objects to list of partial models"""
    return list(
        map(lambda x: PartialModel(
            **x.dict(
                include=set(columns) if columns else set(t.get_args(ColumnType)),
            )
        ), models))


def graph_as_data_graph(graph: Graph) -> DataGraph:
    """Convert Graph object to data graph"""
    data = {
        "nodes": [],
        "relationships": [],
    }
    for node in graph.nodes:
        data["nodes"].append(node.dict())
    for rel in graph.relationships:
        data["relationships"].append(rel.dict())
    return data
