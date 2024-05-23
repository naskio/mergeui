import typing as t
import fastapi as fa
import pydantic as pd
from mergeui.utils import pretty_format_dt, pretty_format_int, pretty_format_float, pretty_format_description, \
    is_valid_repo_id
from mergeui.core.schema import Model, Graph, BaseValidationError
from mergeui.web.schema import DataFrameDataType, DisplayColumnType, PartialModel, DataGraph


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
    display_columns = set(display_columns or Model.display_fields())
    pretty_set = display_columns if pretty else set()
    return list(map(lambda m: {
        **m.dict(include=display_columns),
        **{k: pretty_format_description(getattr(m, k), m.private, is_valid_repo_id(m.id), 256)
           for k in {"description"} if k in pretty_set},
        **{k: pretty_format_dt(getattr(m, k)) for k in Model.dt_fields() if k in pretty_set},
        **{k: pretty_format_int(getattr(m, k)) for k in Model.int_fields() if k in pretty_set},
        **{k: pretty_format_float(getattr(m, k), suffix="%") for k in Model.float_fields() if k in pretty_set},
    }, models))


# noinspection PyProtectedMember
def graph_as_data_graph(graph: Graph) -> DataGraph:
    """Convert Graph object to data graph"""
    nodes = []
    relationships = []
    nodes_data = {}
    for node in graph.nodes:  # _id, _properties, _labels
        node_data = {k: v for k, v in node._properties.items() if k in Model.display_fields()}
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


def markdown_anchor_el(text_: t.Optional[str], href_: t.Optional[str], tooltip_: t.Optional[str]) -> t.Optional[str]:
    """Markdown anchor element with optional tooltip"""
    if not text_:
        return text_
    if not href_ and not tooltip_:
        return text_
    if not tooltip_:
        return f'[{text_}]({href_})'
    if not href_:
        return f'[{text_}](# "{tooltip_}")'
    return f'[{text_}]({href_} "{tooltip_}")'


def models_as_dataframe(
        models: t.List[Model],
        display_columns: t.Optional[t.List[DisplayColumnType]] = None,
        pretty: bool = True,
) -> DataFrameDataType:
    """Convert list of Model objects to DataFrame"""
    display_columns = display_columns or Model.display_fields()
    dt_fields = set(Model.dt_fields())
    int_fields = set(Model.int_fields())
    float_fields = set(Model.float_fields())
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
                    value = markdown_anchor_el(model.id, model.url, model.description)
                    datatype_ = 'markdown'
                elif col == 'description':
                    datatype_ = 'markdown'
                    value = pretty_format_description(value, model.private, is_valid_repo_id(model.id), 128)
                elif col == 'author':
                    datatype_ = 'markdown'
                    value = markdown_anchor_el(value, f"https://huggingface.co/{value}", f'Visit {value} profile on HF')
                elif col in dt_fields:
                    value = pretty_format_dt(value)
                elif col in int_fields:
                    value = pretty_format_int(value)
                elif col in float_fields:
                    value = pretty_format_float(value, suffix='%')
                    datatype_ = 'number'
            else:
                if col in int_fields or col in float_fields:
                    datatype_ = 'number'
                elif col in dt_fields:
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


def list_as_choices(simple: list[str]) -> list[tuple[str, str]]:
    """[(name, value),]"""
    return [(Model.field_label(value), value) for value in simple]


def fix_gradio_select_value(v: t.Any, default_: t.Any = None) -> t.Any:
    return default_ if v == [] else v
