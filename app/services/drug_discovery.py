import re
import os
import json
import urllib.parse
from typing import Dict, Any, List, Optional
from app.core.config import settings

# Comprehensive Knowledge Base of Drug Discovery by Disease
DISEASE_DRUG_DISCOVERY_KNOWLEDGE = {
    "melanoma": {
        "disease_name": "Cutaneous & Advanced Melanoma",
        "disease_overview": "Melanoma originates from malignant transformation of melanocytes and is the deadliest form of skin cancer. Driven predominantly by activating mutations in the MAPK pathway (BRAF V600E in ~50%, NRAS in ~20%, NF1 in ~15%), melanoma historically had a dismal prognosis with 5-year survival under 10% prior to 2011. Over the past 15 years, it has become the flagship model for precision oncology and cancer immunotherapy.",
        "timeline": [
            {"year": "1975", "drug": "Dacarbazine", "mechanism": "Alkylating chemotherapy", "milestone": "First FDA-approved agent for metastatic melanoma; standard of care for decades despite <10% response rate."},
            {"year": "2011", "drug": "Ipilimumab (Yervoy)", "mechanism": "Anti-CTLA-4 Monoclonal Antibody", "milestone": "First immune checkpoint inhibitor in oncology; established durable plateaus in long-term survival."},
            {"year": "2011", "drug": "Vemurafenib (Zelboraf)", "mechanism": "Selective BRAF V600E Kinase Inhibitor", "milestone": "First targeted small molecule inhibitor for BRAF-mutant melanoma; rapid tumor regression."},
            {"year": "2014", "drug": "Pembrolizumab (Keytruda)", "mechanism": "Anti-PD-1 Monoclonal Antibody", "milestone": "Landmark PD-1 inhibitor demonstrating superior overall survival and reduced toxicity compared to ipilimumab."},
            {"year": "2014", "drug": "Dabrafenib + Trametinib", "mechanism": "BRAF + MEK Dual Inhibitor Combination", "milestone": "Dual vertical MAPK blockade significantly delays onset of MAPK reactivation resistance."},
            {"year": "2015", "drug": "Nivolumab + Ipilimumab", "mechanism": "Dual Checkpoint Blockade (PD-1 + CTLA-4)", "milestone": "CheckMate 067 trial showed >50% 5-year overall survival in metastatic melanoma."},
            {"year": "2022", "drug": "Relatlimab + Nivolumab (Opdualag)", "mechanism": "Anti-LAG-3 + Anti-PD-1", "milestone": "First approved LAG-3 immune checkpoint inhibitor, establishing a third distinct checkpoint axis."},
            {"year": "2024", "drug": "Lifileucel (Amtagvi)", "mechanism": "Autologous Tumor-Infiltrating Lymphocyte (TIL) Therapy", "milestone": "First FDA-approved cellular therapy for solid tumors in PD-1 refractory melanoma."},
            {"year": "2024+", "drug": "mRNA-4157 (V940) + Pembrolizumab", "mechanism": "Personalized Neoantigen mRNA Vaccine + PD-1 Blockade", "milestone": "KEYNOTE-942 showed 44% reduction in recurrence/death; spearheading personalized cancer vaccines."}
        ],
        "approved_therapies": [
            {"name": "Pembrolizumab", "brand": "Keytruda", "class": "PD-1 Checkpoint Inhibitor", "target": "PD-1 (PDCD1)", "approval": "2014", "moa": "Blocks PD-1 on T cells, preventing interaction with PD-L1/PD-L2 and restoring antitumor immune cytotoxicity."},
            {"name": "Nivolumab", "brand": "Opdivo", "class": "PD-1 Checkpoint Inhibitor", "target": "PD-1 (PDCD1)", "approval": "2014", "moa": "Fully human IgG4 monoclonal antibody disrupting PD-1 mediated inhibitory signaling."},
            {"name": "Ipilimumab", "brand": "Yervoy", "class": "CTLA-4 Inhibitor", "target": "CTLA-4 (CD152)", "approval": "2011", "moa": "Augments T-cell priming in lymph nodes by inhibiting the early immune checkpoint CTLA-4."},
            {"name": "Dabrafenib", "brand": "Tafinlar", "class": "BRAF Kinase Inhibitor", "target": "BRAF V600E/K", "approval": "2013", "moa": "Reversible, ATP-competitive inhibitor targeting active mutant BRAF serine/threonine kinase."},
            {"name": "Trametinib", "brand": "Mekinist", "class": "MEK1/2 Allosteric Inhibitor", "target": "MEK1 / MEK2 (MAP2K1/2)", "approval": "2013", "moa": "Non-competitive allosteric inhibitor of MEK kinases downstream of BRAF."},
            {"name": "Relatlimab", "brand": "Opdualag (combo)", "class": "LAG-3 Checkpoint Inhibitor", "target": "LAG-3 (CD223)", "approval": "2022", "moa": "Binds LAG-3 on exhausted effector T cells to overcome immune tolerance."},
            {"name": "Tebentafusp", "brand": "Kimmtrak", "class": "Bispecific T-Cell Engager (ImmTAC)", "target": "gp100 x CD3", "approval": "2022", "moa": "Directs CD3+ T cells to lyse gp100-expressing uveal melanoma cells."}
        ],
        "pipeline_modalities": [
            {"modality": "Personalized mRNA Neoantigen Vaccines", "example": "mRNA-4157 (V940), BNT122", "stage": "Phase 3", "details": "Patient-specific synthetic mRNA encoding up to 34 neoantigens to trigger tailored polyclonal CD8+ and CD4+ T-cell expansion."},
            {"modality": "Bispecific Antibodies & T-Cell Engagers", "example": "PD-1 x CTLA-4, PD-1 x VEGF", "stage": "Phase 2/3", "details": "Engineered single molecules simultaneously targeting checkpoint exhaustion and tumor microenvironment angiogenesis."},
            {"modality": "Targeted Protein Degraders (PROTACs)", "example": "BRAF / MEK Proteolysis Degraders", "stage": "Phase 1/2", "details": "Recruiting E3 ubiquitin ligases to completely degrade paradoxical mutant BRAF complexes and circumvent resistance."},
            {"modality": "Next-Gen Oncolytic Virotherapies", "example": "RP1 (Vusolimogene oderparepvec)", "stage": "Phase 2", "details": "Genetically attenuated HSV-1 expressing GM-CSF and fusogenic GALV-GP-R- to initiate systemic immunogenic cell death."}
        ],
        "targets_and_pathways": [
            {"target": "BRAF (V600E / V600K)", "pathway": "MAPK / ERK Signaling Cascade", "type": "Oncogenic Driver Kinase"},
            {"target": "PD-1 (PDCD1) / PD-L1 (CD274)", "pathway": "Immune Checkpoint & Effector T-Cell Function", "type": "Immune Evasion Axis"},
            {"target": "CTLA-4 (CD152)", "pathway": "T-Cell Costimulation / Priming", "type": "Immune Checkpoint Receptor"},
            {"target": "LAG-3 (CD223)", "pathway": "T-Cell Exhaustion & Tolerogenic Signaling", "type": "Immune Checkpoint Receptor"},
            {"target": "NRAS (Q61R/K)", "pathway": "GTPase MAPK/PI3K Signaling", "type": "Undruggable Driver (Novel Covalent Inhibitors Emerging)"},
            {"target": "KIT (L576P / K642E)", "pathway": "Receptor Tyrosine Kinase Signaling", "type": "Target in Mucosal / Acral Melanoma"}
        ],
        "resistance_mechanisms": "BRAF inhibitor resistance frequently emerges within 10-14 months via MAPK pathway reactivation (NRAS mutations, BRAF splicing variants, MEK1/2 mutations) or bypass activation through PI3K/AKT/mTOR. In immunotherapy, primary and acquired resistance stem from loss of beta-2-microglobulin (B2M) leading to HLA-I downregulation, JAK1/JAK2 inactivating mutations compromising interferon-gamma signaling, and an immunosuppressive microenvironment driven by VEGF and regulatory T cells."
    },
    "sickle": {
        "disease_name": "Sickle Cell Disease & Beta-Thalassemia",
        "disease_overview": "Sickle Cell Disease (SCD) is a monogenic autosomal recessive hemoglobinopathy caused by a single nucleotide substitution (A to T; Glu6Val) in the HBB gene, producing abnormal sickle hemoglobin (HbS). Under hypoxia, HbS polymerizes, causing erythrocyte sickling, chronic hemolytic anemia, recurrent vaso-occlusive crises (VOCs), multiorgan damage, and premature mortality. Decades of palliative therapy have now transitioned into curative genomic medicine.",
        "timeline": [
            {"year": "1998", "drug": "Hydroxyurea", "mechanism": "Ribonucleotide Reductase Inhibitor", "milestone": "First FDA-approved oral agent to stimulate fetal hemoglobin (HbF) production and reduce vaso-occlusive painful episodes."},
            {"year": "2017", "drug": "L-Glutamine (Endari)", "mechanism": "Antioxidant Amino Acid Therapy", "milestone": "Reduces oxidative stress in sickled erythrocytes, decreasing acute pain crisis hospitalizations."},
            {"year": "2019", "drug": "Crizanlizumab (Adakveo)", "mechanism": "Anti-P-Selectin Monoclonal Antibody", "milestone": "Inhibits P-selectin on activated vascular endothelium, blocking vaso-occlusive multicellular adhesion."},
            {"year": "2019", "drug": "Voxelotor (Oxbryta)", "mechanism": "HbS Polymerization Inhibitor", "milestone": "Allosterically increases hemoglobin oxygen affinity, inhibiting HbS deoxygenated polymer formation."},
            {"year": "2023", "drug": "Exagamglogene Autotemcel (Casgevy)", "mechanism": "CRISPR-Cas9 Gene-Edited Autologous CD34+ HSPCs", "milestone": "Historic first FDA/EMA-approved CRISPR gene editing therapy; targeted editing of BCL11A erythroid enhancer reactivates HbF."},
            {"year": "2023", "drug": "Lovotibeglogene Autotemcel (Lyfgenia)", "mechanism": "Lentiviral Gene Addition Therapy", "milestone": "Adds functional anti-sickling beta-globin (HbA-T87Q) gene into autologous hematopoietic stem cells."}
        ],
        "approved_therapies": [
            {"name": "Exagamglogene autotemcel", "brand": "Casgevy", "class": "CRISPR-Cas9 Cell Therapy", "target": "BCL11A Erythroid Enhancer (GATA1 binding site)", "approval": "2023", "moa": "Cas9 ribonucleoprotein electroporation disrupts BCL11A erythroid-specific expression, derepressing gamma-globin and boosting fetal hemoglobin (HbF) >40%."},
            {"name": "Lovotibeglogene autotemcel", "brand": "Lyfgenia", "class": "Lentiviral Gene Therapy", "target": "HBB Gene Addition", "approval": "2023", "moa": "Transduces CD34+ stem cells with a lentiviral vector encoding HbA-T87Q, an engineered anti-sickling beta-globin variant."},
            {"name": "Voxelotor", "brand": "Oxbryta", "class": "Small Molecule HbS Polymerization Inhibitor", "target": "Sickle Hemoglobin (HbS)", "approval": "2019", "moa": "Reversibly binds alpha-globin chains to stabilize oxygenated non-sickling hemoglobin conformation."},
            {"name": "Crizanlizumab", "brand": "Adakveo", "class": "P-Selectin Inhibitor", "target": "SELP (P-Selectin)", "approval": "2019", "moa": "Humanized IgG2 kappa antibody that binds P-selectin on platelets and endothelial cells to prevent cellular adhesion."},
            {"name": "Hydroxyurea", "brand": "Droxia / Siklos", "class": "HbF Inducing Agent", "target": "Ribonucleotide Reductase / Soluble Guanylyl Cyclase", "approval": "1998", "moa": "Cytostatic agent that induces epigenetic reactivation of gamma-globin genes, increasing protective HbF."}
        ],
        "pipeline_modalities": [
            {"modality": "Base Editing & Prime Editing", "example": "A-to-G Base Editors (Beam Therapeutics)", "stage": "Phase 1/2", "details": "Direct enzymatic correction of the pathogenic HbS point mutation (A>T) without requiring double-stranded DNA breaks."},
            {"modality": "Non-Myeloablative Conditioning", "example": "Antibody-Drug Conjugates targeting CD117 (c-Kit)", "stage": "Phase 1/2", "details": "Replacing toxic high-dose busulfan chemotherapy conditioning with targeted monoclonal anti-CD117 ADCs."},
            {"modality": "Oral Pyruvate Kinase Activators", "example": "Mitapivat (Agios)", "stage": "Phase 3", "details": "Allosterically activates erythrocyte pyruvate kinase (PKR), elevating ATP and reducing 2,3-DPG to increase Hb oxygen affinity."}
        ],
        "targets_and_pathways": [
            {"target": "HBB (Hemoglobin Subunit Beta)", "pathway": "Erythrocyte Oxygen Transport & Hemoglobin Assembly", "type": "Causal Disease Gene"},
            {"target": "BCL11A (Erythroid Enhancer)", "pathway": "Fetal-to-Adult Globin Switching Repression", "type": "Epigenetic Repressor Target"},
            {"target": "P-Selectin (SELP)", "pathway": "Endothelial Adhesion & Microvascular Occlusion", "type": "Cell Adhesion Molecule"},
            {"target": "GATA1 Binding Motif", "pathway": "Erythroid-Specific Transcription Factor Activation", "type": "Genome Editing Site"}
        ],
        "resistance_mechanisms": "In genomic and cellular therapy, therapeutic challenges include incomplete engraftment of gene-edited CD34+ cells, off-target editing risks, the morbidity of myeloablative busulfan conditioning regimens, and limited global access due to extreme manufacturing complexity."
    },
    "lung": {
        "disease_name": "Non-Small Cell Lung Cancer (NSCLC)",
        "disease_overview": "Non-Small Cell Lung Cancer represents ~85% of all lung cancer diagnoses. Over two decades of oncogene-directed drug discovery have transformed NSCLC from an undifferentiated histology treated with toxic platinum doublets into the archetype of biomarker-driven targeted medicine, segmented by EGFR, ALK, ROS1, RET, MET, KRAS G12C, and HER2 alterations.",
        "timeline": [
            {"year": "2003", "drug": "Gefitinib (Iressa)", "mechanism": "1st-Gen EGFR Tyrosine Kinase Inhibitor", "milestone": "First EGFR TKI, revealing sensitivity in Asian non-smokers with activating EGFR mutations."},
            {"year": "2011", "drug": "Crizotinib (Xalkori)", "mechanism": "ALK / ROS1 / MET Multi-Kinase Inhibitor", "milestone": "First companion diagnostic-paired targeted therapy for ALK-rearranged NSCLC."},
            {"year": "2015", "drug": "Pembrolizumab & Nivolumab", "mechanism": "Anti-PD-1 Monoclonal Antibodies", "milestone": "PD-1 blockade established as 1st-line standard of care based on TPS PD-L1 expression."},
            {"year": "2018", "drug": "Osimertinib (Tagrisso)", "mechanism": "3rd-Gen Mutation-Selective EGFR TKI", "milestone": "FLAURA trial proved superior CNS penetration and overcame secondary T790M resistance mutations."},
            {"year": "2021", "drug": "Sotorasib (Lumakras)", "mechanism": "KRAS G12C Covalent Inhibitor", "milestone": "Historic breakthrough drugging the previously 'undruggable' KRAS GTPase switch-II pocket."},
            {"year": "2023", "drug": "Amivantamab + Lazertinib", "mechanism": "EGFR x MET Bispecific + 3rd-Gen TKI", "milestone": "MARIPOSA trial showed progression-free survival superiority over osimertinib monotherapy."}
        ],
        "approved_therapies": [
            {"name": "Osimertinib", "brand": "Tagrisso", "class": "3rd-Gen EGFR TKI", "target": "EGFR Exon 19 del / L858R / T790M", "approval": "2015", "moa": "Irreversible covalent inhibitor targeting ATP binding site of mutant EGFR while sparing wild-type."},
            {"name": "Alectinib", "brand": "Alecensa", "class": "2nd-Gen ALK Inhibitor", "target": "ALK Fusion Kinases", "approval": "2015", "moa": "CNS-penetrant potent inhibitor of EML4-ALK fusion kinase."},
            {"name": "Sotorasib", "brand": "Lumakras", "class": "KRAS G12C Covalent Inhibitor", "target": "KRAS G12C", "approval": "2021", "moa": "Covalently binds inactive GDP-bound KRAS G12C in the switch-II pocket, locking it in the off state."},
            {"name": "Trastuzumab deruxtecan", "brand": "Enhertu", "class": "Antibody-Drug Conjugate (ADC)", "target": "HER2 (ERBB2)", "approval": "2022", "moa": "Anti-HER2 antibody delivering topoisomerase I inhibitor DXd payload via cleavable tetrapeptide linker."}
        ],
        "pipeline_modalities": [
            {"modality": "Pan-KRAS & KRAS G12D Inhibitors", "example": "RMC-6236, MRTX1133", "stage": "Phase 1/2", "details": "Multi-KRAS inhibitors that overcome resistance to single G12C alleles across broader lung and pancreatic cancers."},
            {"modality": "4th-Generation EGFR TKIs", "example": "BLU-945, BBT-176", "stage": "Phase 1/2", "details": "Overcoming tertiary EGFR C797S resistance mutations emerging after frontline osimertinib."},
            {"modality": "TROP-2 & B7-H3 Targeted ADCs", "example": "Dato-DXd, Ifinatamab deruxtecan", "stage": "Phase 3", "details": "High-potency cytotoxic delivery targeting prevalent cell surface antigens in non-oncogene-addicted NSCLC."}
        ],
        "targets_and_pathways": [
            {"target": "EGFR (Exon 19 del / L858R)", "pathway": "Receptor Tyrosine Kinase / MAPK / PI3K", "type": "Oncogenic Driver Kinase"},
            {"target": "KRAS (G12C / G12D / G12V)", "pathway": "RAS GTPase Signaling Cascade", "type": "Oncogenic GTPase Driver"},
            {"target": "ALK / ROS1 / RET", "pathway": "Chromosomal Rearrangement / Kinase Fusions", "type": "Receptor Tyrosine Kinase Fusions"},
            {"target": "MET (Exon 14 Skipping / Amplification)", "pathway": "HGF / MET Receptor Axis", "type": "Kinase Driver & Resistance Node"},
            {"target": "PD-L1 (CD274)", "pathway": "Tumor Immune Evasion", "type": "Biomarker & Immune Checkpoint"}
        ],
        "resistance_mechanisms": "In targeted therapies, on-target resistance arises through tertiary gatekeeper mutations (EGFR C797S, ALK G1202R). Off-target resistance includes MET amplification, HER2 amplification, histological small-cell lung cancer (SCLC) transformation, and epithelial-to-mesenchymal transition (EMT)."
    }
}


def _detect_paper_diseases_and_targets(paper_text: str) -> Dict[str, Any]:
    """Scans paper text to identify the primary target disease and molecular mechanisms."""
    text_lower = paper_text.lower()

    scores = {
        "melanoma": text_lower.count("melanoma") * 4 + text_lower.count("skin cancer") * 3 + text_lower.count("braf") * 2,
        "sickle": text_lower.count("sickle") * 4 + text_lower.count("thalassemia") * 4 + text_lower.count("hbb") * 3 + text_lower.count("vaso-occlusive") * 3,
        "lung": text_lower.count("lung cancer") * 4 + text_lower.count("nsclc") * 4 + text_lower.count("egfr") * 2 + text_lower.count("osimertinib") * 3,
    }

    # Detect generic mention of other diseases
    generic_disease_patterns = [
        "pancreatic cancer", "breast cancer", "colorectal cancer", "glioblastoma",
        "leukemia", "lymphoma", "prostate cancer", "ovarian cancer", "multiple myeloma",
        "alzheimer", "parkinson", "rheumatoid arthritis", "cystic fibrosis"
    ]

    detected_generic = []
    for gd in generic_disease_patterns:
        if gd in text_lower:
            detected_generic.append(gd.title())

    best_match = max(scores, key=scores.get)
    if scores[best_match] > 2:
        primary_key = best_match
    elif detected_generic:
        primary_key = detected_generic[0].lower().split()[0]
    else:
        primary_key = "melanoma" # default high-impact model

    return {
        "primary_key": primary_key,
        "detected_generic": detected_generic
    }


def _call_gemini_drug_discovery(disease_query: str, paper_text: str) -> Optional[Dict[str, Any]]:
    """Synthesizes dynamic, publication-grade drug discovery landscape using Gemini 3.8 Flash."""
    api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""You are BioLens AI, a principal pharmacology and translational drug discovery expert.
The scientific research paper discusses therapeutic developments for: "{disease_query}".

PAPER CONTEXT:
{paper_text[:8000]}

Generate an exhaustive, publication-grade Drug Discovery Landscape Report for "{disease_query}".
Respond strictly with valid JSON matching this schema:
{{
  "disease_name": "Full Clinical Name of Disease",
  "disease_overview": "Comprehensive 2-paragraph analysis of pathophysiology, genetic landscape, and why drug discovery has been historically challenging.",
  "timeline": [
    {{"year": "YYYY", "drug": "Drug Name", "mechanism": "Mechanism of Action", "milestone": "Historical breakthrough description."}}
  ],
  "approved_therapies": [
    {{"name": "Drug Name", "brand": "Brand Name", "class": "Drug Class", "target": "Molecular Target", "approval": "Approval Year", "moa": "Detailed biological mechanism of action."}}
  ],
  "pipeline_modalities": [
    {{"modality": "Therapeutic Modality (e.g. CRISPR, ADCs, Bispecifics, mRNA Vaccines)", "example": "Investigational Agent(s)", "stage": "Clinical Trial Phase", "details": "Mechanism and target details."}}
  ],
  "targets_and_pathways": [
    {{"target": "Target Name", "pathway": "Biological Pathway", "type": "Target Class"}}
  ],
  "resistance_mechanisms": "Detailed multi-paragraph breakdown of pharmacological and biological resistance mechanisms observed in clinical practice.",
  "external_registries": {{
    "ClinicalTrials": "URL query",
    "DrugBank": "URL query",
    "PubChem": "URL query",
    "PubMed": "URL query"
  }}
}}
"""

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )

        raw = response.text.strip() if response.text else ""
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        return json.loads(raw)
    except Exception as e:
        print(f"Gemini drug discovery notice: {e}")
        return None


def get_drug_discovery_landscape(paper_text: str, paper_title: str = "") -> Dict[str, Any]:
    """
    Synthesizes and retrieves the complete drug discovery landscape, approved therapeutics,
    historical milestone timeline, and investigational pipeline related to the disease in the paper.
    """
    detection = _detect_paper_diseases_and_targets(f"{paper_title} {paper_text}")
    primary_key = detection["primary_key"]

    # Check curated knowledge base first
    curated = None
    for k, v in DISEASE_DRUG_DISCOVERY_KNOWLEDGE.items():
        if k in primary_key:
            curated = dict(v)
            break

    # If Gemini is configured and we need custom / enriched data
    gemini_data = None
    if not curated or getattr(settings, "GEMINI_API_KEY", ""):
        disease_name = curated["disease_name"] if curated else (detection["detected_generic"][0] if detection["detected_generic"] else "Melanoma")
        gemini_data = _call_gemini_drug_discovery(disease_name, paper_text)

    landscape = gemini_data if gemini_data else (curated if curated else DISEASE_DRUG_DISCOVERY_KNOWLEDGE["melanoma"])

    # Ensure search links are attached
    encoded_disease = urllib.parse.quote_plus(landscape.get("disease_name", "Melanoma"))
    landscape["external_registries"] = {
        "ClinicalTrials": f"https://clinicaltrials.gov/search?term={encoded_disease}&aggFilters=status:rec",
        "DrugBank": f"https://go.drugbank.com/unearth/q?searcher=drugs&query={encoded_disease}",
        "PubChem": f"https://pubchem.ncbi.nlm.nih.gov/#query={encoded_disease}%20inhibitor",
        "PubMed": f"https://pubmed.ncbi.nlm.nih.gov/?term={encoded_disease}+drug+discovery+therapeutic"
    }

    return landscape
