import pytest
from huggingface_hub import hf_api
from utils import parse_yaml
from utils.data_extraction import is_valid_repo_id, get_data_origin, list_model_infos, get_model_info, \
    download_file_from_hf, extract_urls_from_text, download_mergekit_config, download_readme, load_model_card
from utils.data_extraction import extract_base_models_from_mergekit_config, extract_merge_method_from_mergekit_config, \
    extract_base_models_from_card_data, extract_license_from_card_data, extract_base_models_from_tags, \
    extract_card_data_string_from_readme, extract_mergekit_configs_string_from_readme


# ##### Hub #####
@pytest.fixture(scope="session")
def invalid_repo_ids() -> list[str]:
    return [
        "/media/data5/hf_models/Mistral-7B-Merge-14-v0.3",
        "/media/data5/hf_models/OpenHermes-2.5-neural-chat-v3-3-openchat-3.5-1210-Slerp",
        r"D:\Learning Centre\GenAI\LLM Leaderboard\2024042801\mergekit-main\models\Calme-7B-Instruct-v0.9",
        "jeiku/Average_Normie_v2_l3_8B+ResplendentAI/Smarts_Llama3",
        "/content/drive/MyDrive/WestLake"
    ]


@pytest.fixture(scope="session")
def valid_repo_ids() -> list[str]:
    return [
        "mlabonne/Zebrafish-7B",
        "LeroyDyer/Mixtral_AI_128k",  # gated and moved
        "meta-llama/Meta-Llama-3-8B",  # gated
        "nbeerbower/flammen22C-mistral-7B",  # moved
    ]


def test_is_valid_repo_id(invalid_repo_ids, valid_repo_ids):
    for repo_id in invalid_repo_ids:
        assert not is_valid_repo_id(repo_id)
    for repo_id in valid_repo_ids:
        assert is_valid_repo_id(repo_id)


def test_get_data_origin(settings):
    # listing
    expected = ("https://huggingface.co/api/models?author=mlabonne&model_name=Zebrafish-7B"
                "&tags=arxiv%3A2403.19522&tags=merge&sort=lastModified&limit=1&full=True&cardData=True&config=True")
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


def test_list_model_infos():
    limit = 10
    tag = "merge"
    models = list_model_infos(tags=tag, limit=limit)
    assert len(models) == limit
    assert all([tag in model.tags for model in models])


def test_list_model_infos__filtered():
    models = list_model_infos(
        author='mlabonne',
        model_name="Zebrafish-7B",
        tags=['arxiv:2403.19522', 'merge'],
        sort="lastModified",
        limit=1,
    ) + list_model_infos(
        author='meta-llama',
        model_name="Meta-Llama-3-8B",
        tags='llama-3',
        limit=1,
    )
    for model in models:
        # none
        assert model.disabled is None
        # others
        assert model.last_modified is not None
        assert model.author is not None
        assert model.gated is not None
        assert model.id
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


def test_get_model_info():
    model_id = "Q-bert/MetaMath-Cybertron-Starling"
    model, origin = get_model_info(model_id)
    assert model is not None
    assert not model.gated
    assert model.id == model_id
    assert model.disabled is not None


def test_get_model_info__gated():
    model_id = "meta-llama/Meta-Llama-3-8B"
    model, origin = get_model_info(model_id)
    assert model is not None
    assert model.gated
    assert model.id == model_id


def test_get_model_info__gated_and_moved():
    model_id = "LeroyDyer/Mixtral_AI_128k"
    new_model_id = "LeroyDyer/Mixtral_AI_128k_Base"
    # without fallback to listing
    model, origin = get_model_info(model_id, include_gated=False)
    assert model is None and origin is None
    # without moved support
    model, origin = get_model_info(model_id, include_moved=False)
    assert model is None and origin is None
    # with fallback and moved
    model, origin = get_model_info(model_id)
    assert model is not None
    assert model.gated
    assert model.id == new_model_id


def test_get_model_info__moved():
    model_id = "nbeerbower/flammen22C-mistral-7B"
    new_model_id = "flammenai/flammen22C-mistral-7B"
    model, origin = get_model_info(model_id)
    assert model is not None
    assert not model.gated
    assert model.id == new_model_id


def test_get_model_info__invalid_repo_id(invalid_repo_ids):
    for invalid_id in invalid_repo_ids:
        model, origin = get_model_info(invalid_id)
        assert model is None and origin is None


def test_get_model_info__not_found(invalid_repo_ids):
    model_id = "teamX/modelY"
    model, origin = get_model_info(model_id)
    assert model is None and origin is None


def test_download_file_from_hf():
    model_id = "mlabonne/Zebrafish-7B"
    filename = "config.json"
    file_path, origin = download_file_from_hf(model_id, filename)
    assert file_path.exists()
    assert file_path.name == filename
    assert file_path.is_file()
    assert file_path.stat().st_size > 0
    assert origin == f"https://huggingface.co/{model_id}/resolve/main/{filename}"
    # not found
    filename = ".config.json"
    file_path, origin = download_file_from_hf(model_id, filename)
    assert file_path is None and origin is None
    # not found without in_siblings
    file_path, origin = download_file_from_hf(model_id, filename, in_siblings=False)
    assert file_path is None and origin is None


def test_download_mergekit_config():
    model_id = "mlabonne/Zebrafish-7B"
    expected_fn = "mergekit_config.yml"
    file_path, origin = download_mergekit_config(model_id)
    assert file_path.exists()
    assert file_path.name == expected_fn
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_download_mergekit_config__gated():
    model_id = "meta-llama/Meta-Llama-3-8B"
    with pytest.raises(hf_api.GatedRepoError):
        file_path, origin = download_mergekit_config(model_id)
        assert file_path is None and origin is None
        raise hf_api.GatedRepoError("GatedRepoError handled by download_mergekit_config")


def test_download_mergekit_config__moved():
    model_id = "Test157t/Heracleana-Maid-7b"
    expected_fn = "mergekit_config.yml"
    file_path, origin = download_mergekit_config(model_id)
    assert file_path.exists()
    assert file_path.name == expected_fn
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_download_readme():
    model_id = "mlabonne/Zebrafish-7B"
    expected_fn = "README.md"
    file_path, origin = download_readme(model_id)
    assert file_path.exists()
    assert file_path.name == expected_fn
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_download_readme__gated():
    model_id = "meta-llama/Meta-Llama-3-8B"
    expected_fn = "README.md"
    file_path, origin = download_readme(model_id)
    assert file_path.exists()
    assert file_path.name == expected_fn
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_download_readme__moved():
    model_id = "nbeerbower/flammen22C-mistral-7B"
    expected_fn = "README.md"
    file_path, origin = download_readme(model_id)
    assert file_path.exists()
    assert file_path.name == expected_fn
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_load_model_card():
    model_id = "mlabonne/Zebrafish-7B"
    card = load_model_card(model_id)
    assert card is not None
    assert card.data is not None
    assert card.data.license == 'cc-by-nc-4.0'


def test_load_model_card__gated():
    model_id = "meta-llama/Meta-Llama-3-8B"
    card = load_model_card(model_id)
    assert card is not None
    assert card.data is not None
    assert card.data.license == 'other'


def test_load_model_card__moved():
    model_id = "nbeerbower/flammen22C-mistral-7B"
    card = load_model_card(model_id)
    assert card is not None
    assert card.data is not None
    assert card.data.license == "apache-2.0"


# ##### Hub #####


# ##### Data Extraction #####


@pytest.fixture(scope="session")
def parsed_card_data(settings) -> dict:
    card_data_path = settings.project_dir / 'tests/test_data/miqu-1-120b__card_data.yml'
    return parse_yaml(card_data_path.read_text())[0]


@pytest.fixture(scope="session")
def readme_markdown(settings) -> str:
    return (settings.project_dir / 'tests/test_data/miqu-1-120b__README.md').read_text()


def test_extract_base_models_from_mergekit_config(settings):
    mergekit_config_path = settings.project_dir / 'tests/test_data/mergekit_config.yml'
    expected = {'psmathur/orca_mini_v3_13b', 'garage-bAInd/Platypus2-13B'}
    yaml_doc = parse_yaml(mergekit_config_path.read_text())[0]
    base_models = extract_base_models_from_mergekit_config(yaml_doc)
    assert base_models == expected


def test_extract_base_models_from_mergekit_moe_config(settings):
    mergekit_moe_config_path = settings.project_dir / 'tests/test_data/mergekit_moe_config.yml'
    expected = {'mlabonne/Marcoro14-7B-slerp', 'openchat/openchat-3.5-1210', 'beowolx/CodeNinja-1.0-OpenChat-7B',
                'maywell/PiVoT-0.1-Starling-LM-RP', 'WizardLM/WizardMath-7B-V1.1'}
    yaml_doc = parse_yaml(mergekit_moe_config_path.read_text())[0]
    base_models = extract_base_models_from_mergekit_config(yaml_doc)
    assert base_models == expected


def test_extract_base_models_from_card_data(parsed_card_data):
    expected = {'152334H/miqu-1-70b-sf'}
    base_models = extract_base_models_from_card_data(parsed_card_data)
    assert base_models == expected


def test_extract_base_models_from_tags():
    expected = {'Q-bert/MetaMath-Cybertron', 'berkeley-nest/Starling-LM-7B-alpha'}
    tags = [
        "transformers",
        "safetensors",
        "mistral",
        "text-generation",
        "Math",
        "merge",
        "en",
        "dataset:meta-math/MetaMathQA",
        "base_model:Q-bert/MetaMath-Cybertron",
        "base_model:berkeley-nest/Starling-LM-7B-alpha",
        "license:cc-by-nc-4.0",
        "autotrain_compatible",
        "endpoints_compatible",
        "text-generation-inference",
        "region:us"
    ]
    base_models = extract_base_models_from_tags(tags)
    assert base_models == expected


def test_extract_card_data_string_from_readme(readme_markdown):
    card_data_string = extract_card_data_string_from_readme(readme_markdown)
    assert card_data_string is not None
    assert "base_model:" in card_data_string
    assert "license: other" in card_data_string
    assert card_data_string.startswith("base_model")
    assert card_data_string.endswith("other\n")


def test_extract_mergekit_configs_string_from_readme(readme_markdown):
    mergekit_config_string = extract_mergekit_configs_string_from_readme(readme_markdown)
    assert mergekit_config_string is not None
    assert "merge_method: passthrough" in mergekit_config_string
    assert mergekit_config_string.startswith("dtype: float16")
    assert mergekit_config_string.endswith("model: 152334H/miqu-1-70b-sf\n")


def test_extract_merge_method_from_mergekit_config(settings):
    mergekit_config_path = settings.project_dir / 'tests/test_data/mergekit_config.yml'
    expected = 'slerp'
    yaml_doc = parse_yaml(mergekit_config_path.read_text())[0]
    merge_method = extract_merge_method_from_mergekit_config(yaml_doc)
    assert merge_method == expected


def test_extract_license_from_card_data(parsed_card_data):
    expected = 'other'
    license_ = extract_license_from_card_data(parsed_card_data)
    assert license_ == expected


# ##### Data Extraction #####


# ##### Helpers #####
def test_extract_urls_from_text():
    expected = [
        "https://huggingface.co/meta-llama/Meta-Llama-3-8B",
    ]
    assert extract_urls_from_text(
        "Access to model meta-llama/Meta-Llama-3-8B is restricted and you are not in the authorized list. "
        "Visit https://huggingface.co/meta-llama/Meta-Llama-3-8B to ask for access.") == expected
# ##### Helpers #####
