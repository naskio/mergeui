import typing as t
import datetime as dt
from loguru import logger
from pathlib import Path
import time
import redis
import huggingface_hub as hf
from huggingface_hub import hf_api
from utils import aware_to_naive_dt, filter_none, format_duration
from utils.index.data_extraction import get_model_info, load_model_card, download_mergekit_config, get_data_origin, \
    extract_benchmark_results_from_dataset, extract_model_url_from_model_info, extract_model_name_from_model_card, \
    extract_model_description_from_model_card, extract_license_from_tags, extract_license_from_model_card, \
    extract_model_architecture_from_model_info, extract_merge_method_from_model_description, \
    extract_merge_method_from_mergekit_config, extract_base_models_from_tags, extract_base_models_from_model_card, \
    extract_base_models_from_mergekit_configs, extract_mergekit_configs_from_model_card, \
    extract_mergekit_configs_from_file, extract_model_name_from_model_id, extract_author_from_model_id
from core.settings import Settings


def create_redis_connection(settings: Settings) -> redis.Redis:
    return redis.Redis(
        host=settings.redis_dsn.host,
        port=settings.redis_dsn.port,
        db=settings.redis_dsn.path.replace("/", ""),
        username=settings.redis_dsn.username,
        password=settings.redis_dsn.password,
        client_name=f"{settings.app_name}",
    )


def index_model_by_id(model_id: str, results_dataset_folder: str) -> tuple[dict, list]:
    """Index one model by its ID. Return the node data and relationships data"""
    start_time = time.time()
    results_dataset_folder = Path(results_dataset_folder)
    _got: tuple[t.Optional[hf_api.ModelInfo], t.Optional[str]] = get_model_info(
        model_id=model_id,
        include_gated=True,
        include_moved=True,
    )
    model_info, model_info_origin = _got
    # private/local model
    if model_info is None:
        logger.warning(f"Model {model_id} not found in HF")
        end_time = time.time()
        logger.success(f"Job={model_id} completed in {format_duration(start_time, end_time)}")
        return filter_none({
            "id": model_id,
            "url": extract_model_url_from_model_info(model_id),
            "name": extract_model_name_from_model_id(model_id),
            "description": None,
            "license": "unknown",
            "author": extract_author_from_model_id(model_id),
            "indexed": True,
            "indexed_at": aware_to_naive_dt(dt.datetime.utcnow()),
            "private": True,
            "labels": ["Model"],
        }), []
    # public model
    model_card: t.Optional[hf.ModelCard] = load_model_card(model_info.id)
    model_card_origin = get_data_origin(model_id=model_info.id, filename_or_path="README.md")
    _got: tuple[t.Optional[Path], t.Optional[str]] = download_mergekit_config(model_info.id, model_info.siblings)
    mergekit_config_path, mergekit_config_origin = _got
    mergekit_configs_from_model_card = extract_mergekit_configs_from_model_card(model_card)
    mergekit_configs_from_file = extract_mergekit_configs_from_file(mergekit_config_path)
    benchmark_results: t.Optional[dict[str, t.Union[float, dt.datetime]]] = (
            extract_benchmark_results_from_dataset(model_id, dataset_folder=results_dataset_folder)
            or extract_benchmark_results_from_dataset(model_info.id, dataset_folder=results_dataset_folder)
    )
    description: t.Optional[str] = extract_model_description_from_model_card(model_card)
    node_data = {
        "id": model_id,
        "new_id": model_info.id if model_info.id != model_id else None,
        "url": extract_model_url_from_model_info(model_info),
        "name": extract_model_name_from_model_card(model_card) or extract_model_name_from_model_id(model_info.id),
        "description": description,
        "license": extract_license_from_tags(model_info.tags) or extract_license_from_model_card(
            model_card) or "unknown",
        "author": model_info.author or extract_author_from_model_id(model_info.id),
        "merge_method": extract_merge_method_from_model_description(description),
        "architecture": extract_model_architecture_from_model_info(model_info),
        "likes": model_info.likes,
        "downloads": model_info.downloads,
        "created_at": aware_to_naive_dt(model_info.created_at),
        "updated_at": aware_to_naive_dt(model_info.last_modified),
        **(benchmark_results or {}),
        "private": model_info.private,
        "disabled": model_info.disabled,
        "gated": model_info.gated in ["auto", "manual"],
        "indexed": True,
        "indexed_at": aware_to_naive_dt(dt.datetime.utcnow()),
        "labels": ["Model"],
    }
    node_relationships = []
    base_model_extractors = {
        "tags": {
            "func": extract_base_models_from_tags,
            "args": [model_info.tags or [], ],
            "origin": model_info_origin,
        },
        "cardData.base_model": {
            "func": extract_base_models_from_model_card,
            "args": [model_card],
            "origin": model_card_origin,
        },
        "mergekit_config": {
            "func": extract_base_models_from_mergekit_configs,
            "args": [mergekit_configs_from_file],
            "origin": mergekit_config_origin,
        },
        "modelCard.yaml": {
            "func": extract_base_models_from_mergekit_configs,
            "args": [mergekit_configs_from_model_card],
            "origin": model_card_origin,
        },
    }
    # relationships
    for extractor_method, extractor_data in base_model_extractors.items():
        _func, _args, _origin = extractor_data["func"], extractor_data["args"], extractor_data["origin"]
        base_model_set: set = _func(*_args)
        for base_model in base_model_set:
            node_relationships.append(
                filter_none(
                    dict(
                        type="DERIVED_FROM",
                        method=extractor_method,
                        origin=_origin,
                        source=model_id,
                        target=base_model,
                    )
                )
            )
    # extract merge_method
    for mergekit_config in (mergekit_configs_from_file + mergekit_configs_from_model_card):
        _merge_method = extract_merge_method_from_mergekit_config(mergekit_config)
        if _merge_method:
            node_data["merge_method"] = _merge_method
            break
    # add extra labels if needed
    if node_relationships or node_data.get("merge_method"):
        node_data["labels"].append("MergedModel")
    # logging
    end_time = time.time()
    logger.success(f"Job={model_id} completed in {format_duration(start_time, end_time)}")
    return filter_none(node_data), node_relationships
