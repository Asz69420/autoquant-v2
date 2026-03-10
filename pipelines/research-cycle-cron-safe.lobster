name: research-cycle-cron-safe
steps:
  - id: canonical-research-cycle
    command: 'openclaw lobster run --pipeline pipelines/research-cycle.lobster --cwd .'
