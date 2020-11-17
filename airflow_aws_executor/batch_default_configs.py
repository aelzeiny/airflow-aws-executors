from airflow.configuration import conf


DEFAULT_BATCH_KWARGS = {
    'jobName': conf.get('batch', 'job_name'),
    'jobQueue': conf.get('batch', 'job_queue'),
    'jobDefinition': conf.get('batch', 'job_definition'),
    'containerOverrides': {
        'command': []
    }
}
