"""Generate synthetic job applicant resumes for functional tests of the careers site.

All people, companies and contact details are fictional. Run from the repository root:

    pip install fpdf2
    python samples/applicants/generate.py

The PDFs are written next to this script. Apply with them through the careers site; see README.md for the job each
one is meant for and the outcome to expect. The three older resumes in samples/resumes complement this set.
"""

from pathlib import Path

from fpdf import FPDF

OUTPUT = Path(__file__).resolve().parent

EN = {"summary": "Summary", "experience": "Experience", "skills": "Skills", "education": "Education", "details": "Details"}
DE = {"summary": "Profil", "experience": "Berufserfahrung", "skills": "Kenntnisse", "education": "Ausbildung", "details": "Weitere Angaben"}

APPLICANTS = [
    dict(slug="amara-osei-product-designer", name="Amara Osei", head="Product Designer | London, UK | amara.osei@example.com",
         summary="Product designer with 5 years of experience in B2B SaaS. Strong in interface craft and design systems; research is mostly done together with a dedicated researcher.",
         experience=["Product Designer, Ledgerly (B2B finance SaaS), 2021 - present: Redesigned invoicing and reporting flows for 3,000 business customers; contributed 40 components to the shared design system.",
                     "UI Designer, Pixelforge Agency, 2019 - 2021: Web and mobile interfaces for SMB clients."],
         skills="Figma, prototyping, design systems, usability testing (as participant in studies), stakeholder workshops. No AI product experience yet.",
         education="BA Graphic Design, Falmouth University.",
         details=["Languages: English", "Availability: 2 months notice"]),
    dict(slug="priyanka-desai-senior-frontend-engineer", name="Priyanka Desai", head="Senior Frontend Engineer | Berlin, DE | priyanka.desai@example.com",
         summary="Frontend engineer with 9 years of experience building accessible B2B web apps in React and TypeScript. Maintains a design system used by 6 teams.",
         experience=["Senior Frontend Engineer, Kestrel Cloud, 2020 - present: Led the migration to a token-based component library; raised Lighthouse accessibility from 74 to 98 and fixed 120 WCAG 2.2 issues. Built a streaming chat UI for an AI assistant.",
                     "Frontend Engineer, Altmark Systems, 2016 - 2020: Dashboards with D3 and React; introduced Playwright end-to-end tests that cut regressions by 40%."],
         skills="React, TypeScript, Next.js, accessibility (WCAG 2.2), Storybook, Playwright, performance, streaming UIs.",
         education="BSc Computer Science, TU Berlin.",
         details=["Languages: English, German, Hindi", "Availability: 2 months notice"]),
    dict(slug="diego-alvarez-backend-developer", name="Diego Alvarez", head="Backend Developer | Valencia, ES | diego.alvarez@example.com",
         summary="Backend developer with 6 years in Java and Spring, building payment and billing APIs. Little frontend work.",
         experience=["Backend Developer, Turia Payments, 2020 - present: REST APIs and batch jobs for card settlement; reduced settlement time from 6 hours to 40 minutes.",
                     "Junior Developer, Levante IT, 2018 - 2020: Maintenance of an internal ERP."],
         skills="Java, Spring Boot, PostgreSQL, Kafka, Docker. Basic HTML and CSS, no React or TypeScript.",
         education="BSc Software Engineering, Universitat de Valencia.",
         details=["Languages: Spanish, English", "Availability: 1 month notice"]),
    dict(slug="sven-larsen-ml-engineer-rag", name="Sven Larsen", head="Machine Learning Engineer | Madrid, ES | sven.larsen@example.com",
         summary="ML engineer with 7 years of experience, the last 3 building retrieval-augmented generation systems and the evaluation suites that keep them honest.",
         experience=["Senior ML Engineer, Brisa Search, 2021 - present: Built hybrid search with semantic reranking on Azure AI Search for 2M documents; created a groundedness and citation regression suite with 400 test questions that runs on every release.",
                     "ML Engineer, Nordlicht Analytics, 2018 - 2021: Classification and ranking models in Python, deployed with MLflow."],
         skills="Python, Azure AI Search, Azure AI Foundry, embeddings, LLM evaluation, prompt engineering, MLOps, Docker.",
         education="MSc Artificial Intelligence, Universidad Politecnica de Madrid.",
         details=["Languages: English, Spanish, Swedish", "Availability: 1 month notice"]),
    dict(slug="aditi-rao-data-scientist", name="Aditi Rao", head="Data Scientist | Madrid, ES | aditi.rao@example.com",
         summary="Data scientist with 4 years of experience in forecasting and experimentation. Has started to explore LLM applications in side projects.",
         experience=["Data Scientist, Mercado Logistics, 2022 - present: Demand forecasting models and A/B tests; a side project builds a document Q&A prototype with embeddings and a vector database.",
                     "Analyst, Cobalt Retail, 2020 - 2022: Reporting and SQL analysis."],
         skills="Python, pandas, scikit-learn, SQL, basic embeddings and vector search. No production LLM or evaluation experience.",
         education="MSc Statistics, Universidad Carlos III de Madrid.",
         details=["Languages: English, Hindi, Spanish (B2)", "Availability: 2 months notice"]),
    dict(slug="anika-schmidt-customer-success-dach", labels=DE, name="Anika Schmidt", head="Customer Success Managerin | Hamburg, DE | anika.schmidt@example.com",
         summary="Customer Success Managerin mit 7 Jahren Erfahrung in B2B-Software. Betreut Enterprise-Kunden in Deutschland, Oesterreich und der Schweiz.",
         experience=["Senior Customer Success Managerin, Nordlicht Software, 2020 - heute: Verantwortlich fuer 38 Enterprise-Kunden (DACH); Verlaengerungsquote von 88 auf 95 Prozent gesteigert; Onboarding-Zeit um ein Drittel verkuerzt.",
                     "Customer Success Managerin, Elbe Systems, 2017 - 2020: Onboarding und Reporting fuer Mittelstandskunden."],
         skills="Onboarding, Verlaengerungen, Reporting, Salesforce, Zendesk, Praesentationen auf Deutsch und Englisch.",
         education="BA Betriebswirtschaft, Universitaet Hamburg.",
         details=["Sprachen: Deutsch (Muttersprache), Englisch (verhandlungssicher)", "Verfuegbarkeit: 3 Monate Kuendigungsfrist"]),
    dict(slug="ethan-walker-customer-success-manager", name="Ethan Walker", head="Customer Success Manager | Bristol, UK | ethan.walker@example.com",
         summary="Customer success manager with 6 years in B2B SaaS, managing UK and Irish accounts. Strong on renewals and reporting.",
         experience=["Customer Success Manager, Avonside Software, 2020 - present: 45 accounts in the UK and Ireland; net revenue retention of 112%.",
                     "Support Specialist, Severn Cloud, 2018 - 2020: Tier 2 support."],
         skills="Renewals, onboarding, reporting, HubSpot, Gainsight. English only.",
         education="BA Business Management, University of Bristol.",
         details=["Languages: English", "Availability: 1 month notice"]),
    dict(slug="sophie-laurent-ux-researcher", name="Sophie Laurent", head="UX Researcher | Leeds, UK | sophie.laurent@example.com",
         summary="UX researcher with 5 years of experience in B2B tools, including 2 years researching recruiting and HR workflows and AI-assisted features.",
         experience=["UX Researcher, Talentbridge (HR tech), 2022 - present: Ran 45 interviews and 6 diary studies with recruiters; built a research repository; evaluated an AI shortlist feature and showed that explanations raised trust.",
                     "Research Associate, University of Leeds, 2020 - 2022: Usability studies for accessible software."],
         skills="Interviews, diary studies, survey design, usability testing, Dovetail, research ops, evaluating AI features.",
         education="MSc Human-Computer Interaction, University of Leeds.",
         details=["Languages: English, French", "Availability: 1 month notice"]),
]


def build(candidate: dict) -> None:
    labels = candidate.get("labels", EN)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, candidate["name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, candidate["head"], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    def section(title: str, lines: list[str]) -> None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in lines:
            pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        pdf.ln(2)

    section(labels["summary"], [candidate["summary"]])
    section(labels["experience"], candidate["experience"])
    section(labels["skills"], [candidate["skills"]])
    section(labels["education"], [candidate["education"]])
    section(labels["details"], candidate["details"])
    pdf.output(str(OUTPUT / f"{candidate['slug']}.pdf"))


def main() -> None:
    for candidate in APPLICANTS:
        build(candidate)
    print(f"Wrote {len(APPLICANTS)} resumes to {OUTPUT}")


if __name__ == "__main__":
    main()
