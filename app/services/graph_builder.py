def build_graph(entities: list, relations: list = None):
    """
    Builds a simple node/edge graph structure from entities.
    Returns a dict compatible with graph visualization libraries.
    """
    nodes = [{"id": i, "label": e["name"], "type": e["type"]} for i, e in enumerate(entities)]
    edges = relations or []
    return {"nodes": nodes, "edges": edges}