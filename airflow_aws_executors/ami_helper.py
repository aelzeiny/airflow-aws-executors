"""
It turns out that the #1 source of grief is setting up AWS correctly.
This file will help folks debug their AWS Permissions
"""
import logging
import time
import unittest
from airflow_aws_executors.batch_executor import AwsBatchExecutor
from airflow.utils.state import State


class BatchAMIHelper(unittest.TestCase):
    def setUp(self):
        self._log = logging.getLogger("FargateAMIHelper")
        self.executor = AwsBatchExecutor()
        self.executor.start()

    def test_boto_submit_job(self):
        self.executor._submit_job(None, ['airflow', 'version'], None)

    def test_boto_describe_job(self):
        job_id = self.executor._submit_job(None, ['airflow', 'version'], None)
        self.executor._describe_tasks([job_id])

    def test_boto_terminate_job(self):
        job_id = self.executor._submit_job(None, ['airflow', 'version'], None)
        self.executor.batch.terminate_job(
            jobId=job_id,
            reason='Testing AMI permissions'
        )

    def test_sample_airflow_task(self):
        job_id = self.executor._submit_job(None, ['airflow', 'version'], None)
        job = None
        while job is None or job.get_job_state() == State.QUEUED:
            responses = self.executor._describe_tasks([job_id])
            assert responses, 'No response received'
            job = responses[0]
            time.sleep(1)

        self.assertEqual(job.get_job_state(), State.SUCCESS, 'AWS Batch Job did not run successfully!')

