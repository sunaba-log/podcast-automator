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

variable "input_retention_days" {
  type        = number
  description = "Days to retain input audio objects before deletion. Omit or set null to disable lifecycle deletion."
  default     = null

  validation {
    condition     = var.input_retention_days == null || var.input_retention_days > 0
    error_message = "input_retention_days must be null (disabled) or a positive number."
  }
}

variable "input_bucket_force_destroy" {
  type        = bool
  description = "Allow Terraform to delete the input bucket even if it contains objects."
  default     = false
}

variable "function_timeout_seconds" {
  type        = number
  description = "Function timeout in seconds."
  default     = 540
}

variable "function_available_memory_gib" {
  type        = string
  description = "Function available memory in GiB (e.g., 2Gi, 4Gi)."
  default     = "16Gi"
}

variable "function_max_instance_count" {
  type        = number
  description = "Max instances for the function."
  default     = 1
}

variable "discord_webhook_info_secret_name" {
  type        = string
  description = "Secret Manager secret name for Discord info webhook URL."
}

variable "discord_webhook_error_secret_name" {
  type        = string
  description = "Secret Manager secret name for Discord error webhook URL."
}
