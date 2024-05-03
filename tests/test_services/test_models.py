import sys
from loguru import logger
from core.db import DatabaseConnection, Settings
from repositories.graph import GraphRepository
from services.models import ModelService, ListModelsInputDTO, GetModelLineageInputDTO

logger.remove()
logger.add(sink=sys.stderr, level='INFO')


class TestModelService:
    @classmethod
    def setup_class(cls):
        cls.settings = Settings()
        cls.db_conn = DatabaseConnection(cls.settings)
        # cls.teardown_class()
        cls.db_conn.setup()
        cls.service = ModelService(GraphRepository(cls.db_conn))
        cls.db_conn.populate_from_json(cls.settings.project_dir / "tests/test_data/graph.json")

    @classmethod
    def teardown_class(cls):
        cls.db_conn.reset()

    def test_get_model_id_choices(self):
        result = self.service.get_model_id_choices()
        assert 'fblgit/una-cybertron-7b-v2-bf16' in result

    def test_get_license_choices(self):
        result = self.service.get_license_choices()
        assert 'apache-2.0' in result

    def test_get_merge_method_choices(self):
        result = self.service.get_merge_method_choices()
        assert 'slerp' in result

    def test_get_architecture_choices(self):
        result = self.service.get_architecture_choices()
        assert 'MistralForCausalLM' in result

    def test_get_model_lineage(self):
        result = self.service.get_model_lineage(GetModelLineageInputDTO(
            id='fblgit/una-cybertron-7b-v2-bf16'
        ))
        assert len(result.nodes) == 5
        assert len(result.relationships) == 7

    def test_list_models(self):
        result = self.service.list_models(ListModelsInputDTO(
            query='MistralForCausalLM'
        ))
        assert len(result) > 0

    def test_list_models__exclude(self):
        result = self.service.list_models(ListModelsInputDTO(
            license='apache-2.0'
        ))
        assert len(result) == 5
        result = self.service.list_models(ListModelsInputDTO(
            license='apache-2.0',
            exclude='base models'
        ))
        assert len(result) == 1
        result = self.service.list_models(ListModelsInputDTO(
            license='apache-2.0',
            exclude='merged models'
        ))
        assert len(result) == 4

    def test_list_models__sort_by(self):
        result = self.service.list_models(ListModelsInputDTO(
            license='apache-2.0',
            sort_by='most likes',
        ))
        assert len(result) == 5
        assert result[0].likes > result[1].likes > result[-1].likes
