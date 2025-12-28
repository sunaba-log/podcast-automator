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
}

variable "project_id" {
  type        = string
  description = "GCP project ID."
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


variable "discord_webhook_info_secret_name" {
  type        = string
  description = "Secret Manager secret name for Discord info webhook URL."
}

variable "discord_webhook_error_secret_name" {
  type        = string
  description = "Secret Manager secret name for Discord error webhook URL."
}

variable "cloudflare_account_id" {
  type        = string
  description = "Cloudflare account ID that owns the R2 bucket."
}

variable "cloudflare_zone_name" {
  type        = string
  description = "Cloudflare zone name (e.g., example.com) for the custom domain."
}

variable "r2_bucket_name" {
  type        = string
  description = "Cloudflare R2 bucket name for podcast assets."
}

variable "r2_subdomain" {
  type        = string
  description = "Subdomain part for the custom domain (e.g., dev.podcast-test)."
}
