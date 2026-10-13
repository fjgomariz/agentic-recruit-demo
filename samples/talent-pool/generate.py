"""Generate the synthetic talent pool resumes for the Foundry IQ demo.

All people, companies, and contact details are fictional. Run from the repository root:

    pip install fpdf2
    python samples/talent-pool/generate.py

The PDFs are written next to this script and are what the Foundry IQ knowledge source indexes.
The pool deliberately mixes roles, synonyms (UX researcher vs user research lead), languages,
typos, and salary expectations so that agentic retrieval has something interesting to plan over.
"""

from pathlib import Path

from fpdf import FPDF

OUTPUT = Path(__file__).resolve().parent

EN = {"summary": "Summary", "experience": "Experience", "skills": "Skills", "education": "Education", "details": "Details"}
DE = {"summary": "Profil", "experience": "Berufserfahrung", "skills": "Kenntnisse", "education": "Ausbildung", "details": "Weitere Angaben"}
ES = {"summary": "Perfil", "experience": "Experiencia", "skills": "Habilidades", "education": "Formacion", "details": "Otros datos"}

CANDIDATES = [
    # Design and research: closest to the Senior Product Designer job.
    dict(slug="nadia-haddad-ux-research-lead", name="Nadia Haddad", head="User Research Lead | London, UK | nadia.haddad@example.com",
         summary="UX researcher with 8 years in B2B SaaS. Built and led a team of four researchers for workflow and analytics products, including two AI-assisted features.",
         experience=["Research Lead, Brightlane (HR tech SaaS), 2020 - present: Led discovery research and usability studies for recruiter tools; introduced a research repository used by 5 squads. Co-designed prototypes with product designers.",
                     "Senior UX Researcher, Northwind Analytics, 2017 - 2020: Ran interviews, diary studies and surveys with enterprise admins; influenced the reporting redesign."],
         skills="User research, usability testing, interviews, survey design, research ops, Figma (prototyping), stakeholder workshops, AI feature evaluation.",
         education="MSc Human-Computer Interaction, University College London.",
         details=["Languages: English, Arabic", "Availability: 2 months notice", "Salary expectation: GBP 78,000"]),
    dict(slug="jonas-weber-senior-ux-designer-de", labels=DE, name="Jonas Weber", head="Senior UX Designer | Berlin, DE | jonas.weber@example.com",
         summary="Senior UX Designer mit 9 Jahren Erfahrung in B2B-Software, davon 3 Jahre fuer KI-gestuetzte Planungstools. Staerken: Design-Systeme, Nutzerforschung und Zusammenarbeit mit Produkt und Entwicklung.",
         experience=["Senior UX Designer, Kestrel Logistics Software, 2021 - heute: Verantwortlich fuer das Design eines KI-gestuetzten Routenplaners vom Konzept bis zum Launch. Leitung von 25 Usability-Tests. Aufbau eines Design-Systems mit 90 Komponenten.",
                     "UX Designer, Altmark Systems, 2017 - 2021: Redesign eines Verwaltungsportals fuer Unternehmenskunden."],
         skills="Figma, Prototyping, Design-Systeme, Nutzerforschung, Barrierefreiheit (WCAG), Workshops, Mentoring.",
         education="BA Kommunikationsdesign, Universitaet der Kuenste Berlin.",
         details=["Sprachen: Deutsch (Muttersprache), Englisch (fliessend)", "Verfuegbarkeit: 3 Monate Kuendigungsfrist", "Gehaltsvorstellung: EUR 82.000"]),
    dict(slug="sofia-marin-disenadora-producto-es", labels=ES, name="Sofia Marin", head="Disenadora de producto senior | Madrid, ES | sofia.marin@example.com",
         summary="Disenadora de producto con 7 anos de experiencia en software B2B para finanzas. Experiencia liderando investigacion con usuarios y sistemas de diseno.",
         experience=["Senior Product Designer, Cuenta Clara (fintech B2B), 2020 - actualidad: Lidere el rediseno del panel de tesoreria para empresas; 30 entrevistas con clientes; sistema de diseno compartido por 4 equipos.",
                     "Product Designer, Ibero Pagos, 2017 - 2020: Disene flujos de conciliacion y facturacion."],
         skills="Figma, investigacion con usuarios, sistemas de diseno, prototipado, accesibilidad, colaboracion con producto e ingenieria.",
         education="Grado en Diseno, Universidad Politecnica de Madrid.",
         details=["Idiomas: espanol (nativo), ingles (C1)", "Disponibilidad: 1 mes de preaviso", "Expectativa salarial: EUR 62.000"]),
    dict(slug="priya-nair-product-designer", name="Priya Nair", head="Product Designer | London, UK | priya.nair@example.com",
         summary="Product designer with 4 years of experience on consumer mobile apps (fitness and food delivery).",
         experience=["Product Designer, FitLoop, 2022 - present: Designed onboarding and workout flows for an app with 2M users. Ran 15 usability sessions.",
                     "Junior Product Designer, Snackly, 2020 - 2022: Designed ordering screens and maintained the component library."],
         skills="Figma, prototyping, usability testing, mobile design. No B2B or leadership experience.",
         education="BA Graphic Design, Goldsmiths.",
         details=["Languages: English", "Availability: 1 month notice", "Salary expectation: GBP 52,000"]),
    dict(slug="daniel-okafor-ui-designer", name="Daniel Okafor", head="UI Designer | Manchester, UK | daniel.okafor@example.com",
         summary="UI designer with 7 years crafting interfaces for B2B software products.",
         experience=["Senior UI Designer, Contoso Billing (B2B SaaS), 2019 - present: High-fidelity screens and icon sets for invoicing and reporting; maintained the visual style guide.",
                     "UI Designer, Fabrikam CRM, 2017 - 2019: Applied branding to dashboards and email templates."],
         skills="Figma, Sketch, visual design, style guides. Did not run user research; no AI tooling experience.",
         education="BA Digital Media, Manchester Metropolitan University.",
         details=["Languages: English", "Availability: 2 months notice", "Salary expectation: GBP 66,000"]),
    dict(slug="elena-petrova-design-systems-lead", name="Elena Petrova", head="Design Systems Lead | London, UK | elena.petrova@example.com",
         summary="Design systems lead with 11 years in enterprise software; built systems adopted by 12 product teams and mentored 8 designers.",
         experience=["Design Systems Lead, Meridian Cloud, 2019 - present: Owns a 200-component system with accessibility baked in (WCAG 2.2); partners with engineering on a token pipeline.",
                     "Senior Product Designer, Orbit Analytics, 2014 - 2019: Led design for a B2B data exploration product; ran research with analysts."],
         skills="Design systems, Figma variables, accessibility, governance, mentoring, B2B product design, user research.",
         education="MA Interaction Design, Royal College of Art.",
         details=["Languages: English, Russian", "Availability: 3 months notice", "Salary expectation: GBP 92,000"]),
    dict(slug="marcus-lindqvist-service-designer", name="Marcus Lindqvist", head="Service Designer | Stockholm, SE | marcus.lindqvist@example.com",
         summary="Service designer with 8 years in the public sector and B2B consulting. Strong facilitator of co-design workshops.",
         experience=["Service Designer, Nordlys Consulting, 2019 - present: Mapped end-to-end journeys for HR and onboarding services; facilitated 60+ workshops.",
                     "Interaction Designer, Swedish Tax Digital, 2016 - 2019: Redesigned citizen-facing forms."],
         skills="Service blueprints, journey mapping, workshop facilitation, prototyping in Figma, research synthesis.",
         education="MSc Design, KTH Royal Institute of Technology.",
         details=["Languages: Swedish, English", "Availability: 1 month notice", "Salary expectation: EUR 70,000"]),
    dict(slug="aisha-khan-interaction-designer", name="Aisha Khan", head="Interaction Designer | London, UK | aisha.khan@example.com",
         summary="Intraction designer with 5 years in HR tech, focused on conversatoinal interfaces and recruiter workflows. Passionate about usabilty and acessibility.",
         experience=["Interaction Designer, Talentwave (HR tech), 2021 - present: Designed a chatbot-assisted candidate screening flow; ran reasearch sessions with recruiters.",
                     "UX Designer, Pixelhouse, 2019 - 2021: Delivered web apps for SMB clients."],
         skills="Figam, prototyping, conversational UI, usabilty testing, user flows, design critiques.",
         education="BSc Psychology, University of Bristol; UX bootcamp.",
         details=["Languages: English, Urdu", "Availability: immediate", "Salary expectation: GBP 60,000"]),
    dict(slug="tomas-ribeiro-product-designer", name="Tomas Ribeiro", head="Product Designer | Lisbon, PT | tomas.ribeiro@example.com",
         summary="Product designer with 3 years in fintech startups; fast prototyper who likes working directly with engineers.",
         experience=["Product Designer, Lusopay, 2023 - present: Designed merchant onboarding and payout screens; shipped 20+ features.",
                     "Junior Designer, Atlantic Labs, 2022 - 2023: Landing pages and marketing site."],
         skills="Figma, prototyping, front-end basics (HTML, CSS), analytics.",
         education="BA Multimedia Design, University of Lisbon.",
         details=["Languages: Portuguese, English", "Availability: immediate", "Salary expectation: EUR 45,000"]),
    dict(slug="hannah-cole-head-of-design", name="Hannah Cole", head="Head of Design | London, UK | hannah.cole@example.com",
         summary="Design leader with 14 years of experience; managed teams of up to 12 across B2B products, including generative AI assistants for knowledge workers.",
         experience=["Head of Design, Parley AI, 2021 - present: Built the design function from 2 to 11; shipped an AI writing assistant used by 40k teams; sets design strategy and hiring standards.",
                     "Design Manager, Tallis Software, 2016 - 2021: Led product design for collaboration tools."],
         skills="Design leadership, hiring, strategy, AI product design, research practice, stakeholder management.",
         education="BA Product Design, Loughborough University.",
         details=["Languages: English, French", "Availability: 3 months notice", "Salary expectation: GBP 125,000"]),
    dict(slug="yuki-tanaka-ai-product-designer", name="Yuki Tanaka", head="Product Designer, AI products | London, UK | yuki.tanaka@example.com",
         summary="Product designer with 6 years of experience, the last 3 designing copilot-style experiences for enterprise software, including trust, citations and human-in-the-loop review.",
         experience=["Product Designer, Helio Systems, 2021 - present: Designed an enterprise copilot with source citations and approval flows; ran 30 usability sessions with analysts.",
                     "UX Designer, Kansai Digital, 2018 - 2021: Internal tools for manufacturing customers."],
         skills="Figma, prototyping, AI interaction patterns, explainability, user research, design systems.",
         education="BEng Human Interface, Kyoto Institute of Technology.",
         details=["Languages: Japanese, English", "Availability: 2 months notice", "Salary expectation: GBP 74,000"]),
    dict(slug="oliver-grant-ux-writer", name="Oliver Grant", head="UX Writer / Content Designer | London, UK | oliver.grant@example.com",
         summary="Content designer with 6 years writing interface copy and design guidelines for B2B products.",
         experience=["Content Designer, Meridian Cloud, 2020 - present: Voice and tone guide, error message patterns, microcopy for onboarding.",
                     "Technical Writer, Orbit Analytics, 2018 - 2020: Product documentation."],
         skills="UX writing, content strategy, information architecture, localization, Figma comments.",
         education="BA English Literature, University of Leeds.",
         details=["Languages: English", "Availability: 1 month notice", "Salary expectation: GBP 58,000"]),
    dict(slug="lucia-ferrari-brand-motion-designer", name="Lucia Ferrari", head="Brand and Motion Designer | Milan, IT | lucia.ferrari@example.com",
         summary="Brand designer with 5 years of experience in campaigns and motion graphics for consumer brands.",
         experience=["Brand Designer, Studio Verde, 2021 - present: Identity systems, social campaigns and motion templates.",
                     "Junior Designer, Tessuto, 2019 - 2021: Packaging and print."],
         skills="Adobe Creative Suite, After Effects, illustration, typography. No product design experience.",
         education="BA Visual Communication, Politecnico di Milano.",
         details=["Languages: Italian, English", "Availability: 1 month notice", "Salary expectation: EUR 40,000"]),
    dict(slug="ben-ashworth-accessibility-specialist", name="Ben Ashworth", head="Accessibility Specialist and Designer | Bristol, UK | ben.ashworth@example.com",
         summary="Accessibility-focused designer-developer with 9 years of experience; audits and fixes B2B web apps against WCAG 2.2 and trains design teams.",
         experience=["Accessibility Lead, Cobalt Health Software, 2019 - present: Audits, assistive technology testing, component guidance; reduced critical issues by 80%.",
                     "UI Developer, Greywell, 2015 - 2019: Accessible front ends in React."],
         skills="WCAG 2.2, screen readers, React, Figma annotations, inclusive design, training.",
         education="BSc Computer Science, University of Bath.",
         details=["Languages: English, British Sign Language", "Availability: 2 months notice", "Salary expectation: GBP 72,000"]),
    # Engineering and data: noise and future roles.
    dict(slug="chen-wei-senior-frontend-engineer", name="Chen Wei", head="Senior Frontend Engineer | London, UK | chen.wei@example.com",
         summary="Frontend engineer with 8 years building B2B dashboards in React and TypeScript. Works closely with designers and maintains a component library.",
         experience=["Senior Frontend Engineer, Meridian Cloud, 2019 - present: Led migration to a design-token based component library; improved Lighthouse accessibility score from 72 to 96.",
                     "Frontend Engineer, Orbit Analytics, 2016 - 2019: Data visualization dashboards."],
         skills="React, TypeScript, CSS, accessibility, Storybook, testing, performance.",
         education="BSc Computer Science, Imperial College London.",
         details=["Languages: English, Mandarin", "Availability: 2 months notice", "Salary expectation: GBP 88,000"]),
    dict(slug="rosa-delgado-design-engineer", name="Rosa Delgado", head="Design Engineer | Barcelona, ES | rosa.delgado@example.com",
         summary="Design engineer bridging design and code for 6 years: prototypes in code, motion, and design systems for B2B apps.",
         experience=["Design Engineer, Lumen Software, 2021 - present: Built an interactive prototype library; collaborates daily with product designers.",
                     "Frontend Developer, Costa Digital, 2018 - 2021: Marketing sites and web apps."],
         skills="React, Framer, CSS, Figma, design tokens, accessibility.",
         education="BSc Multimedia Engineering, Universitat Pompeu Fabra.",
         details=["Languages: Spanish, Catalan, English", "Availability: 1 month notice", "Salary expectation: EUR 58,000"]),
    dict(slug="alex-novak-backend-engineer", name="Alex Novak", head="Backend Engineer | Prague, CZ | alex.novak@example.com",
         summary="Backend engineer with 7 years in Python and Go; designs APIs and event-driven services.",
         experience=["Backend Engineer, Datagrid, 2020 - present: Built ingestion pipelines processing 2B events per day.",
                     "Software Engineer, Praha Tech, 2017 - 2020: REST APIs for logistics."],
         skills="Python, Go, PostgreSQL, Kafka, Docker, Azure.",
         education="MSc Informatics, Czech Technical University.",
         details=["Languages: Czech, English", "Availability: 1 month notice", "Salary expectation: EUR 78,000"]),
    dict(slug="grace-adeyemi-data-scientist", name="Grace Adeyemi", head="Data Scientist | London, UK | grace.adeyemi@example.com",
         summary="Data scientist with 5 years of experience in churn prediction and experimentation for subscription products.",
         experience=["Data Scientist, Streamly, 2021 - present: Built churn models; designed A/B tests with product and design teams.",
                     "Analyst, Metric Labs, 2019 - 2021: Dashboards and reporting."],
         skills="Python, SQL, statistics, experimentation, scikit-learn.",
         education="MSc Statistics, University of Warwick.",
         details=["Languages: English, Yoruba", "Availability: 2 months notice", "Salary expectation: GBP 70,000"]),
    dict(slug="mateo-silva-ml-engineer-rag", name="Mateo Silva", head="Machine Learning Engineer | Madrid, ES | mateo.silva@example.com",
         summary="ML engineer with 6 years of experience; recently focused on retrieval-augmented generation and agent evaluation for enterprise search.",
         experience=["ML Engineer, Sapiens Search, 2021 - present: Built RAG pipelines with hybrid search and semantic reranking; created evaluation suites for answer grounding.",
                     "Data Engineer, Iberdatos, 2018 - 2021: Batch and streaming pipelines."],
         skills="Python, Azure AI Search, embeddings, LLM evaluation, prompt engineering, MLOps.",
         education="MSc Artificial Intelligence, Universidad Complutense de Madrid.",
         details=["Languages: Spanish, English", "Availability: 1 month notice", "Salary expectation: EUR 76,000"]),
    dict(slug="liam-oconnor-devops-engineer", name="Liam O'Connor", head="DevOps Engineer | Dublin, IE | liam.oconnor@example.com",
         summary="DevOps engineer with 8 years in cloud infrastructure, CI/CD, and Kubernetes.",
         experience=["Senior DevOps Engineer, Emerald Pay, 2019 - present: Terraform, GitHub Actions, AKS; cut deployment time from 40 to 8 minutes.",
                     "Systems Engineer, Liffey Networks, 2016 - 2019: Linux operations."],
         skills="Terraform, Bicep, Kubernetes, GitHub Actions, observability.",
         education="BEng Electronic Engineering, Trinity College Dublin.",
         details=["Languages: English", "Availability: 3 months notice", "Salary expectation: EUR 85,000"]),
    # Product, go-to-market, and people.
    dict(slug="sara-lindgren-product-manager", name="Sara Lindgren", head="Senior Product Manager | London, UK | sara.lindgren@example.com",
         summary="Product manager with 8 years in B2B SaaS; owns roadmaps for workflow and analytics products and works closely with design and research.",
         experience=["Senior Product Manager, Brightlane (HR tech SaaS), 2020 - present: Owns the candidate screening product; launched an AI shortlist feature adopted by 60% of customers.",
                     "Product Manager, Northwind Analytics, 2016 - 2020: Reporting and dashboards."],
         skills="Roadmapping, discovery, experimentation, stakeholder management, SQL.",
         education="MBA, London Business School.",
         details=["Languages: English, Swedish", "Availability: 3 months notice", "Salary expectation: GBP 98,000"]),
    dict(slug="david-mensah-technical-program-manager", name="David Mensah", head="Technical Program Manager | Manchester, UK | david.mensah@example.com",
         summary="Technical program manager with 9 years coordinating cross-functional delivery for platform teams.",
         experience=["TPM, Cobalt Health Software, 2018 - present: Runs quarterly planning for 6 teams; reduced slippage by 35%.",
                     "Scrum Master, Greywell, 2015 - 2018."],
         skills="Program management, Jira, risk management, agile coaching.",
         education="BSc Information Systems, University of Manchester.",
         details=["Languages: English", "Availability: 2 months notice", "Salary expectation: GBP 80,000"]),
    dict(slug="isabelle-moreau-marketing-manager", name="Isabelle Moreau", head="Product Marketing Manager | Paris, FR | isabelle.moreau@example.com",
         summary="Product marketing manager with 7 years launching B2B software across Europe.",
         experience=["Product Marketing Manager, Lumen Software, 2020 - present: Positioning, launch plans, sales enablement.",
                     "Marketing Specialist, Seine Digital, 2017 - 2020."],
         skills="Positioning, messaging, launches, analytics, copywriting.",
         education="MSc Marketing, HEC Paris.",
         details=["Languages: French, English", "Availability: 2 months notice", "Salary expectation: EUR 72,000"]),
    dict(slug="omar-farouk-account-executive", name="Omar Farouk", head="Enterprise Account Executive | London, UK | omar.farouk@example.com",
         summary="Account executive with 8 years selling HR and workforce software to enterprises.",
         experience=["Enterprise AE, Talentwave, 2019 - present: Closed GBP 3.2M annual new business; multi-threaded enterprise deals.",
                     "Sales Development Rep, Staffbase, 2016 - 2019."],
         skills="Enterprise sales, MEDDICC, negotiation, CRM.",
         education="BA Economics, University of Nottingham.",
         details=["Languages: English, Arabic", "Availability: 3 months notice", "Salary expectation: GBP 110,000 OTE"]),
    dict(slug="julia-hoffmann-customer-success", labels=DE, name="Julia Hoffmann", head="Customer Success Managerin | Hamburg, DE | julia.hoffmann@example.com",
         summary="Customer Success Managerin mit 6 Jahren Erfahrung in B2B-Software; Schwerpunkt Onboarding und Kundenbindung.",
         experience=["Customer Success Managerin, Kestrel Logistics Software, 2020 - heute: Betreuung von 45 Enterprise-Kunden; Churn um 18 Prozent gesenkt.",
                     "Support Specialist, Altmark Systems, 2018 - 2020."],
         skills="Onboarding, Kundenbindung, Reporting, Zendesk, Praesentationen.",
         education="BA Betriebswirtschaft, Universitaet Hamburg.",
         details=["Sprachen: Deutsch (Muttersprache), Englisch (verhandlungssicher)", "Verfuegbarkeit: 3 Monate", "Gehaltsvorstellung: EUR 68.000"]),
    dict(slug="peter-kowalski-recruiter", name="Peter Kowalski", head="Technical Recruiter | Warsaw, PL | peter.kowalski@example.com",
         summary="Technical recruiter with 6 years hiring engineers and designers for scale-ups; experienced with structured interviews and inclusive hiring.",
         experience=["Senior Recruiter, Vistula Tech, 2020 - present: 120 hires, including a design team of 9; built a structured interview kit.",
                     "Recruiter, Baltic Staffing, 2017 - 2020."],
         skills="Sourcing, structured interviews, ATS, employer branding.",
         education="BA Psychology, University of Warsaw.",
         details=["Languages: Polish, English", "Availability: 1 month notice", "Salary expectation: EUR 55,000"]),
    dict(slug="nina-bergstrom-finance-analyst", name="Nina Bergstrom", head="Financial Analyst | Oslo, NO | nina.bergstrom@example.com",
         summary="Financial analyst with 5 years in FP&A for software companies.",
         experience=["FP&A Analyst, Fjord Software, 2021 - present: Budgeting, forecasting, board reporting.",
                     "Junior Analyst, Nordbank, 2019 - 2021."],
         skills="Excel, Power BI, forecasting, SQL.",
         education="MSc Finance, BI Norwegian Business School.",
         details=["Languages: Norwegian, English", "Availability: 2 months notice", "Salary expectation: EUR 66,000"]),
    dict(slug="ravi-patel-junior-ux-researcher", name="Ravi Patel", head="Junior UX Researcher | Leicester, UK | ravi.patel@example.com",
         summary="Junior user researcher with 1 year of experience; recent MSc graduate seeking a B2B research or design role.",
         experience=["Research Assistant, University of Leicester HCI Lab, 2024 - 2025: Interviews and usability tests for an accessibility study.",
                     "Internship, Cobalt Health Software, 2025: Supported 6 usability sessions."],
         skills="Interviews, usability testing, Dovetail, Figma basics, thematic analysis.",
         education="MSc Human-Computer Interaction, University of Leicester.",
         details=["Languages: English, Gujarati", "Availability: immediate", "Salary expectation: GBP 38,000"]),
    dict(slug="clara-jensen-art-director", name="Clara Jensen", head="Art Director | Copenhagen, DK | clara.jensen@example.com",
         summary="Art director with 10 years in advertising and brand strategy for consumer brands.",
         experience=["Art Director, Nord Reklame, 2016 - present: Campaign concepts, creative direction, photography.",
                     "Designer, Studio Hygge, 2013 - 2016."],
         skills="Creative direction, brand identity, Adobe Creative Suite, presentation.",
         education="BA Graphic Design, Danish Design School.",
         details=["Languages: Danish, English", "Availability: 3 months notice", "Salary expectation: EUR 75,000"]),
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
    for candidate in CANDIDATES:
        build(candidate)
    print(f"Wrote {len(CANDIDATES)} resumes to {OUTPUT}")


if __name__ == "__main__":
    main()
