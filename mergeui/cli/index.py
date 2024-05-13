import typing as t
from pathlib import Path
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
from utils.data_extraction import list_model_infos, hf_whoami
from core.schema import Model
from utils.jobs import index_model_by_id, merge_renamed_models


def wait_for_jobs(jobs: list[rq.job.Job], q: rq.Queue) -> None:
    """Wait for all jobs to finish with re-scheduling failed jobs."""
    while True:
        # keep waiting if any job is keep running (not finished and not failed)
        if any(not job.is_finished and not job.is_failed for job in jobs):
            logger.debug(f"Waiting for {len(jobs)} jobs execution...")
            time.sleep(min(5, max(len(jobs) // 10, 1)))
            continue
        # auto requeue failed jobs
        failed_registry = q.failed_job_registry
        failed_job_ids = failed_registry.get_job_ids()
        for failed_job_id in failed_job_ids:
            failed_registry.requeue(failed_job_id)
            logger.warning(f"Failed job {failed_job_id} requeued")
        # stop when all jobs are finished and no failed jobs requeued
        if not failed_job_ids:
            break


def index_models(limit: t.Optional[int] = None) -> None:
    """Index All models from the HuggingFace Hub"""
    settings: 'core.settings.Settings' = get_settings()
    r = redis.Redis(
        host=settings.redis_dsn.host,
        port=settings.redis_dsn.port,
        db=settings.redis_dsn.path.replace("/", "")
    )
    q = rq.Queue(connection=r)
    repository: 'repositories.GraphRepository' = get_graph_repository()
    track_model_ids = []
    # logging whoami
    hf_whoami()
    # list models from the hub
    model_info_list_params = dict(
        tags="merge", sort="createdAt", direction=-1,
        limit=limit,
        fetch_config=False, card_data=False, full=False
    )
    model_info_list: list[hf_api.ModelInfo] = list_model_infos(**model_info_list_params)
    model_ids = [mi.id for mi in model_info_list]
    # download dataset
    logger.debug(f"Downloading dataset: HF_HUB_ENABLE_HF_TRANSFER={os.environ.get('HF_HUB_ENABLE_HF_TRANSFER')}...")
    results_dataset_folder = Path(hf.snapshot_download(
        repo_id='open-llm-leaderboard/results',
        repo_type='dataset',
        allow_patterns="*.json",
    ))
    logger.debug(f"Dataset downloaded to: {results_dataset_folder}")
    while model_ids:
        track_model_ids += model_ids
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
        # logging
        end_time = time.time()
        logger.debug(f"Iteration completed in {end_time - start_time:.2f} seconds")
        # prepare next iteration
        models = repository.list_nodes(label="Model", filters=dict(indexed=False))
        models = t.cast(list[Model], models)
        model_ids = [model.id for model in models]
    # handling all moved models
    models = repository.list_nodes(label="Model", filters=dict(indexed=True))
    models = t.cast(list[Model], models)
    moved_pairs = []
    for model in models:
        new_model_id = model._properties.get("new_id")
        if new_model_id and model.id != new_model_id:
            logger.warning(f"Model {model.id} has been moved to {new_model_id}")
            moved_pairs.append((model.id, new_model_id))
    # schedule moved jobs
    jobs = q.enqueue_many([
        q.prepare_data(
            merge_renamed_models,
            [model_id, new_model_id],
            timeout=60 * 2,  # 2 minutes
            result_ttl=60 * 60 * 2,  # 2 hours
            failure_ttl=60 * 60 * 2,  # 2 hours
            job_id=f"merge_renamed_models__{model_id.replace('/', '__')}__to__{new_model_id.replace('/', '__')}"
        ) for model_id, new_model_id in moved_pairs
    ])
    # wait for jobs
    wait_for_jobs(jobs, q)
    # logging
    logger.info(f"Indexed {len(models)} models, {len(moved_pairs)} moved")


def main(limit: t.Optional[str] = None, reset_db: bool = True) -> None:
    """Entry point for the index CLI command."""
    start_time = time.time()
    repository: 'repositories.GraphRepository' = get_graph_repository()
    if reset_db:
        repository.db_conn.setup(reset_if_not_empty=True)
    db_index__indexed = gq.MemgraphIndex("Model", property="indexed")
    # setup
    logger.debug(f"Creating indexes...")
    repository.db_conn.db.create_index(db_index__indexed)
    logger.debug(f"Indexes created")
    # indexing models
    index_models(int(limit) if limit is not None else limit)
    # teardown
    logger.debug(f"Removing extra properties...")
    repository.remove_properties(label="Model", filters=dict(indexed=True), keys={"indexed", "new_id"})
    logger.debug(f"Extra properties removed")
    logger.debug(f"Dropping indexes...")
    repository.db_conn.db.drop_index(db_index__indexed)
    logger.debug(f"Indexes dropped")
    end_time = time.time()
    logger.info(f"completed in {end_time - start_time:.2f} seconds")
