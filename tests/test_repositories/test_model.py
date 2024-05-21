from core.schema import Model


def test_list_models(model_repository):
    # get all
    result = model_repository.list_models()
    assert len(result) == 6
    assert isinstance(result[0], Model)
    # limit
    result = model_repository.list_models(limit=2)
    assert len(result) == 2
    # get by license only
    result = model_repository.list_models(filters=dict(license='cc-by-nc-4.0'))
    assert len(result) == 1
    # get by search query only
    result = model_repository.list_models(query='cc-by-nc')
    assert len(result) == 1
    # get by license and architecture
    result = model_repository.list_models(filters=dict(license='cc-by-nc-4.0', architecture="MistralForCausalLM"))
    assert len(result) == 1
    result = model_repository.list_models(filters=dict(license='cc-by-nc-4.0', architecture="NotFound"))
    assert len(result) == 0
    # exclude
    result = model_repository.list_models(filters=dict(license='apache-2.0'))
    assert len(result) == 5
    result = model_repository.list_models(filters=dict(license='apache-2.0'), label="MergedModel")
    assert len(result) == 1
    result = model_repository.list_models(filters=dict(license='apache-2.0'), not_label="MergedModel")
    assert len(result) == 4
    # base_model
    result = model_repository.list_models(filters=dict(license='apache-2.0'), label="MergedModel",
                                          base_model="fblgit/una-cybertron-7b-v2-bf16")
    assert len(result) == 1
    result = model_repository.list_models(filters=dict(license='apache-2.0'), label="MergedModel",
                                          base_model="mistralai/Mistral-7B-v0.1")
    assert len(result) == 0
    # get by search query only
    result = model_repository.list_models(query='hola')
    assert len(result) == 0
    result = model_repository.list_models(query='hola', filters=dict(license='apache-2.0'))
    assert len(result) == 0
    # search query with license
    result = model_repository.list_models(query='cc-by-nc', filters=dict(license='cc-by-nc-4.0'))
    assert len(result) == 1
    result = model_repository.list_models(query='MistralForCausalLM', filters=dict(license='apache-2.0'))
    assert len(result) == 5
    # merge_method
    result = model_repository.list_models(filters=dict(merge_method='slerp'))
    assert len(result) == 2
