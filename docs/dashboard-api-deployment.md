# Dashboard API — CI/CD and AWS setup

How `farmer-registry-dashboard-api` is built and deployed by this repo's
pipeline, and the one-time AWS and Jenkins steps it needs. Read alongside
[deployment.md](deployment.md), which covers the registry pipeline as a whole.

| | |
| --- | --- |
| Source | <https://github.com/Centre-for-Open-Societal-Systems/farmer-registry-dashboard-api> (public) |
| What it is | Read-only FastAPI service: aggregate chart data for the OAN dashboards BFF |
| Image | `${AWS_ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com/openg2p/farmer-registry/dashboard-api` |
| Deployed as | Deployment + ClusterIP Service `farmer-registry-dashboard-api` in `far`, part of the `farmer-registry` Helm release |
| Chart | `helm/openg2p-farmer-registry/templates/dashboard-api.yaml`, values `dashboardApi.*` |
| Reads | `fr_rpt_farmer`, `fr_rpt_land` in `farmer_registry` on `commons-postgresql` |

---

## 1. How it flows

```
 dashboard-api repo                      farmer-registry repo (this one)
 (develop / staging / main)              push to develop / staging
            │                                        │
            │   git clone --depth 1 <same branch>    ▼
            └──────────────────────────────► Jenkins multibranch job (Jenkinsfile)
                                               ├─ Checkout dashboard-api  → .build/dashboard-api
                                               ├─ ECR Login               (aws-ecr-creds)
                                               ├─ Build & Push            → ECR …/dashboard-api:<sha12>, :develop
                                               └─ Deploy (far namespace)  (vpn-agent2)
                                                    helm upgrade farmer-registry
                                                      dashboardApi.enabled=true, image=<sha12>
                                                      analytics.reportingViews.enabled=true
                                                    rollout status deploy/farmer-registry-dashboard-api
                                                                │
                           EC2 RKE2 cluster, namespace far      ▼
     OAN dashboards BFF ──HTTP──► svc/farmer-registry-dashboard-api:80 ──► commons-postgresql
                                                                        (fr_rpt_* views)
```

### Branch mapping

| farmer-registry branch | dashboard-api branch built | Deployed to |
| --- | --- | --- |
| `develop` | `develop` | dev (`gen2-dev-kubeconfig`) |
| `staging` | `staging` | staging (`staging-farmer-kubeconfig`) |
| any other branch / PR | the same-named branch if it exists, else `develop` | nowhere (build and push only) |

To pin a specific branch or tag instead, set the environment variable
`DASHBOARD_API_REF` on the Jenkins job (or folder). The build log prints what was
used: `dashboard-api: <ref> @ <sha12>`, and the image carries it as the labels
`org.opencontainers.image.revision` / `…ref.name`.

**Order of merges.** The dashboard-api branch a build clones must already hold
the service (its `Dockerfile`); otherwise the *Checkout dashboard-api* stage
fails with `dashboard-api <branch> has no Dockerfile`. Merge the service into the
dashboard-api repository's `develop` (and `staging`) **before** this pipeline
change reaches farmer-registry `develop` (and `staging`).

**A push to the dashboard-api repository does not deploy on its own.** It is
picked up by the next farmer-registry build of the matching branch. After merging
there, re-run the farmer-registry job for that branch (*Build Now*), or see §6.

---

## 2. AWS: create the ECR repository (once per account)

The pipeline pushes to `openg2p/farmer-registry/<component>`, so this service's
repository is **`openg2p/farmer-registry/dashboard-api`**, in the same account
(`AWS_ACCOUNT_ID` on the Jenkins job) and region (**ap-south-1**) as the others.
Until it exists every build fails at the push with
`name unknown: The repository with name 'openg2p/farmer-registry/dashboard-api'
does not exist`.

### Option A — script (recommended)

With AWS credentials that may manage ECR (an admin/DevOps profile, not the
Jenkins push credential):

```sh
aws sts get-caller-identity                        # confirm the account
ci/aws/create-dashboard-api-ecr.sh -n              # dry run: shows the commands
ci/aws/create-dashboard-api-ecr.sh                 # create + lifecycle policy
```

It is idempotent. It creates the repository with scan-on-push, mutable tags (CI
re-pushes `:develop` on every build) and AES256 encryption, then applies a
lifecycle policy:

1. images tagged `develop`, `staging` or `main` are never expired;
2. untagged images expire after 7 days;
3. beyond that, the last 50 images are kept (`KEEP=` to change).

### Option B — AWS Console

1. **Amazon ECR → Private registry → Repositories → Create repository**, region
   **Asia Pacific (Mumbai) ap-south-1**.
2. Visibility **Private**. Name: `openg2p/farmer-registry/dashboard-api`.
3. Tag immutability: **Mutable**. Image scan settings: **Scan on push** on.
   Encryption: AES-256. **Create**.
4. Open the repository → **Lifecycle policy → Create rule**, and add the three
   rules above in that order (priority 1, 2, 3). Rule 1: *Image status* tagged,
   *Tag patterns* `develop`, `staging`, `main`, *Count type* "Image count more
   than" 3. Rule 2: untagged, "Since image pushed" 7 days. Rule 3: any, "Image
   count more than" 50.

### Check

```sh
aws ecr describe-repositories --region ap-south-1 \
  --repository-names openg2p/farmer-registry/dashboard-api \
  --query 'repositories[0].[repositoryUri,imageTagMutability]' --output text
```

---

## 3. AWS: IAM for Jenkins (push)

Jenkins logs in and pushes with the credential **`aws-ecr-creds`** (an AWS
access key bound with `AmazonWebServicesCredentialsBinding`). Find the IAM user
behind it (IAM → Users → Security credentials → match the access key ID shown in
Jenkins → Manage Credentials) and look at its policies:

* If it already allows the ECR push actions on
  `…:repository/openg2p/farmer-registry/*` (or `*`), **nothing to do**.
* If it lists repositories by name, add the new one, or replace the list with the
  wildcard. A ready-to-attach policy (replace `<ACCOUNT_ID>`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EcrLogin",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "FarmerRegistryPush",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "arn:aws:ecr:ap-south-1:<ACCOUNT_ID>:repository/openg2p/farmer-registry/*"
    }
  ]
}
```

A push denied here shows in the build as `denied: User: arn:aws:iam::…:user/…
is not authorized to perform: ecr:InitiateLayerUpload`.

---

## 4. AWS: image pulls on the EC2 cluster nodes

The dev and staging RKE2 nodes already pull the other
`openg2p/farmer-registry/*` images, so whatever gives them that access (usually
the EC2 **instance profile** with `AmazonEC2ContainerRegistryReadOnly`, or an
ECR credential provider / registry config in `/etc/rancher/rke2/registries.yaml`)
covers the new repository too — **unless** it is scoped to named repositories.
Check once:

* EC2 → the node instances → *IAM role* → its policies. `AmazonEC2ContainerRegistryReadOnly`
  or a `…/openg2p/farmer-registry/*` resource is fine; a list of named
  repositories needs `openg2p/farmer-registry/dashboard-api` added.
* After the first deploy, `kubectl -n far get pods -l app.kubernetes.io/component=dashboard-api`
  must not show `ErrImagePull` / `ImagePullBackOff`.

No security-group change is needed: the service is only reached from inside the
cluster.

---

## 5. Jenkins

Nothing new to create. The pipeline reuses:

| What | Used for |
| --- | --- |
| multibranch job on this repo, `Jenkinsfile` | builds and deploys (unchanged) |
| env `AWS_ACCOUNT_ID` | ECR registry host |
| credential `aws-ecr-creds` | ECR login and push (§3) |
| credentials `gen2-dev-kubeconfig`, `staging-farmer-kubeconfig` | Helm deploy (unchanged) |

The dashboard-api repository is public, so the clone needs no credential. The
build agents need `git` and outbound HTTPS to `github.com` (they already clone
this repo). If the repository is ever made private, add a GitHub credential and
wrap the clone in the *Checkout dashboard-api* stage with `withCredentials`.

After this change is merged: open the job → **Scan Multibranch Pipeline Now**
(or push to `develop`), and watch the new stages:

* `Checkout dashboard-api` → `dashboard-api: develop @ <sha>`
* `Build & Push` → `docker push …/dashboard-api:<sha12>`
* `Deploy (far namespace)` → `deployment "farmer-registry-dashboard-api" successfully rolled out`
  and `=== reporting-views Job outcome ===`.

Optional pin: *Configure → Properties → Environment variables* (or the folder),
`DASHBOARD_API_REF=<branch or tag>`. Remove it to go back to branch mapping.

---

## 6. Database and reporting views

* **Credentials.** The pod uses the registry's own database user: `DATABASE_URL`
  is assembled from `global.registryDBUser`, `global.postgresqlHost` and the
  password in Secret `farmer-registry` / key `farmer-registry-db-user` — the same
  wiring the analytics jobs use. Nothing to create. (A dedicated read-only role is
  a later hardening step; see the service's `docs/configuration.md`.)
* **Views.** The CI deploy now enables `analytics.reportingViews`: the
  post-upgrade Job `farmer-registry-fr-reporting-views` (hook weight 45) creates
  `fr_rpt_*`, and the CronJob `farmer-registry-fr-reporting-views-refresh`
  refreshes them hourly. It reads the geo hierarchy from Master Data with Secret
  `master-data` / key `master-data-db-user`, which commons-services provides in
  `far`. Bulk sample data, Superset dashboards and maps content stay off.
* **Freshness.** A chart can lag the register by up to the refresh interval plus
  the BFF cache TTL (15 min by default).

---

## 7. Wiring the dashboards

Point the OAN dashboards BFF at the Service (in-cluster):

```ini
FARMER_REGISTRY_DASHBOARD_API_URL=http://farmer-registry-dashboard-api.far
```

There is deliberately no Ingress: the service has no authentication. If the
dashboards run outside the cluster, expose it through a private route (internal
load balancer, VPN) rather than the public ingress.

Tunables live under `dashboardApi.*` in the release values (`helm get values`
keeps them across CI deploys): `workers` (default 2, each holding 10 DB
connections), `replicas`, `geoLevelTotals` (e.g. `{regions: 13, woredas: 1138}`
for coverage rates), `allowedOrigins`, `env`, `resources`.

---

## 8. Verify

```sh
NS=far
kubectl -n $NS get deploy,svc farmer-registry-dashboard-api
kubectl -n $NS get job farmer-registry-fr-reporting-views
kubectl -n $NS get cronjob farmer-registry-fr-reporting-views-refresh

# Image running matches the build
kubectl -n $NS get deploy farmer-registry-dashboard-api \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

# From inside the cluster
kubectl -n $NS run dash-curl --rm -it --restart=Never --image=curlimages/curl -- \
  sh -c 'curl -s http://farmer-registry-dashboard-api/health; echo;
         curl -s "http://farmer-registry-dashboard-api/api/v1/charts/farmerKpis"; echo'

# From a workstation
kubectl -n $NS port-forward svc/farmer-registry-dashboard-api 8005:80
# then http://localhost:8005/docs
```

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Push fails: `repository … does not exist` | ECR repository not created | §2 |
| Push fails: `not authorized to perform: ecr:…` | `aws-ecr-creds` policy scoped to other repositories | §3 |
| `Checkout dashboard-api` fails: `… has no Dockerfile` | That dashboard-api branch does not hold the service yet | Merge it there first (§1), or set `DASHBOARD_API_REF` |
| `Checkout dashboard-api` fails: `Remote branch … not found` | `DASHBOARD_API_REF` names a branch/tag that does not exist | Fix or remove the override |
| Pod `ErrImagePull` / `ImagePullBackOff` | Node role cannot pull the new repository | §4 |
| Helm fails on `farmer-registry-fr-reporting-views` | View creation failed (logs are printed by the deploy stage) | `kubectl -n far logs job/farmer-registry-fr-reporting-views` |
| Pod not Ready, `/health` 500 | Database unreachable or wrong credentials | `kubectl -n far logs deploy/farmer-registry-dashboard-api`; check Secret `farmer-registry` |
| Charts 500: `relation "fr_rpt_farmer" does not exist` | Reporting views not created | Check the views Job; `analytics.reportingViews.enabled` must be true |
| Charts all zero | Views empty or not refreshed | `kubectl -n far create job --from=cronjob/farmer-registry-fr-reporting-views-refresh refresh-now` |
| New dashboard-api code not deployed | Pushes there do not trigger this pipeline | Rebuild the farmer-registry branch (§1) |

## 10. Rollback

The service is part of the `farmer-registry` release, so `helm rollback
farmer-registry <rev> -n far` rolls it back with everything else. To take it out
alone, set `dashboardApi.enabled: false` in the Jenkinsfile's CI values and
deploy.
