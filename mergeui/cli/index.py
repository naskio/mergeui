import typing as t
import datetime as dt
import json
import os
from loguru import logger
import time
import redis
import rq
import huggingface_hub as hf
from huggingface_hub import hf_api
import gqlalchemy as gq
import core.settings
import core.db
import repositories
from core.dependencies import get_settings, get_graph_repository
from utils import filter_none, custom_serializer, log_progress, format_duration
from utils.index.data_extraction import list_model_infos, hf_whoami
from utils.index.jobs import index_model_by_id


def wait_for_jobs(jobs: list[rq.job.Job], q: rq.Queue, auto_reschedule: bool = True) -> None:
    """Wait for all jobs to finish with re-scheduling failed jobs."""
    while True:
        # keep waiting if any job is keep running (not finished and not failed)
        if any(not job.is_finished and not job.is_failed for job in jobs):
            logger.debug(f"Waiting for {len(jobs)} jobs execution...")
            time.sleep(min(5, max(len(jobs) // 10, 1)))  # sleep 1 second at least and 5 seconds at most
            continue
        if auto_reschedule:
            # auto requeue failed jobs
            failed_registry = q.failed_job_registry
            failed_job_ids = failed_registry.get_job_ids()
            for failed_job_id in failed_job_ids:
                failed_job = q.fetch_job(failed_job_id)
                logger.warning(f"Requeuing failed job {failed_job.id}...\n"
                               f"{failed_job.func_name}(args={failed_job.args}, kwargs={failed_job.kwargs})\n"
                               f"exc_string: {failed_job.latest_result().exc_string}")
                failed_registry.requeue(failed_job.id)
            # stop when all jobs are finished and no failed jobs requeued
            if not failed_job_ids:
                break
        else:
            break  # stop when all jobs are finished


def index_models(limit: t.Optional[int], local_files_only: bool = False) -> dict:
    """Index All models from the HuggingFace Hub"""
    nodes_map, rels_list = {}, []
    settings: 'core.settings.Settings' = get_settings()
    r = redis.Redis(
        host=settings.redis_dsn.host,
        port=settings.redis_dsn.port,
        db=settings.redis_dsn.path.replace("/", "")
    )
    q = rq.Queue(connection=r)
    # logging whoami
    hf_whoami()
    # download dataset
    logger.debug(f"Downloading dataset: HF_HUB_ENABLE_HF_TRANSFER={os.environ.get('HF_HUB_ENABLE_HF_TRANSFER')}"
                 f" and local_files_only={local_files_only}...")
    results_dataset_folder: str = hf.snapshot_download(
        repo_id='open-llm-leaderboard/results',
        repo_type='dataset',
        allow_patterns="*.json",
        local_files_only=local_files_only,
    )
    logger.debug(f"Dataset downloaded to: {results_dataset_folder}")
    # list models from the hub
    model_info_list_params = dict(
        tags="merge", sort="createdAt", direction=-1,
        limit=limit,
        fetch_config=False, card_data=False, full=False
    )
    model_info_list: list[hf_api.ModelInfo] = list_model_infos(**model_info_list_params)
    model_ids: set[str] = set([mi.id for mi in model_info_list])
    while model_ids:
        logger.debug(f"Indexing {len(model_ids)} models...")
        start_time = time.time()
        # # schedule jobs
        jobs = q.enqueue_many([
            q.prepare_data(
                index_model_by_id,
                [model_id, results_dataset_folder],
                timeout=60 * 2,  # 2 minutes
                result_ttl=60 * 60 * 2,  # 2 hours
                failure_ttl=60 * 60 * 2,  # 2 hours
                job_id=f"index_model_by_id__{model_id.replace('/', '__')}"
            ) for model_id in model_ids
        ])
        # wait for jobs
        wait_for_jobs(jobs, q)
        # get results
        for job in jobs:
            _got: tuple[dict, list] = job.return_value()
            new_node, new_rels = _got
            assert new_node.get("id") not in nodes_map, f"Model {new_node.get('id')} already indexed"
            nodes_map[new_node.get("id")] = new_node
            rels_list.extend(new_rels)
        # logging
        end_time = time.time()
        logger.debug(f"Iteration completed in {format_duration(start_time, end_time)}")
        # prepare next iteration
        model_ids = set(rel["target"] for rel in rels_list) - set(nodes_map.keys())
    # handling all renamed models
    rename_map = {}  # old_id -> new_id
    final_nodes_map = {}
    for node in nodes_map.values():
        old_id = node.get("id")
        new_id = node.get("new_id")
        # check if renamed
        if new_id and old_id != new_id:
            logger.warning(f"Model {old_id} has been moved to {new_id}")
            rename_map[old_id] = new_id
            # renaming
            node = {
                **node,
                "id": new_id,
                "alt_ids": [old_id],
            }
        # check if exists, merge with existing
        if node["id"] in final_nodes_map:
            existing_node = final_nodes_map.get(node["id"])
            node = {
                **node,
                **existing_node,
                "alt_ids": list(set(existing_node.get("alt_ids", [] + node.get("alt_ids", [])))),
            }
        final_nodes_map[node["id"]] = filter_none({
            **node,
            "new_id": None,
            "indexed": None,
        })
    # fixing relationships
    existing_rels = set()
    final_rels_list = []
    for rel in rels_list:
        source = rename_map.get(rel["source"], rel["source"])
        target = rename_map.get(rel["target"], rel["target"])
        rel_unique_key = source, target, rel["method"], rel["origin"]
        if rel_unique_key in existing_rels:
            continue
        final_rels_list.append(filter_none({
            **rel,
            "source": source,
            "target": target,
        }))
        existing_rels.add(rel_unique_key)
    # logging
    logger.success(f"=> {len(final_nodes_map)} models ({len(rename_map)} moved), {len(final_rels_list)} relationships")
    # return index graph
    return {
        "directed": True,
        "multigraph": True,
        "nodes_count": len(final_nodes_map),
        "relationships_count": len(final_rels_list),
        "nodes": list(final_nodes_map.values()),
        "relationships": final_rels_list,
    }


def main(
        limit: t.Optional[t.Union[str, int]] = None,
        reset_db: bool = True,
        save_json: bool = True,
        local_files_only: bool = False,
) -> None:
    """Entry point for the index CLI command."""
    start_time = time.time()
    limit = int(limit) if limit is not None else limit
    settings = get_settings()
    repository: 'repositories.GraphRepository' = get_graph_repository()
    # setup
    if reset_db:
        repository.db_conn.reset()
        repository.db_conn.setup_pre_populate()
    logger.debug(f"Creating extra indexes...")
    repository.db_conn.db.create_index(gq.MemgraphIndex("Model", property="indexed"))
    logger.debug(f"Extra indexes created")
    # indexing models
    index_graph: dict = index_models(limit, local_files_only=local_files_only)
    # save to json
    if save_json:
        index_graph_path = settings.project_dir / "media" / f"index_{dt.datetime.utcnow().isoformat()}.json"
        logger.debug(f"Saving index to json file...")
        index_graph_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_graph_path, "w") as f:
            json.dump(index_graph, f, indent=4, default=custom_serializer)
        logger.success(f"Index saved to file: {index_graph_path}")
    # import to Database
    logger.debug(f"Importing {index_graph.get('nodes_count')} nodes to database...")
    for ind, node in enumerate(index_graph["nodes"]):
        repository.set_properties(
            label="Model",
            filters=dict(id=node["id"]),
            new_values={k: v for k, v in node.items() if k not in {"id", "labels"}},
            new_labels=node["labels"],
            create=True,
        )
        log_progress(ind, index_graph["nodes_count"], step=5)
    logger.debug(f"Importing {index_graph.get('relationships_count')} relationships to database...")
    for ind, rel in enumerate(index_graph["relationships"]):
        repository.create_relationship(
            label="Model",
            from_id=rel["source"],
            to_id=rel["target"],
            relationship_type=rel["type"],
            properties={k: v for k, v in rel.items() if k not in {"source", "target", "type"}},
        )
        log_progress(ind, index_graph["relationships_count"], step=5)
    logger.success(f"Imported {index_graph['nodes_count']} nodes and {index_graph['relationships_count']} rels")
    # teardown
    logger.debug(f"Removing extra properties...")
    repository.remove_properties(label="Model", keys={"indexed", "new_id"})
    logger.debug(f"Extra properties removed")
    logger.debug(f"Dropping extra indexes...")
    repository.db_conn.db.drop_index(gq.MemgraphIndex("Model", property="indexed"))
    logger.debug(f"Extra indexes dropped")
    if reset_db:
        repository.db_conn.setup_post_populate()
    # logging
    end_time = time.time()
    logger.success(f"completed in {format_duration(start_time, end_time)}")


if __name__ == '__main__':
    main(10, local_files_only=True)
