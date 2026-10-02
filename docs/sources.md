# Sources, attribution and submission gates

Checked 2026-09-20. Public pages were read directly; Challenge 03's three detail sections and the FAQ judging/eligibility sections were expanded in a browser.

- [Organizer home and schedule](https://www.yuvayodhatech.com/): lists idea submission by October 4, teams of 1–4, Indian citizenship/residency, age 18+, full-time enrollment in India; prototype/judging October 11–November 22 and finale January 2027. Exact cutoff time and timezone require confirmation.
- [Challenge 03](https://www.yuvayodhatech.com/challenges): asks for local reliability, architecture/design, baseline evidence and ownership/O&M with affordability. A simulation is encouraged; hardware is not expected. Ideas include shared storage, flexible loads and local scheduling.
- [Official FAQ](https://www.yuvayodhatech.com/faq): first evaluation weights are problem 20%, architecture 20%, impact 25%, feasibility 20%, sustainability 15%. Its eligibility section mentions UG/PG/STEM enrollment; apply the more detailed home-page criteria too.
- [Terms](https://www.yuvayodhatech.com/terms): submissions must respect originality/IP and avoid unauthorized AI-generated content. This does **not** establish that all AI assistance or pre-existing code is allowed. Obtain organizer clarification for this existing repository and AI-assisted implementation.
- [Linked application portal](https://apply.younoodle.com/round/yuva_yodha_tech_hackathon_2026): public fetch provided no application fields. Attachment limits, required answers and registered-account workflow remain unverified. No form was submitted or terms accepted.

No data source is cited as support for the synthetic asset sizes, load traces or costs. Their source/status is explicitly an engineering assumption; see `data/assumptions.json`. No personal interviews, vendor quotations, partnerships or field trials were conducted.

Runtime dependency versions and integrity pins are in `uv.lock`. This project uses FastAPI, Starlette, Pydantic, uvicorn, httpx, plus their dependencies. Official project links: [FastAPI](https://github.com/fastapi/fastapi), [Pydantic](https://github.com/pydantic/pydantic), [uvicorn](https://github.com/encode/uvicorn), [httpx](https://github.com/encode/httpx), [uv](https://github.com/astral-sh/uv). Retain each package's license notices when redistributing dependencies. CI uses GitHub checkout and Astral setup-uv actions. The project originally provided no license file; this change does not choose a license on the author's behalf.

## User / organizer actions before submission

1. Confirm eligibility and registration details against the current portal.
2. Ask whether this pre-existing project and disclosed AI-assisted code/docs are permitted, and what disclosure is required.
3. Confirm deadline timezone, attachment limits and all required fields.
4. Replace cost placeholders with dated quotes and, where feasible, validate operator/resident assumptions with consent.
5. Review the generated evidence and submit only after author approval.

These are external release gates, not outstanding local programming work or evidence of permission. No external contact, publication, payment or hardware connection has been performed.
