import math
import typing as t
import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout
from bokeh.models import MultiLine, HoverTool, Text, Label, TapTool, OpenURL, CrosshairTool, \
    HelpTool, Plot, ColumnDataSource, Arrow, Range1d, OpenHead, BoxZoomTool, \
    ResetTool, PanTool, WheelZoomTool, SaveTool, WheelPanTool, GraphRenderer, \
    StaticLayoutProvider
from bokeh.plotting import figure
from bokeh.palettes import RdYlGn11, Set3_12
import core.settings
from core.dependencies import get_settings
from utils import pretty_format_dt, pretty_format_int, pretty_format_float, pretty_format_description, is_valid_repo_id
from utils.images import load_image_as_data_uri, load_image_as_np_array
from core.schema import Graph, DerivedFrom, Model
from web.schema import LabelFieldType, ColorFieldType


# ##### Helpers #####
def ld_to_dl(ld: list[dict]) -> dict[str, list]:
    if not ld:
        return {}
    return {k: [d[k] for d in ld] for k in ld[0]}


def dl_to_ld(dl: dict[str, list]) -> list[dict]:
    if not dl:
        return []
    return [dict(zip(dl, x)) for x in zip(*dl.values())]


def get_position_between(a: tuple[float, float], b: tuple[float, float], scaler: float = 0.95) -> tuple[float, float]:
    """Get position of point C between A and B where AC = scaler * AB """
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dist_ab = math.sqrt(dx ** 2 + dy ** 2)
    if dist_ab == 0:
        return a[0], a[1]
    dist_ac = scaler * dist_ab
    unit_dx = dx / dist_ab
    unit_dy = dy / dist_ab
    scaled_dx = unit_dx * dist_ac
    scaled_dy = unit_dy * dist_ac
    return a[0] + scaled_dx, a[1] + scaled_dy


def hash_string(string: t.Optional[str]) -> int:
    hash_value = 0
    if string:
        for char in string:
            hash_value = (hash_value * 31 + ord(char)) % 1000000007
    return hash_value


# ##### Helpers #####


# ##### Graph Manipulation #####


# noinspection PyProtectedMember
def _get_nxg_skeleton(graph: Graph) -> nx.Graph:
    nxg = nx.DiGraph()
    for node in graph.nodes:
        nxg.add_node(node._id)
    for rel in graph.relationships:
        nxg.add_edge(rel._start_node_id, rel._end_node_id)
    return nxg


# noinspection PyProtectedMember
def _get_relationship_groups(relationships: list[DerivedFrom]) -> dict[tuple[int, int], list[DerivedFrom]]:
    grouped_edges: dict[tuple[int, int], list[DerivedFrom]] = {}
    for rel in relationships:
        key = rel._start_node_id, rel._end_node_id
        if key not in grouped_edges:
            grouped_edges[key] = []
        grouped_edges[key].append(rel)
    return grouped_edges


def _get_node_positions(nxg: nx.Graph) -> t.Dict[int, tuple[float, float]]:
    return graphviz_layout(nxg, prog="dot")


def _get_graph_ranges(positions: t.Dict[int, tuple[float, float]]) -> tuple[Range1d, Range1d]:
    if not positions:  # empty graph
        return Range1d(0, 1), Range1d(0, 1)
    x_left, x_right = float("inf"), float("-inf")
    y_bottom, y_top = float("inf"), float("-inf")
    for x, y in positions.values():
        x_left = min(x_left, x)
        x_right = max(x_right, x)
        y_bottom = min(y_bottom, y)
        y_top = max(y_top, y)
    if len(positions) == 1:  # single node
        return Range1d(x_left - 1, x_right + 1), Range1d(y_bottom - 1, y_top + 1)
    return Range1d(x_left, x_right), Range1d(y_bottom, y_top)


def _scale_range(r: Range1d, c: float) -> Range1d:
    w = r.end - r.start
    if w == 0:
        new_w = 10 * c
    else:
        new_w = w * c
    padding = (new_w - w) / 2
    return Range1d(r.start - padding, r.end + padding)


# noinspection PyProtectedMember
def _get_graph_data_sources(
        *,
        graph: Graph,
        positions: dict,
        selected_id: t.Optional[str],
        label_field: t.Optional[LabelFieldType],
        color_field: t.Optional[ColorFieldType],
) -> tuple[ColumnDataSource, ColumnDataSource]:
    relationships = t.cast(list[DerivedFrom], graph.relationships)
    nodes = t.cast(list[Model], graph.nodes)
    grouped_edges: dict[tuple[int, int], list[DerivedFrom]] = _get_relationship_groups(relationships)
    nodes_data: list[dict] = []
    for node in nodes:
        x, y = positions[node._id]
        is_selected = (node.id == selected_id)
        is_merged_model = "MergedModel" in node._labels
        is_permissive_license_label, is_permissive_license_value = get_is_permissive_license(node.license)
        # prepare data
        node_data = {k: v for k, v in node._properties.items() if k in Model.display_fields()}
        # add metadata
        node_data.update({
            # drawing
            "index": node._id,
            "x": x,
            "y": y,
            # meta
            "is_selected": is_selected,
            "is_merged_model": is_merged_model,
            "is_permissive_license": is_permissive_license_value,
            "summary": get_node_summary(node),
        })
        # add styles
        if color_field == "license":
            color_field = "is_permissive_license"
        node_data.update({
            # viz default (glyphs.Text)
            "anchor": "center",
            "text_align": "center",
            "text_baseline": "middle",
            "text_alpha": 1.0,
            "border_line_width": 1.5,
            "border_radius": 24,
            **get_node_styles(
                value=node_data.get(str(color_field) if color_field else None),
                is_selected=is_selected,
                is_merged_model=is_merged_model,
                color_field=color_field,
            ),
        })
        # pretty format fields after computing styles
        node_data.update({
            **{k: pretty_format_dt(getattr(node, k)) for k in Model.dt_fields()},
            **{k: pretty_format_int(getattr(node, k)) for k in Model.int_fields()},
            **{k: pretty_format_float(getattr(node, k), "%") for k in Model.float_fields()},
        })
        # label
        node_data["label"] = node_data.get(str(label_field) if label_field else None) or (" " * 5)
        # legend_label
        if color_field == "is_permissive_license" and is_permissive_license_label is not None:
            node_data["legend_label"] = is_permissive_license_label
        nodes_data.append(node_data)

    rels_data: list[dict] = []
    for edge_key, edge_data in grouped_edges.items():
        start = edge_key[0]
        end = edge_key[1]
        arrow_end = get_position_between(positions[start], positions[end], 0.6)
        cardinality = len(edge_data)
        # prepare data
        rel_data = {
            "type": get_edge_type(edge_data),
            "url": get_edge_extraction_origin(edge_data),
            "summary": get_edge_summary(edge_data),
        }
        # add metadata
        rel_data.update({
            # drawing
            "start": start,
            "end": end,
            "x_start": positions[start][0],
            "y_start": positions[start][1],
            "x_end": positions[end][0],
            "y_end": positions[end][1],
            "arrow_x_start": positions[start][0],
            "arrow_y_start": positions[start][1],
            "arrow_x_end": arrow_end[0],
            "arrow_y_end": arrow_end[1],
            # meta
            "cardinality": cardinality,
        })
        # add styles
        rel_data.update({
            # viz (MultiLine + Arrow with OpenHead)
            **get_edge_styles(cardinality=cardinality),
        })
        rels_data.append(rel_data)
    return ColumnDataSource(data=ld_to_dl(nodes_data)), ColumnDataSource(data=ld_to_dl(rels_data))


# ##### Graph Manipulation #####

# ##### Viz #####

def get_is_permissive_license(license_: t.Optional[str]) -> tuple[t.Optional[str], t.Optional[bool]]:
    """return (legend_label, value) of is_permissive_license"""
    if not license_:
        return None, None  # "Unknown", None
    license_ = license_.lower()
    permissive_licenses = ['mit', 'bsd', 'apache-2.0', 'openrail']
    if any(perm_license in license_ for perm_license in permissive_licenses):
        return 'Permissive', True
    return 'Non commercial', False


def get_edge_summary(grouped_edges: list[DerivedFrom]) -> str:
    cardinality = len(grouped_edges)
    return f"{', '.join([edge.method for edge in grouped_edges])} ({cardinality})"


def get_edge_extraction_origin(grouped_edges: list[DerivedFrom]) -> str:
    return grouped_edges[0].origin


# noinspection PyProtectedMember
def get_edge_type(grouped_edges: list[DerivedFrom]) -> str:
    return grouped_edges[0]._type


def get_edge_styles(*, cardinality: int) -> dict:
    styles = {
        "line_color": "black",
        "line_alpha": 0.35,
        "line_width": 4,
        "legend_label": "Cardinality = 1",
    }
    if cardinality == 2:
        styles.update({
            "line_alpha": 2 / 3,
            "legend_label": "Cardinality = 2",
        })
    if cardinality > 2:
        styles.update({
            "line_alpha": 1.0,
            "legend_label": "Cardinality > 2",
        })
    return styles


def get_node_summary(node: Model, max_length: int = 96) -> str:
    return pretty_format_description(node.description, node.private, is_valid_repo_id(node.id), max_length)


def get_node_styles(
        *,
        value: t.Union[None, str, bool, float, int],
        is_selected: bool,
        is_merged_model: bool,
        color_field: t.Optional[str] = None,
) -> dict:
    styles = {
        "background_fill_color": "beige",
        "border_line_color": "beige",
        "text_font_size": "12px",
        "text_font_style": "normal",
        "padding": 8,
        "text_color": "black",
        "legend_label": None,
    }
    if value is None:
        styles.update({
            "background_fill_color": "beige",
            "border_line_color": "beige",
            "legend_label": "Undefined",
        })
    elif isinstance(value, bool):
        bool_mapper = {
            True: {
                'background_fill_color': 'lightgreen',
                "border_line_color": "lightgreen",
                "legend_label": "True",
            },
            False: {
                'background_fill_color': '#ffa5a5',
                "border_line_color": "#ffa5a5",
                "legend_label": "False",
            }
        }
        styles.update(bool_mapper[value])
    elif isinstance(value, float) or isinstance(value, int):
        number_mapper = {
            0: {
                'background_fill_color': "#801500",
                "border_line_color": "#801500",
                "text_color": "white",
            },
            1: {
                'background_fill_color': RdYlGn11[10],
                "border_line_color": RdYlGn11[10],
                "text_color": "white",
            },
            2: {
                'background_fill_color': RdYlGn11[9],
                "border_line_color": RdYlGn11[9],
                "text_color": "black",
            },
            3: {
                'background_fill_color': RdYlGn11[8],
                "border_line_color": RdYlGn11[8],
                "text_color": "black",
            },
            4: {
                'background_fill_color': RdYlGn11[7],
                "border_line_color": RdYlGn11[7],
                "text_color": "black",
            },
            5: {
                'background_fill_color': RdYlGn11[6],
                "border_line_color": RdYlGn11[6],
                "text_color": "black",
            },
            6: {
                'background_fill_color': RdYlGn11[5],
                "border_line_color": RdYlGn11[5],
                "text_color": "black",
            },
            7: {
                'background_fill_color': RdYlGn11[4],
                "border_line_color": RdYlGn11[4],
                "text_color": "black",
            },
            8: {
                'background_fill_color': RdYlGn11[3],
                "border_line_color": RdYlGn11[3],
                "text_color": "black",
            },
            9: {
                'background_fill_color': RdYlGn11[2],
                "border_line_color": RdYlGn11[2],
                "text_color": "black",
            },
            10: {
                'background_fill_color': RdYlGn11[1],
                "border_line_color": RdYlGn11[1],
                "text_color": "white",
            },
            11: {
                'background_fill_color': RdYlGn11[0],
                "border_line_color": RdYlGn11[0],
                "text_color": "white",
            }
        }
        if isinstance(value, float):  # scores in [0.0 - 1.0]
            if value <= 0.0:
                value_class = 0
            elif value >= 1.0:
                value_class = len(number_mapper) - 1
            else:
                value_class = int(value * 10) + 1
            legend_label_mapper = [
                "0%",
                "]0 - 10%[",
                "[10% - 20%[",
                "[20% - 30%[",
                "[30% - 40%[",
                "[40% - 50%[",
                "[50% - 60%[",
                "[60% - 70%[",
                "[70% - 80%[",
                "[80% - 90%[",
                "[90% - 100%[",
                "100%",
            ]
            legend_label = legend_label_mapper[value_class]
        else:  # int: likes, downloads
            value_class, legend_label = None, None
            classes_max = [0, 3, 5, 10, 20, 50, 100, 250, 500, 1000, 10000]
            if color_field == "downloads":
                classes_max = [0, 10, 50, 100, 500, 1000, 5000, 10000, 100000, 1000000, 10000000]
            if value <= 0:
                value_class = 0
                legend_label = "0"
            elif value >= classes_max[-1]:
                value_class = len(number_mapper) - 1
                legend_label = f"+{pretty_format_int(classes_max[-1])}"
            if value_class is None:
                for v_c, c_max in enumerate(classes_max):
                    if value < c_max:
                        value_class = v_c
                        break
                legend_label = (f"[{pretty_format_int(classes_max[value_class - 1])} - "
                                f"{pretty_format_int(classes_max[value_class])}[")
        styles.update(number_mapper[value_class], legend_label=legend_label)
    else:
        palette = Set3_12
        color_index = hash_string(str(value)) % len(palette)
        styles.update({
            'background_fill_color': palette[color_index],
            "border_line_color": palette[color_index],
            "text_color": "black",
            "legend_label": str(value),
        })
    merged_mapper = {
        True: {
            "text_font_size": "12px",
            "text_font_style": "italic",
            "padding": 8,
        },
        False: {
            "text_font_size": "12px",
            "text_font_style": "bold",
            "padding": 12,
        }
    }
    styles.update(merged_mapper[is_merged_model])
    selected_mapper = {
        True: {"border_line_color": "black"},
        False: {},
    }
    styles.update(selected_mapper[is_selected])
    return styles


# ##### Viz #####


class GraphPlotBuilder:
    settings: core.settings.Settings
    # in
    graph: Graph
    selected_id: t.Optional[str]
    label_field: t.Optional[LabelFieldType]
    color_field: t.Optional[ColorFieldType]
    # out
    p: Plot

    def __init__(
            self,
            graph: Graph,
            selected_id: t.Optional[str] = None,
            label_field: t.Optional[LabelFieldType] = None,
            color_field: t.Optional[ColorFieldType] = None,
    ):
        self.settings = get_settings()
        self.graph = graph
        self.selected_id = selected_id
        self.label_field = label_field
        self.color_field = color_field

    def icon(self, name: str) -> str:
        icon_path = self.settings.project_dir / 'static' / 'icons' / f'{name}.svg'
        return load_image_as_data_uri(icon_path)

    def mergeui_icon(self) -> str:
        icon_path = self.settings.project_dir / 'static' / 'brand' / 'icon.svg'
        return load_image_as_data_uri(icon_path)

    def mergeui_logo(self) -> tuple:
        logo_path = self.settings.project_dir / 'static' / 'brand' / 'logo.png'
        return load_image_as_np_array(logo_path)

    def _set_plot_layout(self, aspect_ratio: float, background_fill_color: str):
        self.p.sizing_mode = "stretch_both"
        self.p.aspect_ratio = aspect_ratio
        self.p.background_fill_color = background_fill_color
        self.p.grid.grid_line_color = None

    def _set_plot_title(self, title: str):
        self.p.title.text = title
        self.p.title.align = "center"
        self.p.title.text_align = 'center'
        self.p.title.text_baseline = 'middle'
        self.p.title.text_font_size = "16px"
        self.p.title.text_font_style = "bold"

    def _set_plot_toolbar(self):
        self.p.width_policy = 'max'
        self.p.toolbar.logo = None
        self.p.toolbar_location = 'right'
        self.p.tools = [
            *([
                  PanTool(
                      description="Drag to move around",
                  ),
                  WheelPanTool(
                      description="Scroll to move around",
                  ),
                  BoxZoomTool(description="Select area to zoom"),
                  WheelZoomTool(description="Scroll to zoom in/out"),
                  CrosshairTool(
                      description="Show reticle",
                      line_color="grey",
                      line_alpha=0.5,
                      line_width=0.5,
                  ),
                  SaveTool(description="Export plot as png", icon=self.icon('export')),
                  ResetTool(description="Reset Zoom/Center", icon=self.icon('center'))
              ] if not self.is_empty() else []),
            HelpTool(
                description="Source code in GitHub",
                redirect=f"{self.settings.repo_url}",
                icon=self.icon('github'),
            ),
            HelpTool(
                description=f"{self.settings.project_name}",
                redirect=f"{self.settings.repo_url}",
                icon=self.mergeui_icon(),
            ),
        ]

    def _add_graph_renderer(self, positions: dict[int, tuple[float, float]], nodes_data_source: ColumnDataSource,
                            edges_data_source: ColumnDataSource):
        graph_renderer = GraphRenderer(name="graph_renderer")
        if self.graph.nodes:
            graph_renderer.node_renderer.glyph = Text(
                text="label",
                background_fill_color="background_fill_color",
                border_line_color="border_line_color",
                text_color="text_color",
                text_font_style="text_font_style",
                text_font_size="text_font_size",
                padding=8,  # can't be dynamic
                anchor="anchor",
                text_align="text_align",
                text_baseline="text_baseline",
                text_alpha="text_alpha",
                border_line_width="border_line_width",
                border_radius=24,  # can't be dynamic
            )
            graph_renderer.node_renderer.data_source = nodes_data_source
        if self.graph.relationships:
            graph_renderer.edge_renderer.glyph = MultiLine(
                line_color="line_color",
                line_alpha="line_alpha",
                line_width="line_width",
            )
            graph_renderer.edge_renderer.data_source = edges_data_source
            arrows = Arrow(
                name="arrows_renderer",
                end=OpenHead(
                    line_color="line_color",
                    line_alpha="line_alpha",
                    line_width="line_width",
                    line_cap='round',
                    line_join="round",
                ),
                line_color="transparent",
                source=edges_data_source,
                x_start="arrow_x_start", y_start="arrow_y_start", x_end="arrow_x_end", y_end="arrow_y_end",
            )
            self.p.add_layout(arrows)
        graph_renderer.layout_provider = StaticLayoutProvider(graph_layout=positions)
        self.p.renderers.append(graph_renderer)

    def _add_click_tools(self):
        for graph_renderer in self.p.select(name="graph_renderer"):
            click_icon = self.icon('click')
            if self.graph.nodes:
                self.p.add_tools(TapTool(
                    icon=click_icon,
                    description="Click node to open url",
                    renderers=[graph_renderer.node_renderer],
                    callback=OpenURL(url='@url'),
                ))
            if self.graph.relationships:
                self.p.add_tools(TapTool(
                    icon=click_icon,
                    description="Click edge to open origin url",
                    renderers=[graph_renderer.edge_renderer],
                    callback=OpenURL(url='@url'),
                ))

    def _add_hover_tools(self):
        hidden_fields = {'url', 'name', 'description', 'author', 'created_at', 'evaluated_at'}
        tooltips = ([('', '@summary')] +
                    [(Model.field_label(x), f"@{x}") for x in Model.display_fields() if x not in hidden_fields])
        for graph_renderer in self.p.select(name="graph_renderer"):
            hover_icon = self.icon('tooltip')
            if self.graph.nodes:
                self.p.add_tools(HoverTool(
                    tooltips=tooltips,
                    renderers=[graph_renderer.node_renderer],
                    line_policy='interp',
                    show_arrow=False,
                    description="Hover over nodes to see details",
                    icon=hover_icon,
                ))
            if self.graph.relationships:
                self.p.add_tools(HoverTool(
                    tooltips=[('', '@type'), ('Extracted From', '@summary')],
                    renderers=[graph_renderer.edge_renderer],
                    line_policy='interp',
                    show_arrow=False,
                    description="Hover over edges to see details",
                    icon=hover_icon,
                ))

    def _set_plot_ranges(self, graph_range_x: Range1d, graph_range_y: Range1d):
        self.p.x_range = _scale_range(graph_range_x, 1.5)
        self.p.y_range = _scale_range(graph_range_y, 1.35)

    def _hide_plot_axis(self):
        self.p.xaxis.visible = False
        self.p.yaxis.visible = False

    def _add_text_watermark(self):
        w = self.p.x_range.end - self.p.x_range.start
        h = self.p.y_range.end - self.p.y_range.start
        scaler = 0.1
        self.p.add_layout(Label(
            x=self.p.x_range.start + w * scaler,
            y=self.p.y_range.start + h * scaler,
            x_units='screen',
            y_units='screen',
            text=f"Generated by {self.settings.project_name}",
            text_font_size="12pt",
            text_align="left",
            text_baseline="bottom",
            text_font_style="normal",
            text_alpha=0.5,
            # anchor="center", # v3.4.1
            # padding=10, # v3.4.1
            # border_radius=5, # v3.4.1
            # border_line_color="black", # v3.4.1
            # background_fill_color="white", # v3.4.1
        ))

    def _add_image_watermark(self):
        np_arr, img_w, img_h = self.mergeui_logo()
        w = self.p.x_range.end - self.p.x_range.start
        h = self.p.y_range.end - self.p.y_range.start
        x_center = self.p.x_range.start + w / 2
        y_center = self.p.y_range.start + h / 2
        scaler = 0.75
        self.p.image_rgba(
            image=[np_arr],
            x=x_center, y=y_center,
            dw=img_w * scaler, dh=img_h * scaler,
            anchor="center",
            dh_units="screen",
            dw_units="screen",
            global_alpha=0.075,
        )

    def _add_plot_legend(self):
        for graph_renderer in self.p.select(name="graph_renderer"):
            # _TODO: sort legend items
            if self.graph.nodes:
                self.p.circle(
                    'x',
                    'y',
                    visible=False,
                    color='background_fill_color',
                    legend_group='legend_label',
                    source=graph_renderer.node_renderer.data_source,
                )
            if self.graph.relationships:
                self.p.multi_line(
                    'x_start',
                    'y_start',
                    visible=False,
                    line_color="line_color",
                    line_alpha="line_alpha",
                    line_width="line_width",
                    legend_group='legend_label',
                    source=graph_renderer.edge_renderer.data_source,
                )
            if self.p.legend:
                # self.p.legend.location = "top_left"
                # self.p.legend.ncols = 2
                # self.p.legend.nrows = 2
                self.p.legend.title = Model.field_label(self.color_field) if self.color_field else None

    def is_empty(self) -> bool:
        return not self.graph or not self.graph.nodes

    def build(self) -> Plot:
        nxg = _get_nxg_skeleton(self.graph)
        positions = _get_node_positions(nxg)
        nodes_data_source, edges_data_source = _get_graph_data_sources(
            graph=self.graph,
            positions=positions,
            selected_id=self.selected_id,
            label_field=self.label_field,
            color_field=self.color_field,
        )
        range_x, range_y = _get_graph_ranges(positions)
        self.p = figure()
        self._set_plot_title(f"{self.selected_id}'s Merge Lineage" if self.selected_id else "Merge Lineage")
        self._set_plot_toolbar()
        self._set_plot_layout(1.85 / 1.0, "white")
        self._set_plot_ranges(range_x, range_y)
        self._add_image_watermark()
        self._add_text_watermark()
        self._add_graph_renderer(positions, nodes_data_source, edges_data_source)
        self._add_click_tools()
        self._add_hover_tools()
        self._add_plot_legend()
        self._hide_plot_axis()
        return self.p
