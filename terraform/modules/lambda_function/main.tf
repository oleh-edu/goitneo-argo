# Package source into .zip automatically
resource "null_resource" "package" {
  triggers = {
    src_hash = filesha256(var.source_file)
  }

  provisioner "local-exec" {
    command = "cd ${dirname(var.source_file)} && zip -j ${basename(replace(var.source_file, ".py", ".zip"))} ${basename(var.source_file)}"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.prefix}-${var.function_name}"
  retention_in_days = 14
}

# Lambda function
resource "aws_lambda_function" "this" {
  function_name    = "${var.prefix}-${var.function_name}"
  role             = var.role_arn
  handler          = var.handler
  runtime          = var.runtime
  filename         = replace(var.source_file, ".py", ".zip")
  source_code_hash = filebase64sha256(replace(var.source_file, ".py", ".zip"))
  timeout          = var.timeout
  memory_size      = var.memory_size

  depends_on = [
    aws_cloudwatch_log_group.this,
    null_resource.package
  ]
}

