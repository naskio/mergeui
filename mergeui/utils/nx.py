import json
from loguru import logger
from pathlib import Path
import networkx as nx
from gqlalchemy.vendors.database_client import DatabaseClient
from gqlalchemy.transformations.translators.nx_translator import NxTranslator
from mergeui.utils import log_progress


def preview_nx_graph(graph: nx.Graph) -> None:
    logger.info(f"Preview of: {graph}")
    logger.info(f"Nodes: {graph.number_of_nodes()}")
    logger.debug(f"Node IDs: {graph.nodes}")
    for node in graph.nodes(data=True):
        logger.trace(f"{node}")
    logger.info(f"Edges: {graph.number_of_edges()}")
    logger.debug(f"Edge IDs: {graph.edges}")
    for edge in graph.edges(data=True):
        logger.trace(f"{edge}")


def convert_nx_graph_to_dict(graph: nx.Graph) -> dict:
    json_graph: dict = {
        "directed": graph.is_directed(),
        "multigraph": graph.is_multigraph(),
        "nodes_count": graph.number_of_nodes(),
        "relationships_count": graph.number_of_edges(),
        "nodes": [],
        "relationships": [],
    }
    for node_for_adding, node_attributes in graph.nodes(data=True):
        json_graph["nodes"].append({**(node_attributes or {}), "id": node_for_adding})
    for source, target, edge_attributes in graph.edges(data=True):
        json_graph["relationships"].append({**(edge_attributes or {}), "source": source, "target": target})
    return json_graph


def save_nx_graph_to_json_file(graph: nx.Graph, json_path: Path) -> None:
    logger.info(f"Saving graph to: {json_path}")
    json_graph = convert_nx_graph_to_dict(graph)
    json_path.write_text(json.dumps(json_graph, indent=4))  # _TODO: handle dt.datetime fields serialization


def load_nx_graph_from_json_file(json_path: Path) -> nx.Graph:
    logger.info(f"Loading graph from: {json_path}")
    json_graph = json.loads(json_path.read_text())
    graph = nx.MultiDiGraph()
    nodes = json_graph.get("nodes", [])
    relationships = json_graph.get("relationships", [])
    excluded_keys = []  # ["id", "labels"]
    for node in nodes:
        # _TODO: handle dt.datetime fields parsing
        graph.add_node(node["id"], **{k: v for k, v in node.items() if k not in excluded_keys and v is not None})
    excluded_keys = ["source", "target"]
    for rel in relationships:
        graph.add_edge(rel["source"], rel["target"],
                       **{k: v for k, v in rel.items() if k not in excluded_keys and v is not None})
    return graph


# noinspection PyProtectedMember
def get_nx_translator(db: DatabaseClient) -> NxTranslator:
    return NxTranslator(
        host=db.host,
        port=db.port,
        username=db._username,
        password=db._password,
        encrypted=db._encrypted,
        client_name=db._client_name,
    )


def import_nx_graph_to_db(graph: nx.Graph, db: DatabaseClient) -> None:
    logger.info("Importing graph...")
    translator = get_nx_translator(db)
    queries = list(translator.to_cypher_queries(graph))
    logger.debug(f"Executing {len(queries)} queries")
    total = len(queries)
    for ind, query in enumerate(queries):
        logger.trace(f"{query}")
        db.execute(query)
        log_progress(ind, total, step=5)
    if queries:
        logger.success(f"Graph imported")
    else:
        logger.warning(f"Nothing to import")


def export_db_as_nx_graph(db: DatabaseClient) -> nx.Graph:
    logger.info("Exporting graph...")
    translator = get_nx_translator(db)
    # NB: doesn't support multiple edges between nodes (only one exported if we have multiple edges between nodes)
    graph = translator.get_instance()
    fixed_graph = nx.MultiDiGraph()
    for node_for_adding_, node_attrs in graph.nodes(data=True):
        new_node_for_adding = node_attrs["id"] or node_for_adding_
        new_attrs = {k: v for k, v in node_attrs.items() if k != "label"}
        if node_attrs.get("label"):
            new_attrs["labels"] = str(node_attrs["label"]).split(":")
        fixed_graph.add_node(new_node_for_adding, **new_attrs)
    for start, end, edge_attrs in graph.edges(data=True):
        id_src = graph.nodes[start]["id"]
        id_dst = graph.nodes[end]["id"]
        fixed_graph.add_edge(id_src, id_dst, **edge_attrs)
    return fixed_graph
