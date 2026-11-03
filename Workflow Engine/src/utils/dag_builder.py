import networkx as nx
from typing import Dict, List

def build_dag(definition: Dict) -> nx.DiGraph:
    steps = definition.get("steps", [])
    dag = nx.DiGraph()
    for step in steps:
        dag.add_node(step["id"], **step)
    for step in steps:
        step_id = step["id"]
        for dep in step.get("depends_on", []):
            dag.add_edge(dep, step_id)
    if not nx.is_directed_acyclic_graph(dag):
        raise ValueError("Workflow definition contains cycles")
    return dag
