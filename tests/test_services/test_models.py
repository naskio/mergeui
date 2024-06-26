def test_get_model_id_choices(model_service):
    result = model_service.get_model_id_choices()
    assert 'fblgit/una-cybertron-7b-v2-bf16' in result
    assert None not in result


def test_get_license_choices(model_service):
    result = model_service.get_license_choices()
    assert 'apache-2.0' in result
    assert None not in result


def test_get_author_choices(model_service):
    result = model_service.get_author_choices()
    assert 'Q-bert' in result
    assert None not in result


def test_get_merge_method_choices(model_service):
    result = model_service.get_merge_method_choices()
    assert 'slerp' in result
    assert None not in result


def test_get_architecture_choices(model_service):
    result = model_service.get_architecture_choices()
    assert 'MistralForCausalLM' in result
    assert None not in result


def test_get_model_lineage(model_service):
    result = model_service.get_model_lineage(model_id='fblgit/una-cybertron-7b-v2-bf16', directed=False)
    assert len(result.nodes) == 3
    assert len(result.relationships) == 4
    result = model_service.get_model_lineage(model_id='fblgit/una-cybertron-7b-v2-bf16', directed=True)
    assert len(result.nodes) == 1
    assert len(result.relationships) == 0
    result = model_service.get_model_lineage(model_id='Q-bert/MetaMath-Cybertron', directed=True)
    assert len(result.nodes) == 3
    assert len(result.relationships) == 3


def test_list_models(model_service):
    result = model_service.list_models(
        query='MistralForCausalLM',
    )
    assert len(result) > 0


def test_list_models__exclude(model_service):
    result = model_service.list_models(
        license_='apache-2.0',
    )
    assert len(result) == 5
    result = model_service.list_models(
        license_='apache-2.0',
        excludes=['base models']
    )
    assert len(result) == 1
    result = model_service.list_models(
        license_='apache-2.0',
        excludes=['merged models']
    )
    assert len(result) == 4


def test_list_models__sort_by(model_service):
    result = model_service.list_models(
        license_='apache-2.0',
        sort_by='most likes',
    )
    assert len(result) == 5
    assert result[0].likes > result[1].likes > result[-1].likes
    # with null values
    result = model_service.list_models(
        license_='apache-2.0',
        sort_by='average score',
    )
    assert len(result) == 4  # 1 model has null average_score is being excluded
    assert result[0].average_score > result[1].average_score > result[-1].average_score


def test_get_default_model_id(model_service):
    result = model_service.get_default_model_id()
    assert result == "Q-bert/MetaMath-Cybertron-Starling"
