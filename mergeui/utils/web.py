import typing as t
import fastapi as fa
import pydantic as pd
from core.schema import Model, Graph
from utils import pretty_format_dt, pretty_format_int
from web.schema import (DISPLAY_FIELDS, MODEL_DT_FIELDS, MODEL_INT_FIELDS, MODEL_FLOAT_FIELDS,
                        BaseValidationError, DataFrameDataType, DisplayColumnType, PartialModel, DataGraph)


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


def models_as_partials(
        models: t.List[Model],
        display_columns: t.Optional[t.List[DisplayColumnType]] = None,
        pretty: bool = False,
) -> t.List[PartialModel]:
    """Convert list of Model objects to list of partial models"""
    display_columns = set(display_columns or DISPLAY_FIELDS)
    if not pretty:
        pretty_set = set()
    else:
        pretty_set = set(MODEL_DT_FIELDS + MODEL_INT_FIELDS) & display_columns
    copy_set = display_columns - pretty_set
    return list(map(lambda m: PartialModel(
        **m.dict(include=copy_set),
        **{k: pretty_format_dt(getattr(m, k)) for k in MODEL_DT_FIELDS if k in pretty_set},
        **{k: pretty_format_int(getattr(m, k)) for k in MODEL_INT_FIELDS if k in pretty_set},
    ), models))


def graph_as_data_graph(graph: Graph) -> DataGraph:
    """Convert Graph object to data graph"""
    nodes = []
    relationships = []
    nodes_data = {}
    for node in graph.nodes:  # _id, _properties, _labels
        node_data = {k: v for k, v in node._properties.items() if k in DISPLAY_FIELDS}
        nodes_data[node._id] = node_data
        nodes.append(node_data)
    for rel in graph.relationships:  # _id, _properties, _end_node_id, _start_node_id, _type
        relationships.append({
            **rel._properties,
            "type": rel._type,
            "source": nodes_data[rel._start_node_id].get("id"),
            "target": nodes_data[rel._end_node_id].get("id"),
        })
    return DataGraph(nodes=nodes, relationships=relationships)


def models_as_dataframe(
        models: t.List[Model],
        display_columns: t.Optional[t.List[DisplayColumnType]] = None,
        pretty: bool = True,
) -> DataFrameDataType:
    """Convert list of Model objects to DataFrame"""

    def as_rounded_percentage(f_: t.Optional[float]) -> t.Optional[float]:
        if f_ is not None:
            return round(f_ * 100, 2)

    display_columns = set(display_columns or DISPLAY_FIELDS)
    data: list[list] = []
    headers: list[str] = []
    datatypes: list[str] = []
    for model in models:
        row = []
        for col in display_columns:
            value = getattr(model, col)
            datatype_ = 'str'
            if pretty:
                if col == 'id':
                    value = f'[{model.id}]({model.url})'
                    datatype_ = 'markdown'
                elif col == 'description':
                    datatype_ = 'markdown'
                elif col in MODEL_DT_FIELDS:
                    value = pretty_format_dt(value)
                elif col in MODEL_INT_FIELDS:
                    value = pretty_format_int(value)
                elif col in MODEL_FLOAT_FIELDS:
                    value = as_rounded_percentage(value)
                    datatype_ = 'number'
            else:
                if col in MODEL_INT_FIELDS or col in MODEL_FLOAT_FIELDS:
                    datatype_ = 'number'
                elif col in MODEL_DT_FIELDS:
                    datatype_ = 'date'
            row.append(value)
            if len(datatypes) < len(display_columns):
                datatypes.append(datatype_)
            if len(headers) < len(display_columns):
                if pretty:
                    headers.append(Model.field_label(col))
                else:
                    headers.append(col)
        data.append(row)
    return data, headers, datatypes
