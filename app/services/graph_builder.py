import re
from typing import List, Dict, Any

# Relationship Trigger Patterns
RELATION_PATTERNS = [
    (re.compile(r"\b(?:treats?|treated|treatment\s+of|therapy\s+for|effective\s+against|targeting)\b", re.IGNORECASE), "TREATS"),
    (re.compile(r"\b(?:inhibits?|inhibition\s+of|blocked|blockade\s+of|suppresses?|antagonist)\b", re.IGNORECASE), "INHIBITS"),
    (re.compile(r"\b(?:mutat(?:ed|ion)\s+in|harboring|variant\s+of|encoded\s+by)\b", re.IGNORECASE), "MUTATED_IN"),
    (re.compile(r"\b(?:biomarker|predictive\s+of|correlated\s+with|marker\s+for)\b", re.IGNORECASE), "BIOMARKER_FOR"),
    (re.compile(r"\b(?:prolongs?|improved|superior\s+to|increased|boosted)\b", re.IGNORECASE), "IMPROVES"),
    (re.compile(r"\b(?:adverse|toxicity|induced|caused|side\s+effect)\b", re.IGNORECASE), "ADVERSE_EFFECT"),
    (re.compile(r"\b(?:expressed\s+in|upregulated|overexpressed|activation\s+of)\b", re.IGNORECASE), "UPREGULATES"),
    (re.compile(r"\b(?:associated\s+with|linked\s+to|involved\s+in)\b", re.IGNORECASE), "ASSOCIATED_WITH"),
]

def _infer_semantic_relation(ent1_type: str, ent2_type: str, sentence_context: str = "") -> str:
    """
    Infers the most accurate semantic relation type based on sentence text
    and entity types.
    """
    t1, t2 = ent1_type.upper(), ent2_type.upper()

    if sentence_context:
        for pattern, rel_type in RELATION_PATTERNS:
            if pattern.search(sentence_context):
                return rel_type

    # Fallback to domain heuristics
    if ("CHEMICAL" in t1 or "DRUG" in t1) and ("DISEASE" in t2):
        return "TREATS"
    if ("CHEMICAL" in t1 or "DRUG" in t1) and ("GENE" in t2 or "PROTEIN" in t2):
        return "INHIBITS_TARGET"
    if ("MUTATION" in t1) and ("GENE" in t2):
        return "MUTATION_OF"
    if ("GENE" in t1 or "PROTEIN" in t1) and ("DISEASE" in t2):
        return "ASSOCIATED_WITH"
    if ("CHEMICAL" in t1 or "DRUG" in t1) and ("CLINICAL_OUTCOME" in t2):
        return "IMPROVES"
    if ("PATHWAY" in t1) and ("DISEASE" in t2):
        return "DYSREGULATED_IN"

    return "CO_OCCURS_WITH"


def build_graph(entities: List[Dict[str, Any]], full_text: str = "", max_nodes: int = 40) -> Dict[str, Any]:
    """
    Constructs an interactive semantic knowledge graph.
    Extracts nodes with centrality, frequency, external links, and
    directed typed edges with sentence evidence.
    """
    if not entities:
        return {"nodes": [], "edges": [], "summary_stats": {"total_nodes": 0, "total_edges": 0}}

    # Take top entities by frequency to keep graph intelligible and responsive
    selected_entities = entities[:max_nodes]

    # Create Nodes
    nodes = []
    entity_id_map = {}
    for i, ent in enumerate(selected_entities):
        node_id = i + 1
        name = ent["name"]
        entity_id_map[name.lower()] = node_id
        nodes.append({
            "id": node_id,
            "label": name,
            "type": ent["type"],
            "frequency": ent.get("frequency", 1),
            "external_links": ent.get("external_links", {}),
            "degree": 0
        })

    # Break text into sentences for co-occurrence and relation extraction
    sentences = re.split(r'(?<=[.!?])\s+', full_text) if full_text else []
    edges_map: Dict[tuple, Dict[str, Any]] = {}

    # Scan co-occurrences in sentences
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if len(sentence_clean) < 10:
            continue
        sentence_lower = sentence_clean.lower()

        # Find which entities appear in this sentence
        present_nodes = []
        for node in nodes:
            if node["label"].lower() in sentence_lower:
                present_nodes.append(node)

        # Connect pairs in the sentence
        for i in range(len(present_nodes)):
            for j in range(i + 1, len(present_nodes)):
                n1 = present_nodes[i]
                n2 = present_nodes[j]

                # Determine direction: Chemical -> Disease/Gene, Mutation -> Gene, etc.
                src, tgt = n1, n2
                if ("DISEASE" in n1["type"] and "CHEMICAL" in n2["type"]) or \
                   ("GENE" in n1["type"] and "MUTATION" in n2["type"]):
                    src, tgt = n2, n1

                pair_key = (src["id"], tgt["id"])
                relation = _infer_semantic_relation(src["type"], tgt["type"], sentence_clean)

                if pair_key in edges_map:
                    edges_map[pair_key]["weight"] += 1
                    if len(edges_map[pair_key]["evidence"]) < 3 and sentence_clean not in edges_map[pair_key]["evidence"]:
                        edges_map[pair_key]["evidence"].append(sentence_clean)
                else:
                    edges_map[pair_key] = {
                        "source": src["id"],
                        "target": tgt["id"],
                        "source_label": src["label"],
                        "target_label": tgt["label"],
                        "relation_type": relation,
                        "weight": 1,
                        "evidence": [sentence_clean]
                    }

    # If few edges found through exact sentence co-occurrence, add meaningful cross-type heuristic links
    if len(edges_map) < 3 and len(nodes) > 1:
        for i, src in enumerate(nodes):
            for j, tgt in enumerate(nodes):
                if i < j and src["type"] != tgt["type"]:
                    pair_key = (src["id"], tgt["id"])
                    relation = _infer_semantic_relation(src["type"], tgt["type"])
                    edges_map[pair_key] = {
                        "source": src["id"],
                        "target": tgt["id"],
                        "source_label": src["label"],
                        "target_label": tgt["label"],
                        "relation_type": relation,
                        "weight": 1,
                        "evidence": []
                    }
                    if len(edges_map) >= 25:
                        break
            if len(edges_map) >= 25:
                break

    edges = list(edges_map.values())

    # Compute node degrees
    degree_counts: Dict[int, int] = {}
    for edge in edges:
        degree_counts[edge["source"]] = degree_counts.get(edge["source"], 0) + 1
        degree_counts[edge["target"]] = degree_counts.get(edge["target"], 0) + 1

    for node in nodes:
        node["degree"] = degree_counts.get(node["id"], 0)

    # Compute high-level summary statistics
    type_distribution: Dict[str, int] = {}
    for node in nodes:
        t = node["type"]
        type_distribution[t] = type_distribution.get(t, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "summary_stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "type_distribution": type_distribution
        }
    }