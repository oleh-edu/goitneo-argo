variable "project_name" {
  type        = string
  description = "Short name/prefix for resources"
  default     = "mlops-train"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "eu-central-1"
}

variable "aws_account_id" {
  type        = string
  description = "AWS account id"
  default     = ""
}

variable "lambda_timeout" {
  type    = number
  default = 30
}

variable "lambda_memory" {
  type    = number
  default = 128
}
