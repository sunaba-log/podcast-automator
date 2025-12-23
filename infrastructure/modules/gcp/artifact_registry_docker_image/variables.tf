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
