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


def test_list_property_values__exclude_none(graph_repository):
    choices = graph_repository.list_property_values(key="merge_method", exclude_none=True)
    assert isinstance(choices, list)
    assert "slerp" in choices
    assert None not in choices


def test_list_nodes(graph_repository):
    result = graph_repository.list_nodes()
    assert len(result) == 6
    assert isinstance(result[0], gq.Node)


def test_list_nodes__limit(graph_repository):
    result = graph_repository.list_nodes(limit=2)
    assert len(result) == 2


def test_list_nodes__filters(graph_repository):
    result = graph_repository.list_nodes(filters=dict(merge_method="slerp"))
    assert len(result) == 2


def test_get_sub_graph(graph_repository):
    # top node
    gr = graph_repository.get_sub_graph(start_id='Q-bert/MetaMath-Cybertron-Starling')
    assert len(gr.nodes) == 5
    assert isinstance(gr.nodes[0], gq.Node)
    assert len(gr.relationships) == 7
    assert isinstance(gr.relationships[0], gq.Relationship)
    # isolated node
    gr = graph_repository.get_sub_graph(start_id='mistralai/Mistral-7B-v0.1')
    assert len(gr.nodes) == 1
    assert len(gr.relationships) == 0
    # invalid node
    gr = graph_repository.get_sub_graph(start_id='x/y')
    assert len(gr.nodes) == 0
    assert len(gr.relationships) == 0
    # middle node
    gr = graph_repository.get_sub_graph(start_id='Q-bert/MetaMath-Cybertron')
    assert len(gr.nodes) == 5
    assert len(gr.relationships) == 7
    # bottom node
    gr = graph_repository.get_sub_graph(start_id='berkeley-nest/Starling-LM-7B-alpha')
    assert len(gr.nodes) == 5
    assert len(gr.relationships) == 7
    # empty id
    gr = graph_repository.get_sub_graph(start_id='')
    assert len(gr.nodes) == 0
    assert len(gr.relationships) == 0
