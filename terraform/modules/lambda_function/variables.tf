variable "function_name" {
  type        = string
  description = "Lambda function name (without prefix)"
}

variable "source_file" {
  type        = string
  description = "Path to .py file"
}

variable "handler" {
  type        = string
  description = "Handler entrypoint (e.g., validate.handler)"
}

variable "runtime" {
  type        = string
  default     = "python3.12"
}

variable "timeout" {
  type    = number
  default = 30
}

variable "memory_size" {
  type    = number
  default = 128
}

variable "role_arn" {
  type        = string
  description = "IAM role ARN for Lambda"
}

variable "prefix" {
  type        = string
  description = "Prefix for names (e.g., project)"
}

