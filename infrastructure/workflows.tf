resource "google_workflows_workflow" "main" {
  name            = lower("${var.system}-main-${var.environment}")
  region          = var.region
  service_account = local.default_compute_service_account

  source_contents = <<-YAML
  main:
    params: [event]
    steps:
      - init:
          assign:
            - project: ${local.project_id}
            - region: ${var.region}
            - job: ${module.cloud_run_job.job_name}
      - runJob:
          call: googleapis.run.v2.projects.locations.jobs.run
          args:
            name: $${"projects/" + project + "/locations/" + region + "/jobs/" + job}
          result: jobExecution
      - done:
          return: $${jobExecution}
  YAML
}
