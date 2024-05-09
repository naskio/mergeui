import gqlalchemy as gq


def test_list_property_values(graph_repository):
    choices = graph_repository.list_property_values(key="license")
    assert isinstance(choices, list)
    assert "apache-2.0" in choices
    assert None not in choices
    assert choices == sorted(choices)


def test_list_property_values__none(graph_repository):
    choices = graph_repository.list_property_values(key="merge_method")
    assert isinstance(choices, list)
    assert "slerp" in choices
    assert None in choices


def test_list_nodes(graph_repository):
    result = graph_repository.list_nodes()
    assert len(result) == 6
    assert isinstance(result[0], gq.Node)


def test_list_nodes__limit(graph_repository):
    result = graph_repository.list_nodes(limit=2)
    assert len(result) == 2


def test_list_models(graph_repository):
    # get all
    result = graph_repository.list_models()
    assert len(result) == 6
    assert isinstance(result[0], gq.Node)
    # limit
    result = graph_repository.list_models(limit=2)
    assert len(result) == 2
    # get by license only
    result = graph_repository.list_models(license_='cc-by-nc-4.0')
    assert len(result) == 1
    # get by search query only
    result = graph_repository.list_models(query='cc-by-nc')
    assert len(result) == 1
    # get by license and architecture
    result = graph_repository.list_models(license_='cc-by-nc-4.0', architecture="MistralForCausalLM")
    assert len(result) == 1
    result = graph_repository.list_models(license_='cc-by-nc-4.0', architecture="NotFound")
    assert len(result) == 0
    # exclude
    result = graph_repository.list_models(license_='apache-2.0')
    assert len(result) == 5
    result = graph_repository.list_models(license_='apache-2.0', label="MergedModel")
    assert len(result) == 1
    result = graph_repository.list_models(license_='apache-2.0', not_label="MergedModel")
    assert len(result) == 4
    # base_model
    result = graph_repository.list_models(license_='apache-2.0', label="MergedModel",
                                          base_model="fblgit/una-cybertron-7b-v2-bf16")
    assert len(result) == 1
    result = graph_repository.list_models(
        license_='apache-2.0', label="MergedModel",
        base_model="mistralai/Mistral-7B-v0.1")
    assert len(result) == 0
    # get by search query only
    result = graph_repository.list_models(query='hola')
    assert len(result) == 0
    result = graph_repository.list_models(query='hola', license_='apache-2.0')
    assert len(result) == 0
    # search query with license
    result = graph_repository.list_models(query='cc-by-nc', license_='cc-by-nc-4.0')
    assert len(result) == 1
    result = graph_repository.list_models(query='MistralForCausalLM', license_='apache-2.0')
    assert len(result) == 5
    # merge_method
    result = graph_repository.list_models(merge_method='slerp')
    assert len(result) == 2


def test_get_sub_graph(graph_repository):
    # top node
    gr = graph_repository.get_sub_graph(id_='Q-bert/MetaMath-Cybertron-Starling')
    assert len(gr.nodes) == 5
    assert isinstance(gr.nodes[0], gq.Node)
    assert len(gr.relationships) == 7
    assert isinstance(gr.relationships[0], gq.Relationship)
    # isolated node
    gr = graph_repository.get_sub_graph(id_='mistralai/Mistral-7B-v0.1')
    assert len(gr.nodes) == 1
    assert len(gr.relationships) == 0
    # invalid node
    gr = graph_repository.get_sub_graph(id_='x/y')
    assert len(gr.nodes) == 0
    assert len(gr.relationships) == 0
    # middle node
    gr = graph_repository.get_sub_graph(id_='Q-bert/MetaMath-Cybertron')
    assert len(gr.nodes) == 5
    assert len(gr.relationships) == 7
    # bottom node
    gr = graph_repository.get_sub_graph(id_='berkeley-nest/Starling-LM-7B-alpha')
    assert len(gr.nodes) == 5
    assert len(gr.relationships) == 7
    # empty id
    gr = graph_repository.get_sub_graph(id_='')
    assert len(gr.nodes) == 0
    assert len(gr.relationships) == 0
