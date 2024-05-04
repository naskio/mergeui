import typing as t
import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout
import math
from bokeh.plotting import figure
from bokeh.models import MultiLine, HoverTool, Text, Label, TapTool, OpenURL, CrosshairTool, \
    HelpTool, Plot, ColumnDataSource, Arrow, Range1d, OpenHead, BoxZoomTool, \
    ResetTool, PanTool, WheelZoomTool, SaveTool, WheelPanTool, GraphRenderer, \
    StaticLayoutProvider
from core.settings import Settings
from core.schema import Graph, DerivedFrom, Model
from utils import format_datetime
from web.schema import ColumnType
from utils.images import load_image_as_data_uri, load_image_as_np_array


# ##### Helpers #####


def _get_nxg_skeleton(graph: Graph) -> nx.Graph:
    nxg = nx.DiGraph()
    for node in graph.nodes:
        nxg.add_node(node._id)
    for rel in graph.relationships:
        nxg.add_edge(rel._start_node_id, rel._end_node_id)
    return nxg


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


def _get_graph_data_sources(model_id: str, graph: Graph, positions: dict) -> tuple[ColumnDataSource, ColumnDataSource]:
    relationships = t.cast(list[DerivedFrom], graph.relationships)
    nodes = t.cast(list[Model], graph.nodes)
    grouped_edges: dict[tuple[int, int], list[DerivedFrom]] = _get_relationship_groups(relationships)
    nodes_data: list[dict] = []
    for node in nodes:
        x, y = positions[node._id]
        is_selected = node.id == model_id
        is_merged_model = "MergedModel" in node._labels
        is_permissive_license = get_is_permissive_license(node.license)
        nodes_data.append({
            "index": node._id,
            "x": x,
            "y": y,
            # properties
            **node.dict(include=set(t.get_args(ColumnType)), exclude={"created_at", "updated_at"}),
            "created_at": format_datetime(node.created_at),
            "updated_at": format_datetime(node.updated_at),
            # meta
            "is_selected": is_selected,
            "is_merged_model": is_merged_model,
            "is_permissive_license": is_permissive_license,
            # viz (glyphs.Text)
            "anchor": "center",
            "text_align": "center",
            "text_baseline": "middle",
            "text_alpha": 1.0,
            "border_line_width": 1.5,
            "border_radius": 24,
            **get_node_styles(is_selected, is_merged_model, is_permissive_license),
        })
    rels_data: list[dict] = []
    for edge_key, edge_data in grouped_edges.items():
        start = edge_key[0]
        end = edge_key[1]
        arrow_end = get_position_between(positions[start], positions[end], 0.6)
        cardinality = len(edge_data)
        rels_data.append({
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
            # properties
            "type": get_edge_type(edge_data),
            "extracted_from": get_edge_extraction_method(edge_data),
            "url": get_edge_extraction_origin(edge_data),
            # meta
            "cardinality": cardinality,
            # viz (MultiLine + Arrow with OpenHead)
            **get_edge_styles(cardinality),
        })
    return ColumnDataSource(data=ld_to_dl(nodes_data)), ColumnDataSource(data=ld_to_dl(rels_data))


def _get_graph_ranges(positions: t.Dict[int, tuple[float, float]]) -> tuple[Range1d, Range1d]:
    x_left, x_right = float("inf"), float("-inf")
    y_bottom, y_top = float("inf"), float("-inf")
    for x, y in positions.values():
        x_left = min(x_left, x)
        x_right = max(x_right, x)
        y_bottom = min(y_bottom, y)
        y_top = max(y_top, y)
    return Range1d(x_left, x_right), Range1d(y_bottom, y_top)


def _scale_range(r: Range1d, c: float = 1.3) -> Range1d:
    w = r.end - r.start
    new_w = w * c
    padding = (new_w - w) / 2
    return Range1d(r.start - padding, r.end + padding)


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
    dist_ac = scaler * dist_ab
    unit_dx = dx / dist_ab
    unit_dy = dy / dist_ab
    scaled_dx = unit_dx * dist_ac
    scaled_dy = unit_dy * dist_ac
    return a[0] + scaled_dx, a[1] + scaled_dy


# ##### Helpers #####

# ##### Viz #####

def get_is_permissive_license(license_: str) -> t.Optional[bool]:
    license_ = license_.lower()
    permissive_licenses = ['mit', 'bsd', 'apache-2.0', 'openrail']
    if any(perm_license in license_ for perm_license in permissive_licenses):
        return True
    # commercial_licenses = []
    # if any(comm_license in license_ for comm_license in commercial_licenses):
    #     return False
    return False


def get_node_styles(is_selected: bool, is_merged_model: bool, is_permissive_license: t.Optional[bool]) -> dict:
    license_mapper = {
        True: {
            'background_fill_color': 'lightgreen',
            "border_line_color": "lightgreen",
        },
        False: {
            'background_fill_color': '#ffa5a5',
            "border_line_color": "#ffa5a5",
        },
        None: {
            'background_fill_color': 'beige',
            "border_line_color": "beige",
        },
    }
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
        },
    }
    selected_mapper = {
        True: {
            "border_line_color": "black",
            "text_color": "black",
        },
        False: {
            "text_color": "black",
        },
    }
    return {
        **license_mapper[is_permissive_license],
        **merged_mapper[is_merged_model],
        **selected_mapper[is_selected],
    }


def get_edge_styles(cardinality: int) -> dict:
    if cardinality > 1:
        return {
            "line_color": "black",
            "line_alpha": cardinality / 3,
            "line_width": 4,
        }
    return {
        "line_color": "black",
        "line_alpha": 0.35,
        "line_width": 4,
    }


def get_edge_extraction_method(grouped_edges: list[DerivedFrom]) -> str:
    cardinality = len(grouped_edges)
    return f"{', '.join([edge.method for edge in grouped_edges])} ({cardinality})"


def get_edge_extraction_origin(grouped_edges: list[DerivedFrom]) -> str:
    return grouped_edges[0].origin


def get_edge_type(grouped_edges: list[DerivedFrom]) -> str:
    return grouped_edges[0]._type


# ##### Viz #####


class GraphPlotBuilder:
    model_id: str
    graph: Graph
    settings: Settings
    p: Plot

    def __init__(self, settings: Settings):
        self.settings = settings

    def icon(self, name: str) -> str:
        icon_path = self.settings.project_dir / 'static' / 'icons' / f'{name}.svg'
        return load_image_as_data_uri(icon_path)

    def mergeui_logo(self) -> tuple:
        logo_path = self.settings.project_dir / 'static' / 'brand' / 'logo.png'
        return load_image_as_np_array(logo_path)

    def _set_plot_layout(self):
        self.p.sizing_mode = "stretch_both"
        self.p.aspect_ratio = 1.85 / 1.0
        self.p.background_fill_color = "white"
        self.p.grid.grid_line_color = None

    def _set_plot_title(self):
        self.p.title.text = f"{self.model_id}'s Merge Lineage"
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
            ResetTool(description="Reset Zoom/Center", icon=self.icon('center')),
            HelpTool(
                description="Source code in GitHub",
                redirect="https://github.com/naskio/mergeui",
                icon=self.icon('github'),
            ),
            HelpTool(
                description="MergeUI",
                redirect="https://github.com/naskio/mergeui",
                icon=self.icon('mergeui'),
            ),
        ]

    def _add_graph_renderer(self, positions: dict[int, tuple[float, float]], nodes_data_source: ColumnDataSource,
                            edges_data_source: ColumnDataSource):
        graph_renderer = GraphRenderer(name="graph_renderer")
        if self.graph.nodes:
            graph_renderer.node_renderer.glyph = Text(
                text="id",
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
        for graph_renderer in self.p.select(name="graph_renderer"):
            hover_icon = self.icon('tooltip')
            if self.graph.nodes:
                self.p.add_tools(HoverTool(
                    tooltips=list(map(lambda x: (x, f"@{x}"), [x for x in t.get_args(ColumnType) if x not in ['url']])),
                    renderers=[graph_renderer.node_renderer],
                    line_policy='interp',
                    show_arrow=False,
                    description="Hover over nodes to see details",
                    icon=hover_icon,
                ))
            if self.graph.relationships:
                self.p.add_tools(HoverTool(
                    tooltips=[('', '@type'), ('origin', '@extracted_from')],
                    renderers=[graph_renderer.edge_renderer],
                    line_policy='interp',
                    show_arrow=False,
                    description="Hover over edges to see details",
                    icon=hover_icon,
                ))

    def _set_plot_ranges(self, graph_range_x: Range1d, graph_range_y: Range1d):
        self.p.x_range = _scale_range(graph_range_x, 1.25)
        self.p.y_range = _scale_range(graph_range_y, 1.25)

    def _add_text_watermark(self):
        w = self.p.x_range.end - self.p.x_range.start
        h = self.p.y_range.end - self.p.y_range.start
        scaler = 0.05
        self.p.add_layout(Label(
            x=self.p.x_range.start + w * scaler,
            y=self.p.y_range.start + h * scaler,
            x_units='screen',
            y_units='screen',
            text="Generated by MergeUI",
            text_font_size="12pt",
            text_align="left",
            text_baseline="bottom",
            text_font_style="normal",
            text_alpha=0.8,
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
        if self.graph.nodes:
            source = ColumnDataSource(
                dict(
                    x=[0, 0, 0],
                    y=[0, 0, 0],
                    color=['lightgreen', '#ffa5a5', 'beige'],
                    label=['Permissive', 'Non commercial', 'Unknown'],
                )
            )
            self.p.circle('x', 'y', visible=False, radius=1.5, color='color', legend_group='label', source=source)
        if self.graph.relationships:
            source = ColumnDataSource(
                dict(
                    x=[0, 0, 0],
                    y=[0, 0, 0],
                    line_alpha=[0.35, 2 / 3, 1],
                    label=['Cardinality = 1', 'Cardinality = 2', 'Cardinality > 2'],
                )
            )
            self.p.multi_line('x', 'y', visible=False, line_alpha='line_alpha', line_width=4, line_color="black",
                              legend_group='label', source=source)
        if self.p.legend:
            self.p.legend.title = "License"

    def build(self, model_id: str, graph: Graph) -> Plot:
        self.model_id = model_id
        self.graph = graph
        nxg = _get_nxg_skeleton(self.graph)
        positions = _get_node_positions(nxg)
        nodes_data_source, edges_data_source = _get_graph_data_sources(self.model_id, self.graph, positions)
        range_x, range_y = _get_graph_ranges(positions)
        self.p = figure()
        self._set_plot_title()
        self._set_plot_toolbar()
        self._set_plot_layout()
        self._set_plot_ranges(range_x, range_y)
        self._add_image_watermark()
        self._add_text_watermark()
        self._add_graph_renderer(positions, nodes_data_source, edges_data_source)
        self._add_click_tools()
        self._add_hover_tools()
        self._add_plot_legend()
        return self.p