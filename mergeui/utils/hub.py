import typing as t
from loguru import logger
import huggingface_hub as hf
from huggingface_hub import hf_api
from pathlib import Path


def list_hf_models(
        *,
        author: t.Optional[str] = None,
        library: t.Optional[t.Union[str, t.List[str]]] = None,
        language: t.Optional[t.Union[str, t.List[str]]] = None,
        model_name: t.Optional[str] = None,
        tags: t.Optional[t.Union[str, t.List[str]]] = None,
        search: t.Optional[str] = None,
        sort: t.Union[t.Literal["last_modified"], str, None] = "createdAt",
        direction: t.Optional[t.Literal[-1]] = None,
        limit: t.Optional[int] = 10,
        full: t.Optional[bool] = True,
        card_data: bool = True,
        fetch_config: bool = True,
) -> list[hf_api.ModelInfo]:
    logger.debug(f"Listing models with tags={tags}...")
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
    logger.debug(f"Found {len(models)} models with tags={tags}")
    return models


def get_hf_model_by_id(listing_model_info: hf_api.ModelInfo) -> hf_api.ModelInfo:
    model_id = listing_model_info.id
    logger.debug(f"Getting model info for {model_id}...")
    try:
        retrieve_model_info = hf_api.model_info(model_id)
        logger.debug(f"Model info for {model_id} retrieved")
        return retrieve_model_info
    except hf_api.GatedRepoError:
        logger.debug(f"Model {model_id} is in a gated repository")
        listing_model_info.gated = True
        return listing_model_info


def download_file_from_hf(model_info: hf_api.ModelInfo, filenames: t.Union[str, list[str]]) -> t.Optional[Path]:
    filenames = [filenames] if isinstance(filenames, str) else filenames
    logger.debug(f"Getting any {filenames} file for {model_info.id}...")
    for filename in filenames:
        try:
            file_path = hf.hf_hub_download(
                repo_id=model_info.id,
                repo_type="model",
                filename=filename,
            )
            logger.debug(f"'{filename}' file for {model_info.id} retrieved")
            return Path(file_path)
        except hf_api.EntryNotFoundError:
            pass
    logger.debug(f"All {filenames} for {model_info.id} not found")
    return None


def download_mergekit_config_yaml_file(model_info: hf_api.ModelInfo) -> t.Optional[Path]:
    return download_file_from_hf(model_info, ["mergekit_config.yml", "merge.yml", "mergekit_moe_config.yml", ])


def download_readme_markdown_file(model_info: hf_api.ModelInfo) -> t.Optional[Path]:
    return download_file_from_hf(model_info, ["README.md", "readme.md"])
