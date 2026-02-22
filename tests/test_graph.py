import os
import tempfile
import networkx as nx
from agent_scorecard.graph import build_dependency_graph, analyze_graph


def test_build_dependency_graph() -> None:
    """
    Tests building a dependency graph from a simple package structure.

    This test verifies that the builder correctly identifies internal
    module dependencies while correctly handling relative imports.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a small package structure
        pkg_dir = os.path.join(tmpdir, "mypkg")
        os.makedirs(pkg_dir)

        main_py = os.path.join(pkg_dir, "main.py")
        utils_py = os.path.join(pkg_dir, "utils.py")
        init_py = os.path.join(pkg_dir, "__init__.py")

        with open(init_py, "w") as f:
            f.write("")

        with open(main_py, "w") as f:
            f.write("from . import utils\nimport mypkg.utils")

        with open(utils_py, "w") as f:
            f.write("import os")

        graph = build_dependency_graph(tmpdir)

        assert isinstance(graph, nx.DiGraph)
        assert os.path.abspath(main_py) in graph.nodes
        assert os.path.abspath(utils_py) in graph.nodes

        # main.py depends on utils.py
        assert graph.has_edge(os.path.abspath(main_py), os.path.abspath(utils_py))


def test_circular_dependency() -> None:
    """
    Tests detection of circular dependencies in the graph.

    Circular dependencies increase 'Dependency Entanglement' and
    confuse AI agents during recursive analysis.

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        a_py = os.path.join(tmpdir, "a.py")
        b_py = os.path.join(tmpdir, "b.py")

        with open(a_py, "w") as f:
            f.write("import b")
        with open(b_py, "w") as f:
            f.write("import a")

        graph = build_dependency_graph(tmpdir)
        analysis = analyze_graph(graph)

        assert len(analysis["cycles"]) > 0
        # The cycle should contain both a.py and b.py
        cycle = analysis["cycles"][0]
        assert os.path.abspath(a_py) in cycle
        assert os.path.abspath(b_py) in cycle


def test_god_module() -> None:
    """
    Tests detection of 'God Modules' based on in-degree.

    A 'God Module' is defined as a file with > 50 inbound references,
    representing a high-pressure context point for AI agents.

    Returns:
        None
    """
    # RESOLUTION: Maintained Beta branch explicit typing for graph object
    graph: nx.DiGraph = nx.DiGraph()
    god_node = "god.py"
    graph.add_node(god_node)

    # Create a star-pattern graph to trigger the God Module threshold
    for i in range(51):
        other = f"other_{i}.py"
        graph.add_edge(other, god_node)

    analysis = analyze_graph(graph)
    assert len(analysis["god_modules"]) == 1
    assert analysis["god_modules"][0]["file"] == god_node
    assert analysis["god_modules"][0]["in_degree"] == 51
