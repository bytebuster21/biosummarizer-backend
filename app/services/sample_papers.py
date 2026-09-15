from typing import List, Dict, Any

SAMPLE_PAPERS: List[Dict[str, Any]] = [
    {
        "id": "sample-1",
        "title": "Pembrolizumab versus Ipilimumab in Advanced Melanoma: A Randomized Phase 3 Trial (KEYNOTE-006)",
        "abstract": """Background: The programmed cell death 1 (PD-1) immune checkpoint inhibitor pembrolizumab has shown substantial antitumor activity in patients with advanced melanoma. We evaluated the overall survival and progression-free survival benefits of pembrolizumab compared with ipilimumab in patients with metastatic melanoma.

Methods: In this randomized, open-label, international phase 3 trial (NCT01866319), 834 patients with advanced metastatic melanoma harboring BRAF V600E or wild-type alleles were enrolled. Patients were randomized 1:1:1 to receive pembrolizumab at a dose of 10 mg per kilogram every 2 weeks, pembrolizumab every 3 weeks, or four doses of ipilimumab (3 mg per kilogram) every 3 weeks. The primary endpoints were progression-free survival and overall survival.

Results: The estimated 6-month progression-free survival rates were 47.3% for pembrolizumab every 2 weeks, 46.4% for pembrolizumab every 3 weeks, and 26.5% for ipilimumab (hazard ratio for disease progression, 0.58; 95% CI, 0.46 to 0.72; p<0.001). The 1-year overall survival rate was 74.1% for pembrolizumab every 2 weeks, 68.4% for pembrolizumab every 3 weeks, and 58.2% for ipilimumab (hazard ratio for death, 0.63; p=0.0005). Treatment-related adverse events of grade 3 to 5 were less frequent in the pembrolizumab groups (13.3% and 10.1%) than in the ipilimumab group (19.9%). Hepatotoxicity and colitis were observed in a minority of patients.

Conclusions: The PD-1 inhibitor pembrolizumab significantly prolonged progression-free survival and overall survival and had less high-grade toxicity than ipilimumab in patients with advanced metastatic melanoma.""",
        "category": "Immuno-Oncology"
    },
    {
        "id": "sample-2",
        "title": "CRISPR-Cas9 Gene Editing for Sickle Cell Disease and Transfusion-Dependent Beta-Thalassemia (CLIMB-121)",
        "abstract": """Background: Sickle cell disease and beta-thalassemia are severe hemoglobinopathies caused by pathogenic mutations in the HBB gene encoding hemoglobin subunit beta. Reactivation of fetal hemoglobin (HbF) synthesis through targeted CRISPR-Cas9 genome editing of the BCL11A erythroid enhancer represents a transformative curative strategy.

Methods: In ongoing phase 1/2 clinical trials (NCT03745287), autologous CD34+ hematopoietic stem and progenitor cells were harvested and electroporated with Cas9 ribonucleoprotein complexes targeting the GATA1 binding site within the BCL11A erythroid enhancer. Patients underwent myeloablative busulfan conditioning prior to single-dose infusion of exagamglogene autotemcel (exa-cel). Primary endpoints included elimination of severe vaso-occlusive crises (VOCs) and transfusion independence for at least 12 consecutive months.

Results: All 31 evaluated patients with sickle cell disease achieved sustained elimination of vaso-occlusive crises (p<0.0001). Median total hemoglobin increased to 12.0 g/dL with pan-cellular HbF expression exceeding 40% of total erythrocytes. In beta-thalassemia patients, 42 of 44 achieved complete transfusion independence. Neutrophil and platelet engraftment occurred at a median of 27 and 32 days respectively. Adverse events were consistent with myeloablative conditioning chemotherapy, with no off-target cutting or clonal hematopoiesis detected.

Conclusions: Exa-cel CRISPR-Cas9 gene editing demonstrated high clinical efficacy, safety, and durable cure of severe vaso-occlusive complications in patients with sickle cell disease and transfusion-dependent beta-thalassemia.""",
        "category": "Gene Therapy & Hematology"
    },
    {
        "id": "sample-3",
        "title": "Personalized Neoantigen mRNA-4157 Vaccine Plus Pembrolizumab in Resected High-Risk Melanoma (KEYNOTE-942)",
        "abstract": """Background: Personalized mRNA cancer vaccines encoding up to 34 patient-specific tumor neoantigens stimulate polyclonal T-cell antitumor immune responses. Combining mRNA-4157 (V940) with PD-1 blockade may prevent immune escape and reduce postoperative recurrence in resected high-risk cutaneous melanoma.

Methods: In this open-label, randomized phase 2b trial (NCT03897881), 157 patients with resected stage IIIB, IIIC, IIID, or IV melanoma with high tumor mutational burden and TP53 or BRAF mutations were randomized (2:1) to receive mRNA-4157 (1 mg intramuscularly every 3 weeks for up to 9 doses) plus pembrolizumab (200 mg intravenously every 3 weeks for up to 18 cycles) or pembrolizumab monotherapy. The primary endpoint was recurrence-free survival (RFS).

Results: At a median follow-up of 24.2 months, the combination of mRNA-4157 plus pembrolizumab significantly reduced the risk of disease recurrence or death by 44% compared with pembrolizumab alone (hazard ratio, 0.56; 95% CI, 0.31 to 0.99; p=0.043). Distant metastasis-free survival was also significantly prolonged (hazard ratio, 0.35; 95% CI, 0.17 to 0.72; p=0.003). High neoantigen-specific CD8+ and CD4+ T-cell activation was induced in peripheral blood. Grade 3 treatment-related adverse events occurred in 25.0% of the combination group versus 18.0% of the monotherapy group, with no grade 4 or 5 toxicities.

Conclusions: Adjuvant treatment with personalized neoantigen mRNA-4157 vaccine combined with pembrolizumab significantly improved recurrence-free survival and distant metastasis-free survival in patients with resected high-risk melanoma.""",
        "category": "Vaccine & Oncology"
    }
]
