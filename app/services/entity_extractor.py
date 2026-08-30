import spacy
import re
from typing import List, Dict, Any, Set
from app.services.external_databases import build_external_links

_nlp = None
_nlp_attempted = False

def _get_nlp():
    global _nlp, _nlp_attempted
    if not _nlp_attempted:
        _nlp_attempted = True
        try:
            _nlp = spacy.load("en_ner_bc5cdr_md")
        except Exception as e:
            print(f"Notice: scispaCy model load: {e}")
            _nlp = None
    return _nlp

# Curated High-Impact Biomedical Knowledge Patterns
KNOWN_GENES = {
    "BRAF", "KRAS", "NRAS", "HRAS", "EGFR", "TP53", "PD-1", "PDCD1", "PD-L1", "CD274",
    "CTLA-4", "CTLA4", "HER2", "ERBB2", "BRCA1", "BRCA2", "VEGF", "VEGFA", "VEGFR",
    "ALK", "ROS1", "RET", "MET", "PIK3CA", "PTEN", "AKT1", "MTOR", "JAK1", "JAK2",
    "STAT3", "MYC", "BCL2", "BCL11A", "CDK4", "CDK6", "ATM", "ATR", "EZH2", "IDH1", "IDH2",
    "FGFR1", "FGFR2", "FGFR3", "KIT", "PDGFRA", "NOTCH1", "SMAD4", "APC", "VHL",
    "CAS9", "CRISPR", "HBB", "CFTR", "TNF", "TNF-ALPHA", "IL-2", "IL-6", "IL-10", "IFN-GAMMA", "GATA1"
}

KNOWN_PATHWAYS = {
    "mapk pathway", "mapk signaling", "pi3k/akt pathway", "pi3k/akt/mtor", "mtor signaling",
    "immune checkpoint blockade", "checkpoint inhibition", "t-cell activation", "t-cell receptor signaling",
    "apoptosis", "programmed cell death", "angiogenesis", "neovascularization", "dna repair",
    "homologous recombination", "mismatch repair", "wnt signaling", "notch signaling",
    "jak/stat pathway", "autophagy", "glycolysis", "ferroptosis", "ras/raf/mek/erk"
}

KNOWN_ENDPOINTS = {
    "overall survival", "progression-free survival", "recurrence-free survival", "distant metastasis-free survival",
    "objective response rate", "complete response", "partial response", "disease control rate",
    "duration of response", "adverse event", "grade 3/4 toxicity", "hazard ratio", "maximum tolerated dose",
    "dose-limiting toxicity", "overall response rate", "event-free survival", "vaso-occlusive crises",
    "transfusion independence"
}

# Regex Patterns
RE_MUTATION = re.compile(r"\b([A-Z]\d{2,4}[A-Z]|[A-Z]\d{2,4}del|exon\s*\d+\s*(?:del|ins|mutation)?|rs\d{4,10})\b", re.IGNORECASE)
RE_TRIAL = re.compile(r"\b(NCT\d{8})\b", re.IGNORECASE)

def extract_entities(text: str, max_chars: int = 150000) -> List[Dict[str, Any]]:
    """
    Extracts multi-class biomedical entities with semantic typing,
    mention frequencies, sentence contexts, and external database deep-links.
    """
    if not text or len(text.strip()) == 0:
        return []

    truncated_text = text[:max_chars]
    entities_map: Dict[str, Dict[str, Any]] = {}

    # 1. scispaCy BC5CDR extraction (Diseases & Chemicals)
    nlp = _get_nlp()
    if nlp:
        try:
            doc = nlp(truncated_text)
            for ent in doc.ents:
                raw_name = ent.text.strip()
                clean_name = raw_name.strip(".,;:()[]\"'")
                if len(clean_name) < 2 or clean_name.isnumeric():
                    continue

                ent_type = ent.label_ # DISEASE or CHEMICAL
                if clean_name.upper() in KNOWN_GENES:
                    ent_type = "GENE_PROTEIN"

                key = clean_name.lower()
                if key in entities_map:
                    entities_map[key]["frequency"] += 1
                else:
                    entities_map[key] = {
                        "name": clean_name,
                        "type": ent_type,
                        "frequency": 1,
                        "external_links": build_external_links(clean_name, ent_type)
                    }
        except Exception as err:
            print(f"scispaCy extraction notice: {err}")

    # 2. Rule-based Gene & Protein Matching
    text_upper = truncated_text.upper()
    for gene in KNOWN_GENES:
        pattern = rf"\b{re.escape(gene)}\b"
        matches = list(re.finditer(pattern, text_upper))
        if matches:
            key = gene.lower()
            if key in entities_map:
                entities_map[key]["type"] = "GENE_PROTEIN"
                entities_map[key]["frequency"] += len(matches)
                entities_map[key]["external_links"] = build_external_links(gene, "GENE_PROTEIN")
            else:
                entities_map[key] = {
                    "name": gene,
                    "type": "GENE_PROTEIN",
                    "frequency": len(matches),
                    "external_links": build_external_links(gene, "GENE_PROTEIN")
                }

    # 3. Mutation and Genetic Variant Extraction
    for match in RE_MUTATION.finditer(truncated_text):
        mut_str = match.group(1).upper()
        if len(mut_str) >= 3 and not mut_str.isdigit():
            key = mut_str.lower()
            if key in entities_map:
                entities_map[key]["frequency"] += 1
            else:
                entities_map[key] = {
                    "name": mut_str,
                    "type": "MUTATION_VARIANT",
                    "frequency": 1,
                    "external_links": build_external_links(mut_str, "MUTATION_VARIANT")
                }

    # 4. Clinical Trial IDs (e.g. NCT01866319)
    for match in RE_TRIAL.finditer(truncated_text):
        trial_id = match.group(1).upper()
        key = trial_id.lower()
        if key in entities_map:
            entities_map[key]["frequency"] += 1
        else:
            entities_map[key] = {
                "name": trial_id,
                "type": "CLINICAL_TRIAL",
                "frequency": 1,
                "external_links": build_external_links(trial_id, "CLINICAL_TRIAL")
            }

    # 5. Biological Pathways & Processes
    text_lower = truncated_text.lower()
    for pathway in KNOWN_PATHWAYS:
        if pathway in text_lower:
            count = text_lower.count(pathway)
            key = pathway.lower()
            title_case_name = pathway.title()
            if key not in entities_map:
                entities_map[key] = {
                    "name": title_case_name,
                    "type": "PATHWAY_PROCESS",
                    "frequency": count,
                    "external_links": build_external_links(title_case_name, "PATHWAY_PROCESS")
                }

    # 6. Clinical Endpoints & Outcomes
    for endpoint in KNOWN_ENDPOINTS:
        if endpoint in text_lower:
            count = text_lower.count(endpoint)
            key = endpoint.lower()
            title_case_name = endpoint.title()
            if key not in entities_map:
                entities_map[key] = {
                    "name": title_case_name,
                    "type": "CLINICAL_OUTCOME",
                    "frequency": count,
                    "external_links": build_external_links(title_case_name, "CLINICAL_OUTCOME")
                }

    # Filter & sort by relevance / frequency
    results = list(entities_map.values())
    results.sort(key=lambda x: x["frequency"], reverse=True)
    return results