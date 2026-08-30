import urllib.parse
import urllib.request
import json
import re
from typing import Dict, List, Any, Optional

# Knowledge Base Base URLs
NCBI_PUBMED_SEARCH = "https://pubmed.ncbi.nlm.nih.gov/?term="
NCBI_MESH_SEARCH = "https://www.ncbi.nlm.nih.gov/mesh/?term="
NCBI_CLINVAR_SEARCH = "https://www.ncbi.nlm.nih.gov/clinvar/?term="
NCBI_GENE_SEARCH = "https://www.ncbi.nlm.nih.gov/gene/?term="
UNIPROT_SEARCH = "https://www.uniprot.org/uniprotkb?query="
PUBCHEM_SEARCH = "https://pubchem.ncbi.nlm.nih.gov/#query="
DRUGBANK_SEARCH = "https://go.drugbank.com/unearth/q?searcher=drugs&query="
CLINICAL_TRIALS_SEARCH = "https://clinicaltrials.gov/search?term="
COSMIC_SEARCH = "https://cancer.sanger.ac.uk/cosmic/search?q="
OMIM_SEARCH = "https://www.omim.org/search?search="
KEGG_SEARCH = "https://www.genome.jp/kegg-bin/search_pathway_text?keyword="

def build_external_links(entity_name: str, entity_type: str) -> Dict[str, str]:
    """
    Generates direct external database deep-links based on entity type and name.
    Supports NCBI PubMed, ClinVar, NCBI Gene, UniProt, PubChem, DrugBank,
    ClinicalTrials.gov, COSMIC, OMIM, and KEGG.
    """
    encoded_name = urllib.parse.quote_plus(entity_name.strip())
    links: Dict[str, str] = {
        "PubMed": f"{NCBI_PUBMED_SEARCH}{encoded_name}",
        "MeSH": f"{NCBI_MESH_SEARCH}{encoded_name}"
    }

    ent_type_upper = entity_type.upper()

    if "DISEASE" in ent_type_upper or "CONDITION" in ent_type_upper:
        links["ClinVar"] = f"{NCBI_CLINVAR_SEARCH}{encoded_name}"
        links["ClinicalTrials"] = f"{CLINICAL_TRIALS_SEARCH}{encoded_name}"
        links["OMIM"] = f"{OMIM_SEARCH}{encoded_name}"
        links["KEGG Pathway"] = f"{KEGG_SEARCH}{encoded_name}"

    elif "CHEMICAL" in ent_type_upper or "DRUG" in ent_type_upper:
        links["PubChem"] = f"{PUBCHEM_SEARCH}{encoded_name}"
        links["DrugBank"] = f"{DRUGBANK_SEARCH}{encoded_name}"
        links["ClinicalTrials"] = f"{CLINICAL_TRIALS_SEARCH}{encoded_name}"
        links["DailyMed"] = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={encoded_name}"

    elif "GENE" in ent_type_upper or "PROTEIN" in ent_type_upper:
        links["NCBI Gene"] = f"{NCBI_GENE_SEARCH}{encoded_name}"
        links["UniProt"] = f"{UNIPROT_SEARCH}{encoded_name}"
        links["ClinVar"] = f"{NCBI_CLINVAR_SEARCH}{encoded_name}"
        links["COSMIC"] = f"{COSMIC_SEARCH}{encoded_name}"

    elif "MUTATION" in ent_type_upper or "VARIANT" in ent_type_upper:
        links["ClinVar"] = f"{NCBI_CLINVAR_SEARCH}{encoded_name}"
        links["COSMIC"] = f"{COSMIC_SEARCH}{encoded_name}"
        links["dbSNP"] = f"https://www.ncbi.nlm.nih.gov/snp/?term={encoded_name}"

    elif "PATHWAY" in ent_type_upper or "PROCESS" in ent_type_upper:
        links["KEGG"] = f"{KEGG_SEARCH}{encoded_name}"
        links["Reactome"] = f"https://reactome.org/content/query?q={encoded_name}"

    elif "TRIAL" in ent_type_upper:
        if re.match(r"^NCT\d{8}$", entity_name.strip(), re.IGNORECASE):
            links["ClinicalTrials.gov"] = f"https://clinicaltrials.gov/study/{entity_name.strip()}"
        else:
            links["ClinicalTrials.gov"] = f"{CLINICAL_TRIALS_SEARCH}{encoded_name}"

    else:
        # Generic fallback
        links["ClinVar"] = f"{NCBI_CLINVAR_SEARCH}{encoded_name}"
        links["PubChem"] = f"{PUBCHEM_SEARCH}{encoded_name}"
        links["UniProt"] = f"{UNIPROT_SEARCH}{encoded_name}"

    return links


def fetch_related_papers_pubmed(query_terms: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Queries NCBI E-Utilities (PubMed API) to find real related peer-reviewed papers.
    """
    if not query_terms:
        return []

    # Clean and build query
    cleaned_terms = [t.replace('"', '').strip() for t in query_terms if t.strip()]
    if not cleaned_terms:
        return []

    query = " OR ".join([f'"{t}"[Title/Abstract]' for t in cleaned_terms[:4]])
    encoded_query = urllib.parse.quote_plus(query)

    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmode=json&retmax={max_results}&sort=pub_date"

    try:
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "BioSummarizer/2.0 (mailto:research@biosummarizer.org)"}
        )
        with urllib.request.urlopen(req, timeout=7) as response:
            search_data = json.loads(response.read().decode("utf-8"))

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        # Fetch summaries for PMIDs
        ids_str = ",".join(id_list)
        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"

        req_sum = urllib.request.Request(
            summary_url,
            headers={"User-Agent": "BioSummarizer/2.0 (mailto:research@biosummarizer.org)"}
        )
        with urllib.request.urlopen(req_sum, timeout=7) as sum_response:
            sum_data = json.loads(sum_response.read().decode("utf-8"))

        papers = []
        result_dict = sum_data.get("result", {})
        for pmid in id_list:
            item = result_dict.get(pmid, {})
            if not item or "title" not in item:
                continue

            authors = [a.get("name", "") for a in item.get("authors", [])]
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."

            doi = ""
            for article_id in item.get("articleids", []):
                if article_id.get("idtype") == "doi":
                    doi = article_id.get("value", "")
                    break

            papers.append({
                "pmid": pmid,
                "title": item.get("title", "Untitled Article").rstrip("."),
                "authors": author_str or "Unknown Authors",
                "journal": item.get("source", "Biomedical Journal"),
                "pub_date": item.get("pubdate", "Recent"),
                "doi": doi,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "doi_url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })

        return papers

    except Exception as e:
        print(f"PubMed API search error: {e}")
        return []
