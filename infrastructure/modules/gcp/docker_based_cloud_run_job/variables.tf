variable "project_id" {
  description = "GCP project id"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "environment" {
  description = "target environment"
  type        = string
}

variable "system" {
  description = "the system name used for creating resource identifiers"
  type        = string
}

variable "job_name" {
  description = "Cloud Run job name"
  type        = string
}

variable "service_account_email" {
  description = "service account email to run Cloud Run"
  type        = string
}

variable "image_name" {
  description = "container image name inside the repository"
  type        = string
}

variable "docker_context_path" {
  description = "the path where the docker build is to be executed"
  type        = string
}

variable "docker_build_command" {
  description = "the docker build command"
  type        = string
  default     = "make docker-build"
}

variable "docker_build_result_image_name" {
  description = "the resulting image name with tag from executing docker_build_command"
  type        = string
}

variable "image_keep_count" {
  description = "number of most recent image versions to keep"
  type        = number
  default     = 3
}

variable "timeout" {
  description = "Cloud Run request timeout duration (e.g., 300s)"
  type        = string
  default     = "900s"
}

variable "memory" {
  description = "Cloud Run container memory limit (e.g., 2Gi, 4Gi)"
  type        = string
  default     = "512Mi"
}

variable "cpu" {
  description = "Cloud Run container CPU limit (e.g., 1, 2, 4)"
  type        = string
  default     = "2"
}

variable "max_instance_count" {
  description = "Cloud Run max instances"
  type        = number
  default     = 1
}

variable "environment_variables" {
  description = "Environment variables for the Cloud Run container"
  type        = map(string)
  default     = {}
}
