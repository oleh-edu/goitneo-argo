# IAM Role for all Lambda
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${local.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Validate Lambda
module "lambda_validate" {
  source        = "./modules/lambda_function"
  function_name = "validate"
  source_file   = "${path.module}/lambda/validate.py"
  handler       = "validate.handler"
  role_arn      = aws_iam_role.lambda_role.arn
  prefix        = local.name_prefix
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory
}

# Log Metrics Lambda
module "lambda_log_metrics" {
  source        = "./modules/lambda_function"
  function_name = "log-metrics"
  source_file   = "${path.module}/lambda/log_metrics.py"
  handler       = "log_metrics.handler"
  role_arn      = aws_iam_role.lambda_role.arn
  prefix        = local.name_prefix
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory
}
