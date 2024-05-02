from core.base import BaseRepository
import gqlalchemy as gq
from gqlalchemy.vendors.database_client import DatabaseClient
from gqlalchemy.query_builders.memgraph_query_builder import Order


class GraphRepository(BaseRepository):
    def __init__(self, db: DatabaseClient):
        self.db = db

    def get_distinct_property_values(self, key: str = "id", label: str = "") -> list[str]:
        q = (gq.match()
             .node(labels=f"{label}", variable="n")
             .return_(f"DISTINCT n.{key} as v")
             .order_by(properties=[("v", Order.ASC)]))
        return list(map(lambda x: x.get("v"), q.execute()))
