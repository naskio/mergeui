import typing as t
import fastapi as fa
import pydantic as pd
from core.schema import Model, Graph
from utils import format_datetime, format_large_number
from web.schema import ColumnType, PartialModel, DataGraph, BaseValidationError


def pretty_error(error: t.Union[Exception, BaseValidationError, str]) -> str:
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


def models_as_partials(models: t.List[Model], columns: t.Optional[t.List[ColumnType]] = None, pretty: bool = False) \
        -> t.List[PartialModel]:
    """Convert list of Model objects to list of partial models"""
    columns = set(columns or t.get_args(ColumnType))
    formatters = {
        "likes": format_large_number,
        "downloads": format_large_number,
        "created_at": format_datetime,
        "updated_at": format_datetime,
    }
    if not pretty:
        formatters = {}
    return list(map(lambda m: PartialModel(
        **m.dict(include=columns, exclude=formatters.keys()),
        **{k: formatter(getattr(m, k)) for k, formatter in formatters.items() if k in columns},
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


DataFrameDataType = tuple[list[list], list[str], list[str]]


def models_as_dataframe(
        models: t.List[Model], columns: t.Optional[t.List[ColumnType]] = None,
        pretty: bool = True,
        clickable_id: bool = True,
) -> DataFrameDataType:
    """Convert list of Model objects to DataFrame"""
    columns = columns or t.get_args(ColumnType)
    formatters = {
        "likes": format_large_number,
        "downloads": format_large_number,
        "created_at": format_datetime,
        "updated_at": format_datetime,
    }
    number_keys = {'likes', 'downloads'}
    date_keys = {'created_at', 'updated_at'}
    data: list[list] = []
    headers: list[str] = []
    datatypes: list[str] = []
    for model in models:
        row = []
        for col in columns:
            if clickable_id and col == 'id':
                # row.append(f'<a href="{model.url}" target="_blank" rel="noopener noreferrer">{model.id}</a>')
                row.append(f'[{model.id}]({model.url})')
                if len(datatypes) < len(columns):
                    # datatypes.append('html')
                    datatypes.append('markdown')
            elif pretty and col in formatters:
                row.append(formatters[col](getattr(model, col)))
                if len(datatypes) < len(columns):
                    datatypes.append('str')
            else:
                row.append(getattr(model, col))
                if len(datatypes) < len(columns):
                    if col in number_keys:
                        datatypes.append('number')
                    elif col in date_keys:
                        datatypes.append('date')
                    else:
                        datatypes.append('str')
            if len(headers) < len(columns):
                headers.append(col)
        data.append(row)
    return data, headers, datatypes
