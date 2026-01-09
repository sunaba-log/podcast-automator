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

variable "org" {
  type        = string
  description = "Organization name for default labels."
  default     = "sunabalog"
}

variable "project_id" {
  type        = string
  description = "Google Cloud project ID."
}

variable "region" {
  type        = string
  description = "Default region for resources that require it."
  default     = "asia-northeast1"
}

variable "gcs_retention_days" {
  type        = number
  description = "Days to retain input audio objects before deletion. Omit or set null to disable lifecycle deletion."
  default     = null

  validation {
    condition     = var.gcs_retention_days == null || var.gcs_retention_days > 0
    error_message = "gcs_retention_days must be null (disabled) or a positive number."
  }
}

variable "gcs_force_destroy" {
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

variable "cloudflare_access_key_id_secret_name" {
  type        = string
  description = "Secret Manager secret name for Cloudflare R2 access key id."
  default     = "cloudflare-access-key-id"
}

variable "cloudflare_secret_access_key_secret_name" {
  type        = string
  description = "Secret Manager secret name for Cloudflare R2 secret access key."
  default     = "cloudflare-secret-access-key"
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

variable "r2_key_prefix" {
  type        = string
  description = "Key prefix in the R2 bucket for uploaded files (empty for root)."
  default     = "sunabalog"
}

variable "r2_subdomain" {
  type        = string
  description = "Subdomain part for the custom domain (e.g., dev.podcast)."
}
