import pytest
import pprint
from huggingface_hub import hf_api
from utils.hub import list_hf_models, get_hf_model_by_id, download_mergekit_config_yaml_file, \
    download_readme_markdown_file, load_model_card, get_data_origin
from core.settings import Settings

settings = Settings()


@pytest.fixture(scope="session")
def public_model_id() -> str:
    return "mlabonne/Zebrafish-7B"


@pytest.fixture(scope="session")
def gated_model_id() -> str:
    return "meta-llama/Meta-Llama-3-8B"


@pytest.fixture(scope="session")
def public_repo_listing_model_info() -> hf_api.ModelInfo:
    print('public_repo_listing_model_info')
    model = list_hf_models(
        author='mlabonne',
        model_name="Zebrafish-7B",
        tags=['arxiv:2403.19522', 'merge'],
        sort="lastModified",
        limit=1,
    )[0]
    pprint.pprint(model)
    return model


@pytest.fixture(scope="session")
def gated_repo_listing_model_info() -> hf_api.ModelInfo:
    print('gated_repo_listing_model_info')
    model = list_hf_models(
        author='meta-llama',
        model_name="Meta-Llama-3-8B",
        tags='llama-3',
        limit=1,
    )[0]
    pprint.pprint(model)
    return model


def test_list_hf_models():
    limit = 10
    tag = "merge"
    models = list_hf_models(tags=tag, limit=limit)
    # print('list_hf_models')
    # pprint.pprint(models)
    assert len(models) == limit
    assert all([tag in model.tags for model in models])


def test_list_hf_models__filtered(
        public_model_id, public_repo_listing_model_info,
        gated_model_id, gated_repo_listing_model_info
):
    models = [public_repo_listing_model_info, gated_repo_listing_model_info]
    for model in models:
        # none
        assert model.disabled is None
        # others
        assert model.last_modified is not None
        assert model.author is not None
        assert model.gated is not None
        assert model.id in [public_model_id, gated_model_id]
        assert model.tags
        assert model.downloads >= 0
        assert model.likes >= 0
        assert model.created_at is not None
        assert model.private is False
        assert model.pipeline_tag is not None
        assert model.card_data is not None
        assert model.card_data.model_name is None
        assert model.card_data.license is not None
        assert model.config is not None
        assert model.config.get("architectures", [None])[0] is not None


def test_get_hf_model_by_id(public_model_id, public_repo_listing_model_info):
    model = get_hf_model_by_id(public_repo_listing_model_info)
    print('get_hf_model_by_id')
    pprint.pprint(model)
    assert model.id == public_model_id
    assert model != public_repo_listing_model_info
    assert model.disabled is not None


def test_get_hf_model_by_id__gated_repository(gated_model_id, gated_repo_listing_model_info):
    model = get_hf_model_by_id(gated_repo_listing_model_info)
    assert model.id == gated_model_id
    assert model == gated_repo_listing_model_info
    assert model.gated is True


def test_download_mergekit_config_yaml_file(public_repo_listing_model_info):
    file_path = download_mergekit_config_yaml_file(public_repo_listing_model_info)
    assert file_path.exists()
    assert file_path.name == "mergekit_config.yml"
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_download_mergekit_config_yaml_file__gated_repository(gated_repo_listing_model_info):
    with pytest.raises(hf_api.GatedRepoError):
        file_path = download_mergekit_config_yaml_file(gated_repo_listing_model_info)
        assert file_path is None
        raise hf_api.GatedRepoError("dummy for testing, GatedRepoError handled by download_mergekit_config_yaml_file")


def test_download_readme_markdown_file(public_repo_listing_model_info):
    file_path = download_readme_markdown_file(public_repo_listing_model_info)
    assert file_path.exists()
    assert file_path.name == "README.md"
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_download_readme_markdown_file__gated_repository(gated_repo_listing_model_info):
    file_path = download_readme_markdown_file(gated_repo_listing_model_info)
    assert file_path.exists()
    assert file_path.name == "README.md"
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_load_model_card(public_repo_listing_model_info):
    card = load_model_card(public_repo_listing_model_info)
    assert card is not None
    assert card.data is not None
    assert card.data.license == 'cc-by-nc-4.0'


def test_load_model_card__gated(gated_repo_listing_model_info):
    card = load_model_card(gated_repo_listing_model_info)
    print(type(card), card)
    print(type(card.data), card.data)
    assert card is not None
    assert card.data is not None
    assert card.data.license == 'other'


def test_get_data_origin():
    # listing
    expected = "https://huggingface.co/api/models?author=mlabonne&model_name=Zebrafish-7B&tags=arxiv%3A2403.19522&tags=merge&sort=lastModified&limit=1"
    origin = get_data_origin(
        author='mlabonne',
        model_name="Zebrafish-7B",
        tags=['arxiv:2403.19522', 'merge'],
        sort="lastModified",
        limit=1,
    )
    assert origin == expected
    # retrieve
    model_id = "mlabonne/Zebrafish-7B"
    expected = "https://huggingface.co/api/models/mlabonne/Zebrafish-7B"
    origin = get_data_origin(model_id=model_id)
    assert origin == expected
    # download mergekit_config.yml
    config_path = settings.project_dir / "models" / "mlabonne" / "Zebrafish-7B" / "mergekit_config.yml"
    expected = "https://huggingface.co/mlabonne/Zebrafish-7B/resolve/main/mergekit_config.yml"
    origin = get_data_origin(model_id=model_id, filename_or_path=config_path)
    assert origin == expected
    # download README.md
    filename = "README.md"
    expected = "https://huggingface.co/mlabonne/Zebrafish-7B/resolve/main/README.md"
    origin = get_data_origin(model_id=model_id, filename_or_path=filename)
    assert origin == expected
