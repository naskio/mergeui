import sys
from loguru import logger
import gqlalchemy as gq
from core.db import DatabaseConnection, Settings
from repositories.graph import GraphRepository

logger.remove()
logger.add(sink=sys.stderr, level='INFO')


class TestGraphRepository:
    @classmethod
    def setup_class(cls):
        cls.settings = Settings()
        cls.db_conn = DatabaseConnection(cls.settings)
        # cls.teardown_class()
        cls.db_conn.setup()
        cls.repository = GraphRepository(cls.db_conn)
        cls.db_conn.populate_from_json(cls.settings.project_dir / "tests/test_data/graph.json")

    @classmethod
    def teardown_class(cls):
        cls.db_conn.reset()

    def test_list_property_values(self):
        license_choices = self.repository.list_property_values('license')
        assert 'apache-2.0' in license_choices
        assert license_choices == sorted(license_choices)

    def test_list_nodes(self):
        result = self.repository.list_nodes()
        assert len(result) == 6
        assert isinstance(result[0], gq.Node)
        # limit
        result = self.repository.list_nodes(limit=2)
        assert len(result) == 2

    def test_list_models(self):
        # get all
        result = self.repository.list_models()
        assert len(result) == 6
        assert isinstance(result[0], gq.Node)
        # limit
        result = self.repository.list_models(limit=2)
        assert len(result) == 2
        # get by license only
        result = self.repository.list_models(license_='cc-by-nc-4.0')
        assert len(result) == 1
        # get by search query only
        result = self.repository.list_models('cc-by-nc')
        assert len(result) == 1
        # get by license and architecture
        result = self.repository.list_models(license_='cc-by-nc-4.0', architecture="MistralForCausalLM")
        assert len(result) == 1
        result = self.repository.list_models(license_='cc-by-nc-4.0', architecture="NotFound")
        assert len(result) == 0
        # exclude
        result = self.repository.list_models(license_='apache-2.0')
        assert len(result) == 5
        result = self.repository.list_models(license_='apache-2.0', label="MergedModel")
        assert len(result) == 1
        result = self.repository.list_models(license_='apache-2.0', not_label="MergedModel")
        assert len(result) == 4
        # base_model
        result = self.repository.list_models(license_='apache-2.0', label="MergedModel",
                                             base_model="fblgit/una-cybertron-7b-v2-bf16")
        assert len(result) == 1
        result = self.repository.list_models(
            license_='apache-2.0', label="MergedModel",
            base_model="mistralai/Mistral-7B-v0.1")
        assert len(result) == 0
        # get by search query only
        result = self.repository.list_models('hola')
        assert len(result) == 0
        result = self.repository.list_models('hola', license_='apache-2.0')
        assert len(result) == 0
        # search query with license
        result = self.repository.list_models('cc-by-nc', license_='cc-by-nc-4.0')
        assert len(result) == 1
        result = self.repository.list_models('MistralForCausalLM', license_='apache-2.0')
        assert len(result) == 5
        # merge_method
        result = self.repository.list_models(merge_method='slerp')
        assert len(result) == 2

    def test_get_sub_graph(self):
        # top node
        gr = self.repository.get_sub_graph('Q-bert/MetaMath-Cybertron-Starling')
        assert len(gr.nodes) == 5
        assert isinstance(gr.nodes[0], gq.Node)
        assert len(gr.relationships) == 7
        assert isinstance(gr.relationships[0], gq.Relationship)
        # isolated node
        gr = self.repository.get_sub_graph('mistralai/Mistral-7B-v0.1')
        assert len(gr.nodes) == 1
        assert len(gr.relationships) == 0
        # invalid node
        gr = self.repository.get_sub_graph('x/y')
        assert len(gr.nodes) == 0
        assert len(gr.relationships) == 0
        # middle node
        gr = self.repository.get_sub_graph('Q-bert/MetaMath-Cybertron')
        assert len(gr.nodes) == 5
        assert len(gr.relationships) == 7
        # bottom node
        gr = self.repository.get_sub_graph('berkeley-nest/Starling-LM-7B-alpha')
        assert len(gr.nodes) == 5
        assert len(gr.relationships) == 7
        # empty id
        gr = self.repository.get_sub_graph('')
        assert len(gr.nodes) == 0
        assert len(gr.relationships) == 0
