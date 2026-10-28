# Sample applicants

Synthetic resumes (PDF) for functional tests of the careers site. Regenerate them with `python samples/applicants/generate.py` (needs `pip install fpdf2`). Together with the three older files in [`../resumes`](../resumes/README.md) they cover strong, partial and weak matches, a German resume, and two protection cases. All people, companies and contact details are fictional.

| Resume | Apply to | Result seen in the dev deployment (AI score, reviewer) |
| --- | --- | --- |
| `../resumes/maya-rodriguez-senior-product-designer.pdf` | Senior Product Designer | Strong match, 92 → 86, reviewer partially agrees |
| `amara-osei-product-designer.pdf` | Senior Product Designer | Not a match, 57 → 52, reviewer disagrees. The recruiter can override it, which shows up as "Overrode AI" in AI Operations. |
| `../resumes/tom-becker-junior-frontend-developer.pdf` | Senior Product Designer, Senior Frontend Engineer | Not a match |
| `../resumes/lena-fischer-visual-designer.pdf` | Senior Product Designer | Needs manual review: the hidden instruction is blocked by Azure AI Content Safety |
| `priyanka-desai-senior-frontend-engineer.pdf` | Senior Frontend Engineer | Strong match, 87 |
| `diego-alvarez-backend-developer.pdf` | Senior Frontend Engineer | Not a match, 12 |
| `sven-larsen-ml-engineer-rag.pdf` | Machine Learning Engineer, Agents and Evaluation | Strong match, 84 |
| `aditi-rao-data-scientist.pdf` | Machine Learning Engineer, Agents and Evaluation | Not a match, 42 |
| `anika-schmidt-customer-success-dach.pdf` (German) | Customer Success Manager (DACH) | Strong match, 90 |
| `ethan-walker-customer-success-manager.pdf` | Customer Success Manager (DACH) | Not a match, 40: no German, which the role requires |
| `sophie-laurent-ux-researcher.pdf` | UX Researcher | Possible match, 89 → 76, reviewer disagrees |

Also try uploading a file that is not a PDF (for example a ZIP renamed to `.pdf`): the careers site rejects it with "The resume must be a PDF file".

Scores vary a little between runs. The job postings used in the dev deployment were drafted with the job description agent from short notes: Senior Product Designer (London), Senior Frontend Engineer (Berlin), Machine Learning Engineer, Agents and Evaluation (Madrid), Customer Success Manager DACH (Hamburg) and UX Researcher (remote UK).
