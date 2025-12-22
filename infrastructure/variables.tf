variable "environment" {
  type        = string
  description = "Environment name (e.g., dev, prod)."

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be one of: dev, prod."
  }
}

variable "system" {
  type        = string
  description = "System name for default labels."
  default     = "podcast-automator"
}

variable "region" {
  type        = string
  description = "Default region for resources that require it."
  default     = "asia-northeast1"
}
