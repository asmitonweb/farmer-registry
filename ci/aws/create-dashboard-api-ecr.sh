#!/usr/bin/env bash
# Create the ECR repository the Jenkinsfile pushes farmer-registry-dashboard-api
# to, and give it a lifecycle policy. Safe to re-run: an existing repository is
# left in place and only its scan setting and lifecycle policy are (re)applied.
#
#   ci/aws/create-dashboard-api-ecr.sh        # create / update
#   ci/aws/create-dashboard-api-ecr.sh -n     # dry run: print the commands only
#
# Needs AWS credentials allowed to manage ECR in the account (not the Jenkins
# push-only credential). Overridable from the environment:
#   AWS_REGION   default ap-south-1  (Jenkinsfile AWS_REGION)
#   REPO         default openg2p/farmer-registry/dashboard-api
#                (Jenkinsfile ECR_PATH + component name)
#   KEEP         default 50: commit-tagged images kept; older ones expire
#
# See docs/dashboard-api-deployment.md.
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
REPO="${REPO:-openg2p/farmer-registry/dashboard-api}"
KEEP="${KEEP:-50}"

DRY_RUN=false
case "${1:-}" in
  -n|--dry-run) DRY_RUN=true ;;
  -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  "") ;;
  *) echo "unknown argument: $1 (try -h)" >&2; exit 2 ;;
esac

run() {
  echo "+ $*"
  if ! $DRY_RUN; then "$@"; fi
}

# Rule priority matters: an image matched by a rule can never be expired by a
# lower-priority one. So the floating develop/staging tags are matched first by
# a rule that can never fire (only one image can carry each tag), which keeps
# them out of the count-based rule below it.
LIFECYCLE_POLICY=$(cat <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Never expire the image behind a floating branch tag",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": ["develop", "staging", "main"],
        "countType": "imageCountMoreThan",
        "countNumber": 3
      },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Expire untagged images after 7 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 7
      },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 3,
      "description": "Keep the last ${KEEP} commit-tagged images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": ${KEEP}
      },
      "action": { "type": "expire" }
    }
  ]
}
EOF
)

echo "Region: ${AWS_REGION}"
echo "Repository: ${REPO}"
$DRY_RUN && echo "(dry run: nothing is changed)"

if ! $DRY_RUN && aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$REPO" > /dev/null 2>&1; then
  echo "Repository exists; leaving it in place."
else
  # MUTABLE: CI re-pushes the floating :develop tag on every build.
  run aws ecr create-repository \
    --region "$AWS_REGION" \
    --repository-name "$REPO" \
    --image-tag-mutability MUTABLE \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256
fi

run aws ecr put-image-scanning-configuration \
  --region "$AWS_REGION" \
  --repository-name "$REPO" \
  --image-scanning-configuration scanOnPush=true

run aws ecr put-lifecycle-policy \
  --region "$AWS_REGION" \
  --repository-name "$REPO" \
  --lifecycle-policy-text "$LIFECYCLE_POLICY"

if ! $DRY_RUN; then
  URI=$(aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$REPO" \
    --query 'repositories[0].repositoryUri' --output text)
  echo "Ready: ${URI}"
fi
