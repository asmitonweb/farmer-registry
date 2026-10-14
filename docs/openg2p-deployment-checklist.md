# OpenG2P architecture: deployment verification checklist (G2R-311)

Use this to sign off that a Farmer Registry environment runs on the OpenG2P
GitHub architecture: commons in its own namespace, registries in
`far` / `live` / `crop`, images in ECR, charts deployed from the checked-out
source. Tick each line only after you have seen the evidence (a command's
output or a working screen), not on someone's say-so.

Columns to fill in on the call: **Owner**, **Env (dev/staging)**, **Status**.

Sources: Jira G2R-311 and the "Gen2 Configurations" Google Doc (new
standards: shared-services architecture, deployment procedures, versions).
Items that come from the doc are tagged **[Gen2]**.

---

## Decide on the call: where the doc and G2R-311 disagree

- [ ] **Chart for livestock and crop.** [Gen2] says livestock installs the farmer chart (`openg2p/openg2p-farmer-registry` 1.2.0) with its own `values-live.yaml`. G2R-311 says each registry has a thin chart in its own repo. Pick one.
- [ ] **Where charts come from.** [Gen2] has a "CI/CD pushes the helm chart to repo" step. G2R-311 (G2R-312) decided **no** COSS Helm repo: Jenkins deploys the checked-out chart. Confirm G2R-311 wins.
- [ ] **Base image registry.** [Gen2] pulls base images from `registry.gitlab.com`. G2R-311 says OpenG2P is back on GitHub / Docker Hub (`openg2p/openg2p-registry-*`). The repo already uses Docker Hub. Confirm.
- [ ] **Namespace name.** [Gen2] writes `common`; G2R-311 and all our scripts use `commons`. Confirm `commons`.
- [ ] **db-seed frequency.** [Gen2] calls db-seed a one-time activity, but our chart runs it as a hook on **every** deploy. The seed SQL is idempotent, so that's safe. Agree whether to keep it that way.
- [ ] **Secrets across namespaces.** [Gen2] says clone the commons Secrets into each registry namespace (§5). Agree who owns re-syncing them when commons rotates a password.

## 0. Known gaps in the repo today (fix or accept before sign-off)

Found in `develop` while preparing this list. Each one breaks an acceptance criterion of G2R-311.

- [ ] `Jenkinsfile:169` still runs `helm repo add openg2p-gitlab https://gitlab.com/...`. It must use `https://openg2p.github.io/openg2p-helm`, the repo `Chart.yaml` already points at.
- [ ] `ci/commons-services/upgrade.sh` pins `openg2p-gitlab/openg2p-commons-services` at **2.3.0-rc.217**. The target is **2.3.4-rc.245** from the GitHub Helm repo.
- [ ] `ci/commons-services/values-far.yaml` overrides master-data, AWE, IAM and consent-manager images to `registry.gitlab.com/openg2p/platform-services/...`. Confirm where OpenG2P publishes these now (Docker Hub `openg2p/*`?) and re-point them.
- [ ] `helm/openg2p-farmer-registry/values.yaml` default images are `registry.gitlab.com/openg2p/registry/farmer-registry/*`. Point them at ECR (G2R-315).
- [ ] `.gitlab-ci.yml` still exists. Delete it (G2R-318).
- [ ] `values-dev.yaml` uses ECR path `oan/farmer-registry`, but Jenkins pushes to `openg2p/farmer-registry`. Pick one path and remove the other.
- [ ] Per-environment values (hostnames, Keycloak, CA bundle) exist only as live Helm values. Agree on where they live in git (decision #2 in G2R-311).
- [ ] `far-ca-bundle` ConfigMap is hand-applied and not in git (deployment.md §4.4). Agree on an owner.

---

## 1. Versions and sources

Pinned releases only, taken from https://github.com/OpenG2P/versions.

- [ ] Helm repo on Jenkins and on the box: `helm repo list` shows `https://openg2p.github.io/openg2p-helm` and **no** gitlab.com entry.
- [ ] [Gen2] The registry-platform version is copied from OpenG2P/versions into each Dockerfile's `RP_VERSION`. It is a release (1.2.x), never a `develop` build.
- [ ] [Gen2] All four Dockerfile targets (celery, staff-api, partner-api, db-seed) are on the same base version. The `ARG RP_VERSION` / `FROM` lines are identical across farmer, livestock and crop.
- [ ] [Gen2] The commons version is the one in OpenG2P/versions under the commons folder.
- [ ] `openg2p-commons-base` is pinned to `2.3.4-rc.245`.
- [ ] `openg2p-commons-services` is pinned to `2.3.4-rc.245`.
- [ ] `openg2p-registry` dependency is `1.2.2-rc.544` in `helm/openg2p-farmer-registry/Chart.yaml`.
- [ ] The same version is in `Dockerfile` (`RP_VERSION`, `STAFF_UI_VERSION`) and `Jenkinsfile` (`RP_VERSION`). `test/test_rp_pin_lockstep.py` passes.
- [ ] `./scripts/bump-rp-version.sh -n` resolves against OpenG2P/versions and GitHub, not GitLab.
- [ ] `helm dependency build helm/openg2p-farmer-registry` succeeds from a clean checkout.
- [ ] Dev uses the `develop` tag. Staging/UAT use an explicitly pinned release tag, never `develop`.
- [ ] `grep -rni gitlab .` on all three registry repos returns nothing, apart from history notes in docs.

## 2. Cluster and namespaces

- [ ] Namespaces exist: `commons`, `far`, `live`, `crop`.
- [ ] Istio is installed. Gateways exist: `internal` (private, for `*.openg2p.test`) and the public gateway.
- [ ] RBAC: `ci/k8s/farmer-deploy-rbac.yaml` is applied in `far` (SA `farmer-ci`, `admin` RoleBinding, Istio Role).
- [ ] Jenkins kubeconfig credentials work: `kubectl auth can-i list secrets -n far` is `yes` with `gen2-dev-kubeconfig` / `staging-farmer-kubeconfig`.
- [ ] ECR pull secret `far-ecr` exists in each registry namespace, and the `ecr-creds-refresh` CronJob is running (every 8h).
- [ ] Nodes can pull from `379220350808.dkr.ecr.ap-south-1.amazonaws.com`.
- [ ] [Gen2] Node capacity: `kubectl top nodes` shows every node under 80% CPU and memory. Above 80%, add a node before the move.
- [ ] [Gen2] In Rancher (Apps → Repositories), the OpenG2P GitHub chart repo (`https://openg2p.github.io/openg2p-helm`) is added. No GitLab chart repo is left.
- [ ] [Gen2] The WireGuard access list is up to date for everyone who needs the `*.openg2p.test` hosts, Rancher (`rancher.openg2p.test`) and kubectl.
- [ ] [Gen2] Each developer who needs kubectl has a downloaded, exported kubeconfig scoped to their namespace.

## 3. Commons base (`commons` namespace)

- [ ] Release `commons` is `deployed` (`helm list -n commons`).
- [ ] Pods are Running: `commons-postgresql-0`, `commons-redis`, `commons-minio`, `commons-keycloak`.
- [ ] Secrets exist: `commons-postgresql` (`postgres-password`), `commons-keycloak` (`admin-password`), `commons-minio` (`root-user`, `root-password`, `readonly-user`, `readonly-password`).
- [ ] Postgres has PVC/backup configured. The DBs `master_data`, `awe` and `farmer_registry` will all live in this one instance.
- [ ] MinIO buckets exist, including `templates` (used for the ODK Jinja transform).

## 4. Commons services (`commons` namespace)

- [ ] Release `commons-services` is `deployed` at `2.3.4-rc.245`.
- [ ] Running and healthy: IAM staff-portal API + UI, Master Data API, Partner Management (partner + staff APIs), Consent Manager (partner + API), Audit Manager, Keymanager, AWE + AWE UI.
- [ ] Master Data `openapi.json` serves `/geo/get_all_geo_levels` (G2R-172 regression check).
- [ ] Keycloak realm `staff` exists.
- [ ] Secrets the registry needs exist in `commons`: `master-data` (`master-data-db-user`), `awe-db-user` (`awe-db-user-password`). §5 covers copying them into each registry namespace.
- [ ] [Gen2] Master Data and IAM seeding is done by their own repos/charts, not by the registry db-seed. Confirm it ran in `commons`.
- [ ] No `ImagePullBackOff` on any `commons-services-*` pod, including CronJobs (`cm-api-expire-*`, `kc-sa-role-*`).

## 5. Cross-namespace wiring (new: commons is no longer inside `far`)

[Gen2] shared-services standard: the `commons` namespace hosts Keycloak, Postgres, MinIO, Master Data and AWE. `far`, `live` and `crop` only point at them; no registry namespace runs its own copy.

- [ ] No Keycloak, Postgres, MinIO, Master Data or AWE pods run in `far`, `live` or `crop` (`kubectl get pods -n far | grep -E 'keycloak|postgresql|minio|master-data|awe'` is empty).
- [ ] [Gen2] These namespace-scoped Secrets are cloned from `commons` into **each** of `far`, `live` and `crop`: `commons-postgresql`, `commons-keycloak`, `master-data`, `commons-minio`, `awe-db-user`. Clone with:
  ```sh
  for s in commons-postgresql commons-keycloak master-data commons-minio awe-db-user; do
    kubectl get secret $s -n commons -o json \
      | jq 'del(.metadata.namespace,.metadata.uid,.metadata.resourceVersion,.metadata.creationTimestamp,.metadata.managedFields,.metadata.ownerReferences,.metadata.annotations,.metadata.labels)' \
      | jq '.metadata.namespace="far"' | kubectl apply -f -
  done
  ```
- [ ] The cloned Secret values match `commons` (compare `kubectl get secret <name> -n <ns> -o jsonpath='{.data}'` in both namespaces).

The registry chart calls commons services by **bare short name**. With commons in its own namespace those names do not resolve, and the failure is silent (for example, the Location dropdowns disappear).

- [ ] `ci/k8s/commons-aliases.yaml` is applied in `far`, `live` and `crop`, with `externalName` using `.commons.svc.cluster.local`.
- [ ] Postgres, Keycloak, MinIO and Redis hosts in the registry values are fully qualified (`commons-postgresql.commons.svc.cluster.local`, etc.) or aliased.
- [ ] This DNS loop prints an IP for every line, with no `UNRESOLVED`:
  ```sh
  for h in iam-staff-portal-api master-data-api pm-partner-api pm-staff-portal-api \
           cm-partner-api cm-api keymanager auditmanager; do
    printf '%-24s ' "$h"
    kubectl -n far exec deploy/farmer-registry-partner-api -- getent hosts "commons-services-$h" || echo UNRESOLVED
  done
  ```
- [ ] The same check passes from `live` and `crop`.

## 6. Farmer Registry release (`far` namespace)

### 6a. Images and release
- [ ] Jenkins built and pushed all images to ECR `openg2p/farmer-registry/*`: `staff-api`, `staff-ui`, `partner-api`, `celery`, `db-seed`, `sanity-tests`, `dashboard-api`, `connector-service`, `connector-ui`.
- [ ] Release `farmer-registry` is `deployed`, not `failed` (`helm history farmer-registry -n far`).
- [ ] Running images match the build sha: `kubectl -n far get deploy -o jsonpath='{..image}'`.
- [ ] Deployed from the **checked-out chart** (`helm upgrade --install farmer-registry ./helm/openg2p-farmer-registry`), not from a hosted COSS chart.
- [ ] [Gen2] The chart's image values point at ECR and are **checked into git**, not set by hand in Rancher.
- [ ] [Gen2] All environment variables come from Helm values. Nothing was set by hand (no `kubectl set env`, no Rancher edits). Check: `helm get manifest farmer-registry -n far` env matches `kubectl get deploy -n far -o yaml` env.
- [ ] [Gen2] Farmer config, set in Helm values:
  - `COOKIE_DOMAIN` matches the final public domain.
  - The IAM URL the client uses is **https**.
  - The application mnemonic is set (data auditor, …).
- [ ] [Gen2] Livestock and crop need no MinIO change. Confirm their MinIO values are untouched.
- [ ] Live values were backed up before deploy (`helm get values farmer-registry -n far -o yaml`).
- [ ] Rollouts are complete: `staff-portal-api`, `staff-portal-ui`, `partner-api`, `celery-worker`, `celery-beat-producer`, `dashboard-api`, `farmer-registry-redis-master`.

### 6b. Install-time Jobs
- [ ] `farmer-registry-postgres-init` succeeded: DB `farmer_registry`, role `farmer_registry_user`, Secret `farmer-registry`.
- [ ] `farmer-registry-idgen-pg-init` succeeded: DB `farmer_registry_idgenerator`.
- [ ] `farmer-registry-keycloak-init` succeeded: client `farmer-registry-staff-portal` in realm `staff`, redirect `https://<registryHostname>/*`, Secret `farmer-registry-staff-portal`.
- [ ] Keycloak client has **Service accounts enabled**. The celery worker needs it for AWE, otherwise ingest fails with `AWE_BEARER_TOKEN_REQUIRED`.

### 6c. Hook Jobs (run on every deploy, in weight order)
- [ ] `awe-callback-hmac-secret`: Secret `farmer-registry-awe-callback-hmac` exists.
- [ ] **db-seed** (`farmer-registry-db-seed`, weight 10) succeeded. Log shows schema/meta_data, AWE policy, `callback_secret` and templates loaded. `loadSampleData` is off on staging.
- [ ] Sanity seeds `pm-seed` / `cm-seed` / `data-seed` (11–13) succeeded.
- [ ] `iam-register` (19/20) succeeded. The "Farmer Registry" tile appears in IAM after login.
- [ ] **Sanity** (`farmer-registry-sanity`, 25) succeeded. Run once with `runE2e: true`: the smoke-only default stays green even when DNS is broken.
- [ ] **Reporting views** (`farmer-registry-fr-reporting-views`, 45) succeeded. CronJob `...-fr-reporting-views-refresh` is scheduled hourly.
- [ ] [Gen2] The team has a working way to re-run a single hook Job (e.g. db-seed) without a full deploy, and has tried it once on dev:
  ```sh
  helm get hooks farmer-registry -n far \
    | yq eval-all 'select(.kind == "Job" and .metadata.name == "<JOB-NAME>")' - > job.yaml
  kubectl delete job <JOB-NAME> -n far --ignore-not-found
  kubectl apply -f job.yaml -n far
  ```

### 6d. Geo / location hierarchy (geo seed / geo map)
- [ ] Master Data holds the Ethiopia hierarchy (region > zone > woreda > kebele). Run the Jenkins `ci/commons-services` job with `ACTION=seed-locations`, `DRY_RUN=true` first, then commit.
- [ ] `far` only: `migrate-far-geo` was run once (moves off the ETH pack/Kamuntu and remaps farmer records), dry-run first.
- [ ] `livestock`'s own name-keyed hierarchy in `live` is left alone; the seed guard should refuse it.
- [ ] Master Data's `geoSeed.countryPack` setting matches the decision (ETH pack vs our seed). Don't run both.
- [ ] UI check: the intake form's **Location** section shows all five geo dropdowns and they cascade.
- [ ] Reporting geo levels (`docker/db-seed/reporting_geo_levels.sh`) line up with the views. The dashboard chart `farmersByRegion` returns data.
- [ ] Maps content (`mapsContent.enabled`) stays disabled unless agreed otherwise.

### 6e. Dashboard API
- [ ] `/health` returns 200 and charts `farmerKpis`, `farmersByRegion`, `landTenureSplit`, `registryTrendByMonth` return 200.
- [ ] Service is ClusterIP only. It is never attached to the public gateway because it has no auth.

### 6f. Pre-existing objects the release expects
- [ ] `far-ca-bundle` ConfigMap (`ca-bundle.pem`, public roots plus the OpenG2P Local CA) exists **before** the first deploy and is mounted into staff-portal-api.
- [ ] Optionally `openg2p-ca-cert` for the UIs (`NODE_EXTRA_CA_CERTS`).

## 7. ODK Central and connector

- [ ] Agree which ODK Central to use: external (`odk-central.oanstaging.com` / `odk-central-development.oanstaging.com`) or in-cluster `commons-services-odk-central-frontend`. Write the decision down.
- [ ] ODK Central is up and reachable over HTTPS from field devices (public DNS + valid public TLS).
- [ ] ODK Central is reachable **from the connector pod** (`kubectl -n far exec deploy/farmer-connector-worker -- wget -qS -O- <odk-url>/v1/projects`). Expect 401, not a DNS or TLS error.
- [ ] Project created; `odk/ATI_Farmers_Profile_ODK_Form_v2.xlsx` published with media `KebeleList.csv` and `PrimaryCoopList.csv`. Note the project id and form id.
- [ ] Release `farmer-connector` deployed via the `ci/connector` Jenkins job with `ENVIRONMENT` set explicitly. Staging must not pick up dev's values.
- [ ] `farmer_connector` DB and Secret were created by `postgres-init`.
- [ ] Connector settings are under `extraEnv` (not `commonEnv`): `CONNECTOR_ODK_CENTRAL_BASE_URL`, `_PROJECT_ID`, `_FORM_ID`, `_EMAIL`. The password comes from a Secret via `extraEnvFrom`.
- [ ] Partner `farmer-partner` is registered in `master_data.g2p_partners`.
- [ ] `partnerApiService` / `redisHost` in `ci/connector/values-*.yaml` resolve in the namespace.
- [ ] Connector UI is reachable at `connector-farmer-registry.far.openg2p.test`, on the internal gateway only.
- [ ] Same checks for `live` and `crop` connectors.

### 7a. Data sharing: Kafka / WebSub (if in scope for this move)
- [ ] [Gen2] Subscription architecture: the transformation does the schema conversion, data is pushed to WebSub, and consumers use it. Confirm the WebSub hub endpoint and topic for each registry.
- [ ] [Gen2] Trusted-partner data sharing: on the consumer side, a connector pipeline pulls the data and ingests it into the registry. The WebSub pipeline template in the connector UI (`edrmc-websub-template.ts`) is configured and tested end to end.

## 8. DNS and TLS mapping

Fill the **Resolves to** and **TLS** columns on the call. Public hosts need public DNS and a public certificate. `*.openg2p.test` hosts go through host nginx with the `openg2p-private` allowlist, then the Istio `internal` gateway, using a cert from the OpenG2P Local CA.

| Service | Host (staging today; confirm for dev and the new layout) | Exposure | Resolves to | TLS | ✓ |
|---|---|---|---|---|---|
| Farmer staff portal (public) | `farmer-registry-development.oanstaging.com` | public | | | [ ] |
| Farmer staff portal (internal) | `staff-farmer-registry.far.openg2p.test` | private | | | [ ] |
| Livestock staff portal | `*-development.oanstaging.com` (confirm) | public | | | [ ] |
| Crop sown staff portal | `*-development.oanstaging.com` (confirm) | public | | | [ ] |
| Keycloak (public) | `keycloak-development.oanstaging.com` | public | | | [ ] |
| Keycloak (internal) | `keycloak.commons.openg2p.test` | private | | | [ ] |
| AWE | `awe.far.openg2p.test` → moves to `awe.commons.openg2p.test`? | private | | | [ ] |
| IAM staff UI | confirm | public/private | | | [ ] |
| Master Data API | in-cluster only (aliases) | none | | | [ ] |
| MinIO (pre-signed URLs) | `global.minioHost`: must be browser-resolvable | public | | | [ ] |
| ODK Central | `odk-central.oanstaging.com` / `odk-central-development.oanstaging.com` | public | | | [ ] |
| Connector UI (farmer) | `connector-farmer-registry.far.openg2p.test` | private | | | [ ] |
| Connector UI (live/crop) | confirm | private | | | [ ] |
| Dashboard API | `dashboard-api.far.openg2p.test` | private | | | [ ] |

DNS/TLS checks:
- [ ] Each host resolves (`dig +short <host>`) and serves the expected cert (`curl -vI https://<host>`).
- [ ] Wildcard records or explicit A/CNAMEs exist for `*.far`, `*.live`, `*.crop`, `*.commons` `.openg2p.test`.
- [ ] Keycloak client redirect URIs and cookie domain match the final public hostnames.
- [ ] `global.registryHostname` and the public staff UI host in live values match DNS. No placeholder `*.openg2p.org` hosts are left.
- [ ] Host nginx has `client_max_body_size 12m` on **every** portal that uploads files (farmer has it; livestock and crop don't yet).
- [ ] [Gen2] Clients that call the `*.openg2p.test` hosts have the Local CA certificate installed, so they get no SSL errors.
- [ ] The Local CA cert validity is recorded (expires 2036-08-07), and the CA is trusted by every in-cluster caller of `*.openg2p.test`.

## 9. Jenkins / CI

- [ ] The multibranch job builds every branch but deploys only `develop` (dev) and `staging`, on agent `vpn-agent2`.
- [ ] Credentials exist: `aws-ecr-creds`, `AWS_ACCOUNT_ID`, `gen2-dev-kubeconfig`, `staging-farmer-kubeconfig`.
- [ ] No chart-push / GitHub Pages / OCI credentials remain (decision #1, G2R-312).
- [ ] The deploy stage validates the local chart (`helm lint` + `helm template`) before upgrading.
- [ ] Standalone jobs exist: `ci/commons-services` (upgrade / seed-locations / migrate-far-geo) and `ci/connector`.
- [ ] Hook logs (db-seed, iam-register, sanity) are captured in the build log on failure.
- [ ] Crop staging still uses `kubectl set image` until its chart is proven on dev.
- [ ] [Gen2] The image flow is followed for every service: OpenG2P base release + our customisation → Jenkins build → ECR → image tag in Helm values → `helm upgrade` → pod. Dev uses the `develop` tag. Staging and UAT use the release version, bumped by hand in the Helm values.
- [ ] [Gen2] A new service (e.g. a tile server) is added to a namespace through a Helm chart in git, checked first with `helm template` and `helm upgrade --install ... --dry-run --debug`. It is not added with hand-applied deployment / service / virtual-service YAML.

## 10. End-to-end functional sign-off (per registry)

- [ ] Log in to the staff portal as `admin` through Keycloak.
- [ ] Create an intake manually with a photo and a land certificate up to 10 MB. Files upload and the photo renders (MinIO host is correct).
- [ ] Submit, approve in AWE, and see `approval_status = APPROVED` and `register_ingest_process_status = PROCESSED` within about a minute.
- [ ] AWE `webhook_delivery` has no failed rows.
- [ ] ODK path: submit from ODK Collect → connector worker log shows the poll and post → `incoming_classified_data` row → draft intake → approve → farmer is in the register.
- [ ] Partner API ingest with a signed request passes signature validation (pm-partner-api alias).
- [ ] Dashboard charts show the new farmer after the reporting-view refresh.

## 11. Rollback readiness

- [ ] Live values are backed up for `commons`, `commons-services`, `farmer-registry` and `farmer-connector`.
- [ ] `helm history` revision numbers to roll back to are recorded.
- [ ] Postgres backup/snapshot is taken before the move.
- [ ] sha-tagged images from the previous build are still in ECR.

---

References: `docs/deployment.md`, `docs/commons-services-upgrade.md`,
`docs/registry-platform-1.2.2-upgrade.md`, `ci/connector/README.md`,
`ci/k8s/commons-aliases.yaml`, Jira G2R-311 and sub-tasks G2R-313 to G2R-321.
