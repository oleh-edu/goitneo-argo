# MLOps Train Automation with AWS Step Functions, Lambda, and GitHub Actions

This repository provisions an automated training pipeline on AWS using **Terraform**.  
The pipeline includes:

- Two Lambda functions (`ValidateData` → `LogMetrics`)  
- AWS Step Functions state machine to orchestrate them  
- IAM roles for Lambda, Step Functions, and GitHub Actions OIDC  
- Makefile and sync script for easier deployment  
- GitHub Actions workflows to trigger executions, destroy, or reset infra  

---

## 📂 Project Structure

```bash
.
├── Makefile                         # Build, deploy, destroy, reset
├── sync-secrets.sh                  # Script to sync Terraform outputs with GitHub secrets
├── terraform/
│   ├── main.tf                      # Provider and locals
│   ├── variables.tf                 # Input variables
│   ├── outputs.tf                   # Outputs (ARNs)
│   ├── oidc.tf                      # GitHub OIDC provider
│   ├── github_actions.tf            # IAM role for GitHub Actions
│   ├── lambda.tf                    # Lambda role and modules
│   ├── stepfunctions.tf             # Step Function definition
│   ├── lambda/
│   │   ├── validate.py              # Lambda: validation logic
│   │   ├── log_metrics.py           # Lambda: metrics logging logic
│   │   ├── validate.zip             # Auto-built package
│   │   └── log_metrics.zip          # Auto-built package
│   └── modules/
│       └── lambda_function/         # Reusable Lambda module
│           ├── main.tf
│           ├── variables.tf
│           └── outputs.tf
└── .github/
    └── workflows/
        ├── train.yml                # Trigger Step Function on push
        ├── destroy.yml              # Destroy infra + clean secrets
        └── reset.yml                # Reset infra (destroy + deploy)
```

---

## 🔑 Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.6  
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)  
- [GitHub CLI](https://cli.github.com/) (`gh`)  
- [jq](https://stedolan.github.io/jq/) for JSON parsing  
- AWS account with access to IAM, Lambda, Step Functions, CloudWatch  

---

## 🚀 Deployment Workflow

### 1. Build and Deploy with Makefile

```bash
# Initialize Terraform
make init

# Apply changes
make apply

# Build Lambda zip archives
make build-lambda

# Sync Terraform outputs into GitHub secrets
make REPO=my-org/my-repo sync-secrets

# All-in-one command
make REPO=my-org/my-repo deploy
```

---

### 2. Terraform Outputs

After `terraform apply`, you will see outputs like:

```bash
Outputs:

state_machine_arn        = arn:aws:states:eu-central-1:123456789012:stateMachine:mlops-train-train-pipeline
lambda_validate_arn      = arn:aws:lambda:eu-central-1:123456789012:function:mlops-train-validate
lambda_log_metrics_arn   = arn:aws:lambda:eu-central-1:123456789012:function:mlops-train-log-metrics
github_actions_role_arn  = arn:aws:iam::123456789012:role/mlops-train-github-actions-role
```

---

### 3. Sync Terraform Outputs into GitHub Secrets

You can set repository secrets either with the **Makefile** or the **script**.

#### Option A: Makefile

```bash
make REPO=my-org/my-repo sync-secrets
```

#### Option B: Script

```bash
./sync-secrets.sh
```

Secrets created in GitHub repository:

- `STATE_MACHINE_ARN`
- `AWS_ROLE_TO_ASSUME`

---

## 🤖 GitHub Actions Workflows

### 1. Train Workflow

File: `.github/workflows/train.yml`  
Triggered on push to `main`, `master`, or `develop`.

It executes the Step Function:

```yaml
- name: Run Step Function
  run: |
    aws stepfunctions start-execution \\
      --state-machine-arn ${{ secrets.STATE_MACHINE_ARN }} \\
      --name "train-$(date +%s)" \\
      --input "{\\"source\\":\\"github-actions\\", \\"commit\\":\\"${GITHUB_SHA::7}\\"}"
```

---

### 2. Destroy Workflow

File: `.github/workflows/destroy.yml`  
Manually triggered (`workflow_dispatch`).  

It runs `terraform destroy` and removes GitHub secrets:

- `STATE_MACHINE_ARN`
- `AWS_ROLE_TO_ASSUME`

---

### 3. Reset Workflow

File: `.github/workflows/reset.yml`  
Manually triggered (`workflow_dispatch`).  

It runs:

1. `terraform destroy`
2. Removes GitHub secrets
3. `terraform apply`
4. Syncs new outputs back to secrets  

---

## 🧪 Manual Test

To run the Step Function manually:

```bash
aws stepfunctions start-execution \\
  --state-machine-arn <STATE_MACHINE_ARN> \\
  --name "train-$(date +%s)" \\
  --input '{"source":"manual-cli","note":"test run"}'
```

Or use AWS Console → Step Functions → **Start Execution**.

---

## 📝 Example Input JSON

```json
{
  "source": "github-actions",
  "commit": "abc1234"
}
```

---

## ✅ Key Features

- Modular Terraform setup (`modules/lambda_function`)  
- Automatic Lambda packaging into `.zip` with `null_resource`  
- Step Function orchestration of two stages (Validate → LogMetrics)  
- IAM integration with GitHub Actions via OIDC  
- Makefile automation for build, deploy, destroy, reset  
- GitHub Actions workflows for CI/CD, teardown, and reset  

---

⚠️ **Warning**: `make destroy` and `make reset` permanently remove infrastructure and secrets. Use carefully.
