# Parameters
REPO ?= oleh-edu/goitneo-argo

# ---------------------------
# Lambda packaging
# ---------------------------
build-lambda:
	cd terraform/lambda && \
	zip -j validate.zip validate.py && \
	zip -j log_metrics.zip log_metrics.py

# ---------------------------
# Terraform
# ---------------------------
init:
	cd terraform && terraform init

apply:
	cd terraform && terraform apply

plan:
	cd terraform && terraform plan

# ---------------------------
# Sync Terraform outputs -> GitHub Secrets
# ---------------------------
sync-secrets:
	@echo "🔑 Syncing Terraform outputs into GitHub Secrets for $(REPO)"
	@cd terraform && \
	OUTPUTS=$$(terraform output -json) && \
	STATE_MACHINE_ARN=$$(echo $$OUTPUTS | jq -r .state_machine_arn.value) && \
	GITHUB_ROLE_ARN=$$(echo $$OUTPUTS | jq -r .github_actions_role_arn.value) && \
	gh secret set STATE_MACHINE_ARN --body "$$STATE_MACHINE_ARN" --repo "$(REPO)" && \
	gh secret set AWS_ROLE_TO_ASSUME --body "$$GITHUB_ROLE_ARN" --repo "$(REPO)" && \
	echo "✅ Secrets updated in GitHub: STATE_MACHINE_ARN, AWS_ROLE_TO_ASSUME"

# ---------------------------
# All-in-one pipeline
# ---------------------------
deploy: build-lambda init apply sync-secrets

# ---------------------------
# Destroy infrastructure + cleanup GitHub Secrets
# ---------------------------
destroy:
	cd terraform && terraform destroy -auto-approve
	@echo "🗑️ Cleaning GitHub secrets for $(REPO)"
	-gh secret remove STATE_MACHINE_ARN --repo "$(REPO)" || true
	-gh secret remove AWS_ROLE_TO_ASSUME --repo "$(REPO)" || true
	@echo "✅ Infrastructure destroyed and secrets removed"

# ---------------------------
# Reset infrastructure (destroy + deploy)
# ---------------------------
reset: destroy deploy
	@echo "🔄 Infrastructure reset completed"
