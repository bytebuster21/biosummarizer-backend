import spacy

# Load the biomedical NER model once at startup
_nlp = spacy.load("en_ner_bc5cdr_md")


def extract_entities(text: str, max_chars: int = 100000) -> list:
    """
    Extracts biomedical entities (diseases, chemicals/drugs) from text
    using a pretrained scispaCy NER model.
    Returns list of dicts: {"name": ..., "type": ...}
    """
    if not text or len(text.strip()) == 0:
        return []

    # Cap input size to avoid extremely long processing times
    truncated_text = text[:max_chars]

    doc = _nlp(truncated_text)

    seen = set()
    entities = []

    for ent in doc.ents:
        name = ent.text.strip()
        entity_type = ent.label_  # "DISEASE" or "CHEMICAL"

        # Deduplicate (case-insensitive)
        key = (name.lower(), entity_type)
        if key in seen or len(name) < 2:
            continue
        seen.add(key)

        entities.append({"name": name, "type": entity_type})

    return entities