resource "google_workflows_workflow" "main" {
  name                = lower("${var.system}-${var.environment}")
  region              = var.region
  service_account     = local.default_compute_service_account
  deletion_protection = false

  source_contents = <<-YAML
  main:
    params: [event]
    steps:
      - init:
          assign:
            - project: ${var.project_id}
            - region: ${var.region}
            - job: ${module.cloud_run_job.job_name}
      - skipFolderPlaceholder:
          switch:
            - condition: '$${text.match_regex(default(event.data.name, ""), "/$")}'
              return: '$${"Skipped folder placeholder: " + event.data.name}'
      - runJob:
          call: googleapis.run.v2.projects.locations.jobs.run
          args:
            name: $${"projects/" + project + "/locations/" + region + "/jobs/" + job}
            body:
              overrides:
                containerOverrides:
                  - env:
                      - name: "GCS_TRIGGER_OBJECT_NAME"
                        value: $${event.data.name}
          result: jobExecution
      - done:
          return: $${jobExecution}
  YAML
}
