import typing as t
import datetime as dt
from loguru import logger
from pathlib import Path
import time
import huggingface_hub as hf
from huggingface_hub import hf_api
import repositories
from core.dependencies import get_graph_repository
from core.schema import DerivedFrom
from utils import aware_to_naive_dt
from utils.data_extraction import get_model_info, load_model_card, download_mergekit_config, get_data_origin, \
    extract_benchmark_results_from_dataset, extract_model_url_from_model_info, extract_model_name_from_model_card, \
    extract_model_description_from_model_card, extract_license_from_tags, extract_license_from_model_card, \
    extract_model_architecture_from_model_info, extract_merge_method_from_model_description, \
    extract_merge_method_from_mergekit_config, extract_base_models_from_tags, extract_base_models_from_model_card, \
    extract_base_models_from_mergekit_configs, extract_mergekit_configs_from_model_card, \
    extract_mergekit_configs_from_file


def index_model_by_id(model_id: str, results_dataset_folder: Path) -> None:
    """Index one model by its ID."""
    start_time = time.time()
    repository: 'repositories.GraphRepository' = get_graph_repository()
    _got: tuple[t.Optional[hf_api.ModelInfo], t.Optional[str]] = get_model_info(
        model_id=model_id,
        include_gated=True,
        include_moved=True,
    )
    model_info, model_info_origin = _got
    if model_info is None:  # private/local model
        logger.warning(f"Model {model_id} not found in HF")
        # create/update node in DB
        return repository.set_properties(
            label="Model",
            filters=dict(id=model_id),
            new_values=dict(
                indexed=True,
                indexed_at=aware_to_naive_dt(dt.datetime.utcnow()),
                private=True,
            ),
            create=True,
        )
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
        "new_id": model_info.id if model_info.id != model_id else None,
        "url": extract_model_url_from_model_info(model_info),
        "name": extract_model_name_from_model_card(model_card),
        "description": description,
        "license": extract_license_from_tags(model_info.tags) or extract_license_from_model_card(model_card),
        "author": model_info.author,
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
    }
    extra_labels = []
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
        "README.md (yaml)": {
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
                dict(type="DERIVED_FROM", method=extractor_method, origin=_origin, source=model_id, target=base_model)
            )
    # extract merge_method
    for mergekit_config in (mergekit_configs_from_file + mergekit_configs_from_model_card):
        _merge_method = extract_merge_method_from_mergekit_config(mergekit_config)
        if _merge_method:
            node_data["merge_method"] = _merge_method
            break
    # add extra labels if needed
    if node_relationships or node_data.get("merge_method"):
        extra_labels.append("MergedModel")
    # create/update node in DB
    repository.set_properties(
        label="Model",
        filters=dict(id=model_id),
        new_values=node_data,
        create=True,
        new_labels=extra_labels,
    )
    # insert related nodes and relationships in DB
    for rel_data in node_relationships:
        # add base_model to DB if not exists
        repository.create_or_update(
            label="Model",
            filters=dict(id=rel_data["target"]),
            create_values=dict(indexed=False),
            update_values={},
        )
        # add relationships to DB
        repository.create_relationship(
            label="Model",
            from_id=rel_data["source"],
            to_id=rel_data["target"],
            relationship_type=rel_data["type"],
            properties={k: v for k, v in rel_data.items() if k in DerivedFrom.fields()},
        )
    # logging
    end_time = time.time()
    logger.info(f"Job={model_id} completed in {end_time - start_time:.2f} seconds")


def merge_renamed_models(model_id: str, new_model_id: t.Optional[str]) -> None:
    """Merge two models."""
    repository: 'repositories.GraphRepository' = get_graph_repository()
    if model_id != new_model_id and new_model_id:
        repository.merge_nodes(
            label="Model",
            src_id=model_id,
            dst_id=new_model_id,
        )
