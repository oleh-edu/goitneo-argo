#!/usr/bin/env bash
set -euo pipefail

# Repository in ORG/REPO format
REPO="oleh-edu/goitneo-argo"

# Receive outputs in JSON
OUTPUTS=$(terraform -chdir=terraform output -json)

# Get values from outputs
STATE_MACHINE_ARN=$(echo "$OUTPUTS" | jq -r .state_machine_arn.value)
GITHUB_ROLE_ARN=$(echo "$OUTPUTS" | jq -r .github_actions_role_arn.value)

# Write it down in GitHub Secrets
gh secret set STATE_MACHINE_ARN --body "$STATE_MACHINE_ARN" --repo "$REPO"
gh secret set AWS_ROLE_TO_ASSUME --body "$GITHUB_ROLE_ARN" --repo "$REPO"

echo "✅ Secrets updated at $REPO"
