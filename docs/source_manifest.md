# Source manifest

| Data/source | Use | License/version/retrieval | Attribution/transformation |
|---|---|---|---|
| Synthetic generator in `src/data_generator.py` | All generated employee, organization, workflow, access, asset, and audit records | Project code; no external retrieval | Deterministic illustrative records; names are labels, email domain is reserved `example.test` |
| `config/config.json` | Default seed, counts, paths, injection setting | Project configuration | User-editable local settings |
| `database/seed.sql` | Small fixed department, role, and access vocabulary for standalone schema seeding | Project code; no external retrieval | Synthetic organizational vocabulary; production data is not used |

No external or confidential data is sourced. All employees, managers, approvals, IDs, dates, roles, and asset serials are synthetic.
