module "docker_image" {
  source = "../artifact_registry_docker_image"

  project_id                     = var.project_id
  region                         = var.region
  environment                    = var.environment
  system                         = var.system
  image_name                     = var.image_name
  docker_context_path            = var.docker_context_path
  docker_build_command           = var.docker_build_command
  docker_build_result_image_name = var.docker_build_result_image_name
  image_keep_count               = var.image_keep_count
}
