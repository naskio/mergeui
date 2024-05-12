import pytest
import typing as t
import gqlalchemy as gq
from core.schema import Model


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


def test_count_nodes(graph_repository):
    assert graph_repository.count_nodes() == 6


@pytest.mark.run(order=-5)
def test_create_relationship(graph_repository):
    graph_repository.create_or_update(
        filters=dict(id='a'),
        create_values={'name': "A"},
        update_values={},
    )
    graph_repository.create_or_update(
        filters=dict(id='b'),
        create_values={'name': "B"},
        update_values={},
    )
    graph_repository.create_relationship(
        from_id='a',
        to_id='b',
        relationship_type='DUMMY_TYPE',
        properties={'x': 1, 'y': 2},
    )
    sub_graph = graph_repository.get_sub_graph(
        start_id='a',
    )
    assert len(sub_graph.nodes) == 2
    assert len(sub_graph.relationships) == 1
    assert sub_graph.relationships[0]._type == 'DUMMY_TYPE'


@pytest.mark.run(order=-4)
def test_set_properties(graph_repository):
    filters = dict(id='Q-bert/MetaMath-Cybertron-Starling')
    properties = {"a": "aa", "b": 18, "c": True, "d": ["d1", "d2"]}
    graph_repository.set_properties(filters=filters, new_values=properties)
    nodes = graph_repository.list_nodes(filters=filters)
    for node in nodes:
        for key, value in properties.items():
            assert getattr(node, key) == value


@pytest.mark.run(order=-3)
def test_remove_properties(graph_repository):
    filters = dict(id='Q-bert/MetaMath-Cybertron-Starling')
    keys = {"license", "merge_method", "author", "likes", "downloads"}
    graph_repository.remove_properties(filters=filters, keys=keys)
    nodes = graph_repository.list_nodes(filters=filters)
    for node in nodes:
        for key in keys:
            assert getattr(node, key) is None


@pytest.mark.run(order=-2)
def test_create_or_update(graph_repository):
    create_values = dict(x="y")
    update_values = dict(y=999)
    # exist
    filters = dict(id="Q-bert/MetaMath-Cybertron-Starling")
    graph_repository.create_or_update(
        filters=filters,
        create_values=create_values,
        update_values=update_values,
    )
    nodes = graph_repository.list_nodes(filters=filters)
    assert nodes
    for node in nodes:
        for key, value in update_values.items():
            assert getattr(node, key) == value
        for key, value in create_values.items():
            assert getattr(node, key, None) is None
    # new
    filters = dict(id="Q-bert/MetaMath-Cybertron-Starling-2")
    graph_repository.create_or_update(
        filters=filters,
        create_values=create_values,
        update_values=update_values,
    )
    nodes = graph_repository.list_nodes(filters=filters)
    assert nodes
    for node in nodes:
        for key, value in create_values.items():
            assert getattr(node, key) == value
        for key, value in update_values.items():
            assert getattr(node, key, None) is None


@pytest.mark.run(order=-1)
def test_merge_nodes(graph_repository):
    src_id = "Q-bert/MetaMath-Cybertron-Starling"
    dst_id = "Q-bert/MetaMath-Cybertron"
    graph_repository.merge_nodes(src_id=src_id, dst_id=dst_id)
    assert graph_repository.list_nodes(
        filters=dict(id=src_id)
    ) == []
    nodes = graph_repository.list_nodes(
        filters=dict(id=dst_id)
    )
    nodes = t.cast(t.List[Model], nodes)
    for node in nodes:
        assert node.id == dst_id
        assert node.author == "Q-bert"
        assert node.likes == 6  # existing
        assert node.average_score == 0.7124963716086201  # missing
        assert src_id in node.alt_ids
