import pytest
from utils import parse_yaml
from utils.data_extraction import extract_base_models_from_mergekit_config, extract_merge_method_from_mergekit_config, \
    extract_base_models_from_card_data, extract_license_from_card_data, extract_base_models_from_tags, \
    extract_card_data_string_from_readme, extract_mergekit_config_string_from_readme
from core.settings import Settings
from tests.test_utils.test_utils import mergekit_config_path, mergekit_moe_config_path

settings = Settings()


@pytest.fixture(scope="session")
def parsed_card_data() -> dict:
    card_data_path = settings.project_dir / 'tests/test_data/miqu-1-120b__card_data.yml'
    return parse_yaml(card_data_path.read_text())[0]


@pytest.fixture(scope="session")
def readme_markdown() -> str:
    return (settings.project_dir / 'tests/test_data/miqu-1-120b__README.md').read_text()


def test_extract_base_models_from_mergekit_config(mergekit_config_path):
    expected = {'psmathur/orca_mini_v3_13b', 'garage-bAInd/Platypus2-13B'}
    yaml_doc = parse_yaml(mergekit_config_path.read_text())[0]
    base_models = extract_base_models_from_mergekit_config(yaml_doc)
    assert base_models == expected


def test_extract_base_models_from_mergekit_moe_config(mergekit_moe_config_path):
    expected = {'mlabonne/Marcoro14-7B-slerp', 'openchat/openchat-3.5-1210', 'beowolx/CodeNinja-1.0-OpenChat-7B',
                'maywell/PiVoT-0.1-Starling-LM-RP', 'WizardLM/WizardMath-7B-V1.1'}
    yaml_doc = parse_yaml(mergekit_moe_config_path.read_text())[0]
    base_models = extract_base_models_from_mergekit_config(yaml_doc)
    assert base_models == expected


def test_extract_merge_method_from_mergekit_config(mergekit_config_path):
    expected = 'slerp'
    yaml_doc = parse_yaml(mergekit_config_path.read_text())[0]
    merge_method = extract_merge_method_from_mergekit_config(yaml_doc)
    assert merge_method == expected


def test_extract_base_models_from_card_data(parsed_card_data):
    expected = {'152334H/miqu-1-70b-sf'}
    base_models = extract_base_models_from_card_data(parsed_card_data)
    assert base_models == expected


def test_extract_license_from_card_data(parsed_card_data):
    expected = 'other'
    license_ = extract_license_from_card_data(parsed_card_data)
    assert license_ == expected


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


def test_extract_mergekit_config_string_from_readme(readme_markdown):
    mergekit_config_string = extract_mergekit_config_string_from_readme(readme_markdown)
    assert mergekit_config_string is not None
    assert "merge_method: passthrough" in mergekit_config_string
    assert mergekit_config_string.startswith("dtype: float16")
    assert mergekit_config_string.endswith("model: 152334H/miqu-1-70b-sf\n")
