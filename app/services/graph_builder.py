def build_graph(entities: list, relations: list = None):
    """
    Builds a node/edge graph structure from entities.
    If no explicit relations are given, creates co-occurrence edges
    between all detected entities (simple but effective for visualization).
    """
    nodes = [{"id": i, "label": e["name"], "type": e["type"]} for i, e in enumerate(entities)]

    if relations:
        edges = relations
    else:
        # Simple co-occurrence: connect entities of different types
        # (e.g. link a DISEASE to a CHEMICAL, since they likely interact in the text)
        edges = []
        for i, source in enumerate(nodes):
            for j, target in enumerate(nodes):
                if i < j and source["type"] != target["type"]:
                    edges.append({
                        "source": source["id"],
                        "target": target["id"],
                        "relation_type": "CO_OCCURS_WITH"
                    })

    return {"nodes": nodes, "edges": edges}