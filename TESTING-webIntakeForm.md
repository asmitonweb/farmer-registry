# Testing the Web Intake Form branch (`webIntakeForm`)

This branch bundles everything needed to test the farmer web intake work:

| Change | Where |
| --- | --- |
| Single farmer intake form (GEN1 parity), Ethiopic calendar, server-side validation | `farmer-extension/` (PR #14) |
| Local stack on public Docker Hub images, staff UI 1.2.1 | `docker-compose.yml`, `Dockerfile` (PR #15) |
| "Create New Submission" dropdown no longer hidden behind the page card | `docker/staff-ui/assets/staff-ui-1.2-regressions.css` |
| `other_land_owner` is a Yes/No dropdown labeled "Household Farms Land Owned By Others"; unset stays NULL instead of becoming "No" | `zz_farmer_household_layout.sql`, household domain service |

## Prerequisites

- Docker Desktop (or engine + compose v2) with **~8 GB memory** allotted
- Free ports: `3001` (portal), `8001`, `8006`, `8020`, `8030`, `8031`, `8040`,
  `8042`, `8080` (Keycloak), `5432`, `6379`, `9000`, `9001`
- No registry login needed — all base images are public
  (`registry.gitlab.com/openg2p/...` and Docker Hub)
- If you also run the `openg2p-developer` stack: stop it first. The two stacks
  fight over the same fixed ports (Keycloak 8080, MinIO 9000/9001, Postgres…).

## Get it running

```bash
git clone https://github.com/asmitonweb/farmer-registry.git
cd farmer-registry
git checkout webIntakeForm

# Build our images (base platform images are pulled automatically) and start
# everything EXCEPT the dashboard — see "Known limitation" below.
docker compose up -d --build \
  farmer-registry-staff-ui \
  farmer-registry-partner-api \
  farmer-registry-celery-worker \
  farmer-registry-celery-beat \
  farmer-registry-db-seed \
  farmer-registry-geo-remap \
  awe-ui
```

Dependencies pull in the rest (Postgres, Redis, MinIO, Keycloak, IAM,
master-data, AWE, staff-api, geo-seed). First run downloads several GB of
images and seeds ~21,000 Ethiopian localities — expect **10–20 minutes**.

**Do NOT run a bare `docker compose up --build -d`** — it tries to build
`farmer-registry-dashboard-ui`, which currently fails (its `lib/` directory
was never committed; being recovered separately). Everything else is
unaffected: the portal's Dashboard button just 404s.

### Wait for readiness

```bash
docker compose ps
```

Ready when:

- `farmer-registry-staff-api`, `farmer-registry-staff-ui`, `iam-staff-api`,
  `farmer-registry-master-data-api`, `keycloak`, `postgres` → **healthy / up**
- These are **supposed to exit 0** (one-shot jobs — don't restart them):
  `minio-init`, `keycloak-init`, `iam-register-farmer-app`,
  `farmer-registry-geo-seed`, `farmer-registry-db-seed`,
  `farmer-registry-geo-remap`

If every page gives you 403 after login, check
`docker logs farmer-registry-iam-register-app` — that job registers the
role/permission catalog and must have completed.

## Log in

Portal: **http://localhost:3001**

| User | Password | Role |
| --- | --- | --- |
| `staff` | `staff` | Development Agent (day-to-day intake) |
| `admin` | `admin` | Staff admin |
| `alex.carter` | `pass` | AWE approver, stage 1 |
| `nina.patel` | `pass` | AWE approver, stage 2 |

Staff API docs (optional): http://localhost:8001/docs

## What to test

1. **Create New Submission dropdown** — on the Farmer submissions page, the
   button's menu must render *above* the page card and its entries must be
   clickable (this was broken by a 1.2.x base-image regression).
2. **Single farmer intake form** — one form covering personal info, household,
   land (dialog table), crops, livestock, farm inputs, phone numbers, IDs.
3. **Ethiopic calendar** — Date of Birth offers GC and EC entry; check
   conversion consistency.
4. **Server-side validation** — try invalid inputs (digits in a name,
   `size_of_group` ≠ males + females, more children than family size,
   father-included with zero males). The API must reject them even if the
   browser is bypassed.
5. **Household Information section** —
   - "Household Farms Land Owned By Others" renders as a **dropdown**
     (Select / YES / NO), not a checkbox or radio.
   - Leave it on "Select", submit, and verify the stored value is NULL, not
     false:
     ```bash
     docker exec farmer-registry-postgres psql -U postgres -d farmer_registry_db \
       -c "SELECT record_name, other_land_owner FROM g2p_intake_form_households ORDER BY created_at DESC LIMIT 5;"
     ```
6. **Approval flow** — submit as `staff`, approve as `alex.carter` then
   `nina.patel` (AWE UI: http://localhost:8031), confirm the farmer lands in
   the register and the household's `household_head` auto-fills from the
   linked head farmer.

## Gotchas

- **Hard refresh after any staff-ui rebuild** (`Ctrl+Shift+R`). CSS/JS
  filenames don't change when we patch them and are served
  `Cache-Control: immutable`, so a normal reload keeps the old bytes forever.
- Rebuilding just one side after pulling new commits:
  ```bash
  # backend (farmer-extension / metadata / validation)
  docker compose build farmer-registry-staff-api && docker compose up -d --no-deps farmer-registry-staff-api
  # portal (CSS/bundle patches)
  docker compose build farmer-registry-staff-ui && docker compose up -d --no-deps farmer-registry-staff-ui
  ```
- Metadata (form layouts, labels) is seeded into the DB by `db-seed`. If you
  pulled layout changes onto an **existing** stack, re-run it:
  ```bash
  docker compose run --rm farmer-registry-db-seed
  ```
- Reset everything (wipes the database and files):
  ```bash
  docker compose down -v
  ```
  then repeat the `up` command above.

## Known limitation

`farmer-registry-dashboard-ui` does not build on this branch —
`dashboard-ui/lib/` (chart SQL + DB helpers) was accidentally excluded by a
`.gitignore` rule at the time it was committed and is being recovered. Skip
the service (the `up` command above already does); the Dashboard header
button will 404 until it's restored.
