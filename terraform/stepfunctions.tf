# ---------------------------
# IAM Role for Step Functions
# ---------------------------
data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "sfn_policy" {
  statement {
    sid     = "InvokeLambda"
    effect  = "Allow"
    actions = ["lambda:InvokeFunction"]
    resources = [
      module.lambda_validate.arn,
      module.lambda_log_metrics.arn
    ]
  }

  statement {
    sid     = "Logs"
    effect  = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "sfn_role" {
  name               = "${local.name_prefix}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

resource "aws_iam_policy" "sfn_policy" {
  name   = "${local.name_prefix}-sfn-policy"
  policy = data.aws_iam_policy_document.sfn_policy.json
}

resource "aws_iam_role_policy_attachment" "sfn_attach" {
  role       = aws_iam_role.sfn_role.name
  policy_arn = aws_iam_policy.sfn_policy.arn
}

# ---------------------------
# Step Function definition
# ---------------------------
locals {
  sfn_definition = jsonencode({
    Comment = "Training pipeline: ValidateData -> LogMetrics"
    StartAt = "ValidateData"
    States = {
      ValidateData = {
        Type       = "Task"
        Resource   = module.lambda_validate.arn
        ResultPath = "$.validate_result"
        Next       = "LogMetrics"
      }
      LogMetrics = {
        Type       = "Task"
        Resource   = module.lambda_log_metrics.arn
        ResultPath = "$.log_metrics_result"
        End        = true
      }
    }
  })
}

resource "aws_sfn_state_machine" "train_pipeline" {
  name     = "${local.name_prefix}-train-pipeline"
  role_arn = aws_iam_role.sfn_role.arn
  definition = local.sfn_definition

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"
  }
}
