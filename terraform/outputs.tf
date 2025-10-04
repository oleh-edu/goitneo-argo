output "state_machine_arn" {
  value       = aws_sfn_state_machine.train_pipeline.arn
  description = "ARN of the Step Function state machine"
}

output "lambda_validate_arn" {
  value       = module.lambda_validate.arn
  description = "ARN of the Validate Lambda"
}

output "lambda_log_metrics_arn" {
  value       = module.lambda_log_metrics.arn
  description = "ARN of the LogMetrics Lambda"
}

output "github_actions_role_arn" {
  value       = aws_iam_role.github_actions_role.arn
  description = "IAM Role ARN for GitHub Actions OIDC (use in workflow as role-to-assume)"
}
