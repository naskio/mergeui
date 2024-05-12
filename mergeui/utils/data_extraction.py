import math
import typing as t
import datetime as dt
from pathlib import Path
import yaml.scanner
import json
import urllib.parse
from loguru import logger
import re
import huggingface_hub as hf
from huggingface_hub import hf_api
from utils import parse_yaml, filter_none, parse_iso_dt, aware_to_naive_dt
from core.schema import MergeMethodType


# ##### Hub #####

def is_valid_repo_id(repo_id: str) -> bool:
    """Check if str a valid repo_id with namespace/repo_name format."""
    return bool(re.match(r"^[-.\w]+/[-.\w]+$", repo_id))


def get_data_origin(
        *,
        # get model or download file
        model_id: t.Optional[str] = None,
        filename_or_path: t.Optional[t.Union[Path, str]] = None,
        # list models
        author: t.Optional[str] = None,
        library: t.Optional[t.Union[str, t.List[str]]] = None,
        language: t.Optional[t.Union[str, t.List[str]]] = None,
        model_name: t.Optional[str] = None,
        tags: t.Optional[t.Union[str, t.List[str]]] = None,
        search: t.Optional[str] = None,
        sort: t.Optional[str] = "lastModified",
        direction: t.Optional[t.Literal[-1]] = None,
        limit: t.Optional[int] = None,
        full: t.Optional[bool] = True,
        card_data: bool = True,
        fetch_config: bool = True,
) -> t.Optional[str]:
    """Get the URL from a HF get request params."""
    if filename_or_path:  # case download_file_from_hf and load_model_card = README.md
        filename = filename_or_path if isinstance(filename_or_path, str) else filename_or_path.name
        return hf_api.hf_hub_url(repo_id=model_id, filename=filename)
    if model_id:  # case get_model_by_id
        if is_valid_repo_id(model_id):
            return f"https://huggingface.co/api/models/{model_id}"
        else:
            return None
    # case list_models
    params = {
        "author": author,
        "library": library,
        "language": language,
        "model_name": model_name,
        "tags": tags,
        "search": search,
        "sort": sort,
        "direction": direction,
        "limit": limit,
        "full": full or None,
        "cardData": card_data or None,
        "config": fetch_config or None,
    }
    return f"https://huggingface.co/api/models?{urllib.parse.urlencode(filter_none(params), doseq=True)}"


def list_model_infos(
        *,
        author: t.Optional[str] = None,
        library: t.Optional[t.Union[str, t.List[str]]] = None,
        language: t.Optional[t.Union[str, t.List[str]]] = None,
        model_name: t.Optional[str] = None,
        tags: t.Optional[t.Union[str, t.List[str]]] = None,
        search: t.Optional[str] = None,
        sort: t.Optional[str] = "lastModified",
        direction: t.Optional[t.Literal[-1]] = None,
        limit: t.Optional[int] = None,
        full: t.Optional[bool] = True,
        card_data: bool = True,
        fetch_config: bool = True,
) -> list[hf_api.ModelInfo]:
    """List models from HF API."""
    logger.debug(f"Listing models with limit={limit}...")
    models = list(hf_api.list_models(
        author=author,
        library=library,
        language=language,
        model_name=model_name,
        tags=tags,
        search=search,
        sort=sort,
        direction=direction,
        limit=limit,
        full=full,
        cardData=card_data,
        fetch_config=fetch_config,
    ))
    logger.debug(f"Found {len(models)} models")
    return models


def get_model_info(model_id: str, include_gated: bool = True, include_moved: bool = True) \
        -> tuple[t.Optional[hf_api.ModelInfo], t.Optional[str]]:
    """Get model info from HF API by ID.
    include_gated=True => fallback to listing if model is in a gated repository to fetch its model_info
    include_moved=True => get model_info also if the repo has been moved/renamed
    """
    logger.debug(f"Getting model info for {model_id}...")
    try:
        retrieve_model_info = hf_api.model_info(model_id)
        logger.debug(f"Model info for {model_id} retrieved")
        return retrieve_model_info, get_data_origin(model_id=model_id)
    except hf_api.GatedRepoError as e:
        if include_gated:  # handle gated repo
            namespace, repo_name = model_id.split("/")
            if include_moved:  # handle renamed repo
                err = e.response.json().get("error", "")
                urls = extract_urls_from_text(err)
                if urls:
                    repo_url: hf_api.RepoUrl = hf_api.RepoUrl(urls[0])
                    model_id = repo_url.repo_id
                    namespace, repo_name = repo_url.namespace, repo_url.repo_name
            # fallback to listing
            list_params = dict(
                author=namespace,
                model_name=repo_name,
                full=True,
                card_data=True,
                fetch_config=True,
            )
            possible_models = list_model_infos(**list_params)
            for pm in possible_models:
                if pm.id == model_id:
                    # pm.gated = True # could be a string "auto", ...
                    return pm, get_data_origin(**list_params)
            logger.debug(f"Model {model_id} not found in listing")
        logger.debug(f"Model {model_id} is in a gated repository")
    except hf_api.RepositoryNotFoundError:
        logger.debug(f"Model {model_id} not found")
    except hf.utils._validators.HFValidationError as e:
        logger.debug(f"Model {model_id} is invalid\n{e.__repr__()}")
    return None, None


def download_file_from_hf(
        model_id: str,
        filenames: t.Union[str, list[str]],
        siblings: t.Optional[list[hf_api.RepoSibling]] = None,
        in_siblings: bool = True,
        local_files_only: bool = False,
) -> tuple[t.Optional[Path], t.Optional[str]]:
    """
    Download one of the files from HF API by ID.
    in_siblings=True => check if the file is in the siblings list before downloading
    """
    filenames = [filenames] if isinstance(filenames, str) else filenames
    logger.debug(f"Getting any {filenames} file for {model_id}...")
    if siblings:
        siblings = [sibling.rfilename for sibling in siblings]
    else:
        in_siblings = False
    for filename in filenames:
        if in_siblings and filename not in siblings:
            logger.debug(f"'{filename}' file not in siblings, skipping...")
            continue
        try:
            file_path = Path(hf.hf_hub_download(
                repo_id=model_id,
                repo_type="model",
                filename=filename,
                local_files_only=local_files_only,
            ))
            logger.debug(f"'{filename}' file for {model_id} retrieved")
            return file_path, get_data_origin(model_id=model_id, filename_or_path=filename)
        except hf_api.EntryNotFoundError:
            pass
    logger.debug(f"All {filenames} for {model_id} not found")
    return None, None


def download_mergekit_config(
        model_id: str,
        siblings: t.Optional[list[hf_api.RepoSibling]] = None
) -> tuple[t.Optional[Path], t.Optional[str]]:
    """Download one of the mergekit_config files from HF API by ID.
    - Won't download if gated repo
    """
    try:
        return download_file_from_hf(
            model_id, filenames=["mergekit_config.yml", "merge.yml", "mergekit_moe_config.yml"],
            siblings=siblings, in_siblings=True
        )
    except hf_api.GatedRepoError:
        return None, None


def download_readme(
        model_id: str,
        siblings: t.Optional[list[hf_api.RepoSibling]] = None
) -> tuple[t.Optional[Path], t.Optional[str]]:
    """Download the README.md ie Model Card from HF API by ID.
    - Will download even if gated repo
    """
    return download_file_from_hf(
        model_id, filenames=["README.md", "readme.md"],
        siblings=siblings, in_siblings=True,
    )


def load_model_card(path_or_id: t.Union[hf_api.ModelInfo, Path, str]) -> t.Optional[hf.ModelCard]:
    """Load the Model Card from HF API by ID or from a local file."""
    try:
        model_card = None
        if isinstance(path_or_id, (Path, str)):
            model_card = hf.ModelCard.load(path_or_id, ignore_metadata_errors=True)
        return model_card
    except hf_api.EntryNotFoundError:
        logger.debug(f"Model Card for {path_or_id} not found")
    except yaml.scanner.ScannerError:
        logger.debug(f"Model Card for {path_or_id} is invalid")


def hf_whoami() -> None:
    """log currently logged user to HF API."""
    user = hf_api.whoami()
    name = (user or {}).get("name")
    if name:
        logger.success(f"Logged In to HuggingFace as {name}")
    else:
        logger.warning(f"Not Logged In to HuggingFace")


# ##### Hub #####


# ##### Data Extraction #####

def extract_base_models_from_mergekit_config(mergekit_config: dict) -> set[str]:
    """https://github.com/arcee-ai/mergekit#merge-configuration"""
    found = []
    # base_model (str)
    if "base_model" in mergekit_config:
        if isinstance(mergekit_config["base_model"], str):
            found.append(mergekit_config["base_model"])
        elif isinstance(mergekit_config["base_model"], list):
            found.extend(mergekit_config["base_model"])
    # models (list of dict)
    ld = []
    models_list = mergekit_config.get("models", [])
    if isinstance(models_list, list):
        ld.extend(models_list)
    # slices.sources (list of dict)
    if "slices" in mergekit_config and isinstance(mergekit_config["slices"], list):
        for slice_ in mergekit_config["slices"]:
            sources_list = slice_.get("sources", [])
            if isinstance(sources_list, list):
                ld.extend(sources_list)
    # experts (list of dict)
    experts_list = mergekit_config.get("experts", [])
    if isinstance(experts_list, list):
        found.extend([expert.get("source_model") for expert in experts_list])
    # collect all
    found.extend([model.get("model") for model in ld])
    return set(f for f in found if isinstance(f, str))


def extract_base_models_from_mergekit_configs(mergekit_configs: t.Optional[list[dict]]) -> set[str]:
    base_model_set = set()
    if mergekit_configs:
        base_model_set = set.union(*[extract_base_models_from_mergekit_config(mc) for mc in mergekit_configs])
    return base_model_set


def extract_base_models_from_card_data(card_data: dict) -> set[str]:
    # https://huggingface.co/docs/hub/en/model-cards#model-card-metadata
    found = []
    base_model = card_data.get("base_model", None)
    if isinstance(base_model, str):
        found.append(base_model)
    elif isinstance(base_model, list):
        found.extend(base_model)
    return set(f for f in found if isinstance(f, str))


def extract_base_models_from_tags(tags: list[str]) -> set[str]:
    return set([tag.replace('base_model:', '') for tag in tags if tag.startswith('base_model:')])


def extract_base_models_from_model_card(model_card: t.Optional[hf.ModelCard]) -> set[str]:
    if not model_card or not model_card.data:
        return set()
    card_data: hf.ModelCardData = model_card.data
    if card_data.base_model:
        if isinstance(card_data.base_model, str):
            return {card_data.base_model}
        elif isinstance(card_data.base_model, list):
            return set(card_data.base_model)
    return set()


def extract_merge_method_from_mergekit_config(mergekit_config: dict) -> t.Optional[str]:
    return mergekit_config.get("merge_method")


def extract_merge_method_from_model_description(model_description: t.Optional[str]) -> t.Optional[str]:
    if not model_description:
        return None
    available_methods = list(t.get_args(MergeMethodType))
    for method in available_methods:
        if method in model_description:
            return method


def extract_license_from_card_data(card_data: dict) -> t.Optional[str]:
    # return card_data.get("license_name") # any string
    return card_data.get("license")  # one from https://huggingface.co/docs/hub/en/repositories-licenses


def extract_license_from_tags(tags: list[str]) -> t.Optional[str]:
    for tag in tags:
        if tag.startswith('license:'):
            return tag.replace('license:', '')


def extract_license_from_model_card(model_card: t.Optional[hf.ModelCard]) -> t.Optional[str]:
    if not model_card or not model_card.data:
        return None
    return model_card.data.license


def extract_model_name_from_model_card(model_card: t.Optional[hf.ModelCard]) -> t.Optional[str]:
    if not model_card or not model_card.data:
        return None
    return model_card.data.model_name


def sanitize_description(description: str) -> str:
    description = re.sub(r'[^\w_.-]+', ' ', description)
    description = re.sub(r'\s+', ' ', description)
    return description.strip()


def extract_model_description_from_model_card(model_card: t.Optional[hf.ModelCard]) -> t.Optional[str]:
    if not model_card or not model_card.content:
        return None
    readme_str = model_card.content
    hints = [
        " is a fine-tuned ",
        "is a merge of",
        " based on ",
        "was merged using",
        "created using",
        "made with",
        "was trained ",
        " is a ",
        "this model is ",
        "this is an ",
        "mergekit",
        "lazymergekit",
        "this is the ",
        "it is the ",
        "merge ",
        " using ",
        "large language model ",
        "language model",
    ]
    skip_starts = [
        "-",
        "<!--",
    ]
    for line in readme_str.splitlines():
        line = line.strip()
        _line = line.lower()
        if any(_line.startswith(start) for start in skip_starts):
            continue
        if any(hint in _line for hint in hints):
            return sanitize_description(line)
    return None


def extract_model_architecture_from_model_info(model_info: hf_api.ModelInfo) -> t.Optional[str]:
    architectures = (model_info.config or {}).get("architectures", [])
    if architectures:
        return architectures[0]


def extract_model_url_from_model_info(model_info_or_id: t.Union[hf_api.ModelInfo, str]) -> t.Optional[str]:
    model_id = model_info_or_id if isinstance(model_info_or_id, str) else model_info_or_id.id
    if not is_valid_repo_id(model_id):
        return None
    return f"https://huggingface.co/{model_id}"


def extract_benchmark_results_from_dataset(model_id: str, dataset_folder: Path) \
        -> t.Optional[dict[str, t.Union[float, dt.datetime]]]:
    """
    Results:
    - Average (avg(of 6 following))
    - ARC (AI2 Reasoning Challenge (ARC) - Grade-School Science Questions (25-shot))
    - HellaSwag (HellaSwag - Commonsense Inference (10-shot))
    - MMLU (MMLU - Massive Multi-Task Language Understanding, knowledge on 57 domains (5-shot))
    - TruthfulQA (TruthfulQA - Propensity to Produce Falsehoods (0-shot))
    - Winogrande (Winogrande - Adversarial Winograd Schema Challenge (5-shot))
    - GSM8K (GSM8k - Grade School Math Word Problems Solving Complex Mathematical Reasoning (5-shot))
    """
    results, evaluated_at = load_benchmark_results_from_dataset(model_id, dataset_folder)
    if not results:
        return None
    scores = dict()
    # arc
    scores["arc_score"] = results.get("harness|arc:challenge|25", {}).get("acc_norm")
    # hella_swag
    scores["hella_swag_score"] = results.get("harness|hellaswag|10", {}).get("acc_norm")
    # mmlu
    mmlu_sum = 0
    mmlu_count = 0
    for key, value in results.items():
        if key.startswith("harness|hendrycksTest-") and key.endswith("|5"):
            test_score = (value or {}).get("acc_norm")
            if test_score is not None:
                mmlu_sum += test_score
                mmlu_count += 1
    # if mmlu_count == 57:
    if mmlu_count > 0:
        scores["mmlu_score"] = mmlu_sum / mmlu_count
    # truthfulqa
    scores["truthfulqa_score"] = results.get("harness|truthfulqa:mc|0", {}).get("mc2")
    # winogrande
    scores["winogrande_score"] = results.get("harness|winogrande|5", {}).get("acc")
    # gsm8k
    scores["gsm8k_score"] = results.get("harness|gsm8k|5", {}).get("acc")
    scores = filter_none(scores)
    # filter NaN values
    scores = {k: v for k, v in scores.items() if not math.isnan(v)}
    # average
    if len(scores) > 0:
        scores["average_score"] = sum(scores.values()) / len(scores)
    # evaluated_at
    if evaluated_at is not None:
        scores["evaluated_at"] = aware_to_naive_dt(evaluated_at)
    return scores


# ##### Data Extraction #####


# ##### Helpers #####


def extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from text."""
    return re.findall(r'(https?://\S+)', text)


def extract_card_data_string_from_readme(readme: str) -> t.Optional[str]:
    # extracting card_data from Model Card
    if readme.startswith('---\n'):
        return readme.split('---\n')[1]


def extract_mergekit_configs_string_from_readme(readme: str) -> t.Optional[str]:
    config_strings = []
    config_string = None
    start = False
    for line in readme.splitlines():
        if line.startswith('```yaml') or line.startswith('```yml'):
            start = True
            config_string = ''
            continue
        if line.startswith('```'):
            start = False
            if config_string:
                config_strings.append(config_string)
        if start:
            config_string += f"{line}\n"
    if config_strings:
        return "---\n".join([config_string for config_string in config_strings if "merge_method" in config_string])


def extract_mergekit_configs_from_model_card(model_card: t.Optional[hf.ModelCard]) -> list[dict]:
    if not model_card or not model_card.content:
        return []
    readme_str = model_card.content
    configs_string = extract_mergekit_configs_string_from_readme(readme_str)
    config_docs = []
    if configs_string:
        config_docs = parse_yaml(configs_string)
    return config_docs


def extract_mergekit_configs_from_file(file_path: t.Optional[Path]) -> list[dict]:
    configs_string = file_path.read_text() if file_path else None
    config_docs = []
    if configs_string:
        config_docs = parse_yaml(configs_string)
    return config_docs


def load_benchmark_results_from_dataset(model_id: str, dataset_folder: Path) \
        -> tuple[t.Optional[dict], t.Optional[dt.datetime]]:
    repo_folder = dataset_folder / model_id
    if repo_folder.exists() and repo_folder.is_dir():
        merged_results = {}
        json_files = sorted(repo_folder.glob("results*.json"))
        filename = None
        for json_file in json_files:
            loaded = json.loads(json_file.read_text())
            results = (loaded or {}).get("results", {})
            merged_results.update(results)
            filename = json_file.stem
        if filename:  # results_2023-09-08T23-38-08.931556
            parts = filename.split("_")
            if len(parts) == 2:
                parts = parts[1].split("T")
                parts = f"{parts[0]}T{parts[1].replace('-', ':')}"
                evaluated_at = parse_iso_dt(parts)
                return merged_results, evaluated_at
        if merged_results:
            return merged_results, None
    return None, None

# ##### Helpers #####
