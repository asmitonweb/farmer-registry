# OpenG2P deployment checklist (G2R-311)

## Decided
- **No COSS Helm repo.** Each registry's chart is stored in its own repo (`helm/` in farmer, livestock and crop). Jenkins deploys from the checked-out chart. No chart publishing, gh-pages, OCI push or Rancher catalog.
- **Namespaces follow the OpenG2P standard.** Below, `<commons-ns>` is the shared-services namespace and `<registry-ns>` is each registry's namespace. Fill in the real names from the OpenG2P deployment docs.

## Decide first
- [ ] **Base images:** GitLab (Gen2 doc) or OpenG2P Docker Hub (Jira / repo)?
- [ ] **Commons Secrets:** who re-syncs the copies in each `<registry-ns>` when a commons password changes?

## Repo fixes before go-live
- [ ] Jenkinsfile and `ci/commons-services/upgrade.sh` still use the GitLab Helm repo. Switch to `openg2p.github.io/openg2p-helm`.
- [ ] Commons-services is pinned at 2.3.0-rc.217. Move to **2.3.4-rc.245**.
- [ ] Image paths in `values.yaml` and `values-far.yaml` point at GitLab. Point them at ECR / OpenG2P. Delete `.gitlab-ci.yml`.
- [ ] Remove the leftover chart-publishing pieces from `Chart.yaml`: the Rancher catalog annotations and the "CI publishes the version" comment.
- [ ] Our scripts and values hard-code `far` and `commons` (Jenkinsfiles, `ci/commons-services/*`, `ci/connector/values-*.yaml`, `commons-aliases.yaml`, `farmer-deploy-rbac.yaml`). Parameterise them, or rename them to the OpenG2P standard names.
- [ ] Commit the per-environment values and the CA bundle ConfigMap to git. Today they exist only on the cluster.

## Platform
- [ ] Versions come from OpenG2P/versions: registry **1.2.2-rc.544**, commons **2.3.4-rc.245**. Releases only, never `develop`.
- [ ] Namespaces match the OpenG2P standard names: one `<commons-ns>` plus one `<registry-ns>` per registry. Node usage is under 80%.
- [ ] Keycloak, Postgres, MinIO, Master Data and AWE run **only** in `<commons-ns>`.
- [ ] The 5 commons Secrets are cloned into each `<registry-ns>`: `commons-postgresql`, `commons-keycloak`, `master-data`, `commons-minio`, `awe-db-user`.
- [ ] Commons-services names resolve from registry pods (apply `commons-aliases.yaml`, edited for the standard namespace names).

## Registry services (each `<registry-ns>`)
- [ ] Each registry deploys from its own repo's chart: `helm dependency build` + `helm lint` / `template`, then `helm upgrade --install <release> ./helm/<chart>`.
- [ ] Livestock and crop each have their own chart directory, not a copy of the farmer chart.
- [ ] Images: Jenkins → ECR → tag in Helm values (git) → `helm upgrade`. Dev uses the `develop` tag; staging/UAT use a pinned release.
- [ ] All environment variables come from Helm. Nothing is edited by hand in Rancher. Check `COOKIE_DOMAIN`, the https IAM URL and the app mnemonic.
- [ ] Pods are Running: staff-api, staff-ui, partner-api, celery worker/beat, dashboard-api.
- [ ] Jobs succeed:
  - postgres-init and keycloak-init
  - **db-seed**
  - iam-register (tile shows in IAM)
  - sanity, with e2e on
  - reporting views
- [ ] **Geo:** seed-locations, plus the one-time migrate-far-geo for farmer, run (dry-run first). Location dropdowns cascade in the intake form.
- [ ] Re-running a single Job (`helm get hooks` → `kubectl apply`) has been tried on dev.

## ODK
- [ ] Decide: external ODK Central or the in-cluster one.
- [ ] Form and media are published. The connector pod can reach ODK and is deployed with the right `ENVIRONMENT`.
- [ ] Partner `farmer-partner` is registered. ODK submission → draft intake → approval → farmer in the register.

## DNS and TLS (fill in on the call)
| Host | Public/Private | Resolves | TLS |
|---|---|---|---|
| Farmer / livestock / crop staff portals | public | | |
| Internal staff host (`staff-<registry>.<registry-ns>.openg2p.test`) | private | | |
| Keycloak (public + `keycloak.<commons-ns>.openg2p.test`) | both | | |
| AWE (`awe.<commons-ns>.openg2p.test`) | private | | |
| MinIO (browser-resolvable) | public | | |
| ODK Central (`odk-central*.oanstaging.com`) | public | | |
| Connector UIs, dashboard-api (`*.<registry-ns>.openg2p.test`) | private | | |

- [ ] Keycloak redirect URIs and cookie domain match the final hosts. The Local CA is trusted by internal clients. nginx allows 12 MB uploads on every portal.

## Sign-off
- [ ] Staff login, intake with photo upload, AWE approval, and the farmer is created.
- [ ] Rollback is ready: Helm values backed up, revisions noted, DB snapshot taken.
