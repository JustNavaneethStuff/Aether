from uuid import uuid4

from aether_common.domain.task_graph import TaskNode, topological_sort


def test_topological_sort_linear() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    nodes = [
        TaskNode(id=a, agent_name="research", depends_on=[]),
        TaskNode(id=b, agent_name="critic", depends_on=[a]),
        TaskNode(id=c, agent_name="summarizer", depends_on=[b]),
    ]
    sorted_nodes = topological_sort(nodes)
    assert [n.agent_name for n in sorted_nodes] == ["research", "critic", "summarizer"]


def test_topological_sort_parallel() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    nodes = [
        TaskNode(id=a, agent_name="research", depends_on=[]),
        TaskNode(id=b, agent_name="critic", depends_on=[]),
        TaskNode(id=c, agent_name="summarizer", depends_on=[a, b]),
    ]
    sorted_nodes = topological_sort(nodes)
    names = [n.agent_name for n in sorted_nodes]
    assert names.index("summarizer") > names.index("research")
    assert names.index("summarizer") > names.index("critic")
