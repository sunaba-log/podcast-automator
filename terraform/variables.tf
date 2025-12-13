variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  default     = "asia-northeast1"
  description = "GCP Region"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment (dev, staging, prod)"
  validation {
    condition     = can(regex("^(dev|staging|prod)$", var.environment))
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "service_name" {
  type        = string
  default     = "podcast-processor"
  description = "Service name (used for resource naming)"
}

variable "input_bucket_name" {
  type        = string
  description = "GCS bucket name for input (mp3 files)"
}

variable "output_bucket_name" {
  type        = string
  description = "GCS bucket name for output"
}

variable "container_image" {
  type        = string
  description = "Container image URI for Cloud Run Jobs (e.g., gcr.io/project/image:tag)"
}

variable "cloudflare_api_token" {
  type        = string
  sensitive   = true
  description = "Cloudflare API token (read from tfvars or env var)"
  default     = ""
}

variable "cloudflare_account_id" {
  type        = string
  description = "Cloudflare Account ID"
  default     = ""
}
