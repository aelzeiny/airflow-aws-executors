import datetime as dt
from unittest import TestCase, mock

from airflow_aws_executor.batch_plugin import (
    AwsBatchExecutor, BatchJobDetailSchema, BatchJob, BatchJobCollection
)
from airflow.utils.state import State

from .botocore_helper import get_botocore_model, assert_botocore_call


class TestBatchCollection(TestCase):
    """Tests EcsTaskCollection Class"""
    def test_get_and_add(self):
        """Test add_task, task_by_arn, cmd_by_key"""
        self.assertEqual(len(self.collection), 2)

    def test_list(self):
        """Test get_all_arns() and get_all_task_keys()"""
        # Check basic list by ARNs & airflow-task-keys
        self.assertListEqual(self.collection.get_all_jobs(), [self.first_job_id, self.second_job_id])

    def test_pop(self):
        """Test pop_by_key()"""
        # pop first task & ensure that it's removed
        self.assertEqual(self.collection.pop_by_id(self.first_job_id), self.first_airflow_key)
        self.assertEqual(len(self.collection), 1)
        self.assertListEqual(self.collection.get_all_jobs(), [self.second_job_id])

    def setUp(self):
        """
        Create a ECS Task Collection and add 2 airflow tasks. Populates self.collection,
        self.first/second_task, self.first/second_airflow_key, and self.first/second_airflow_cmd.
        """
        self.collection = BatchJobCollection()
        # Add first task
        self.first_job_id = '001'
        self.first_airflow_key = mock.Mock(spec=tuple)
        self.collection.add_job(self.first_job_id, self.first_airflow_key)
        # Add second task
        self.second_job_id = '002'
        self.second_airflow_key = mock.Mock(spec=tuple)
        self.collection.add_job(self.second_job_id, self.second_airflow_key)


class TestBatchJob(TestCase):
    """Tests the EcsFargateTask DTO"""
    def test_queued_tasks(self):
        """Tasks that are pending launch identified as 'queued'"""
        for status in self.all_statuses:
            if status not in (self.success, self.failed, self.running):
                job = BatchJob('id', status)
                self.assertNotIn(job.get_job_state(), (State.RUNNING, State.FAILED, State.SUCCESS))

    def test_running_jobs(self):
        """Tasks that have been launched are identified as 'running'"""
        assert self.running in self.all_statuses, 'A core assumption in the Batch Executor has changed. ' \
                                                  'What happened to the list of statuses or the running state?'
        running_job = BatchJob('AAA', self.running)
        self.assertEqual(running_job.get_job_state(), State.RUNNING)

    def test_success_jobs(self):
        """Tasks that have been launched are identified as 'running'"""
        assert self.success in self.all_statuses, 'A core assumption in the Batch Executor has changed. ' \
                                                  'What happened to the list of statuses or the running state?'
        success_job = BatchJob('BBB', self.success)
        self.assertEqual(success_job.get_job_state(), State.SUCCESS)

    def test_failed_jobs(self):
        """Tasks that have been launched are identified as 'running'"""
        assert self.failed in self.all_statuses, 'A core assumption in the Batch Executor has changed. ' \
                                                 'What happened to the list of statuses or the running state?'
        running_job = BatchJob('CCC', self.failed)
        self.assertEqual(running_job.get_job_state(), State.FAILED)

    def setUp(self):
        batch_model = get_botocore_model('batch')
        self.all_statuses = batch_model['shapes']['JobStatus']['enum']
        self.running = 'RUNNING'
        self.success = 'SUCCEEDED'
        self.failed = 'FAILED'


# class TestAwsBatchExecutor(TestCase):
#     """Tests the AWS Batch Executor itself"""
#     def test_execute(self):
#         """Test execution from end-to-end"""
#         airflow_key = mock.Mock(spec=tuple)
#         airflow_cmd = mock.Mock(spec=list)
#
#         self.executor.ecs.run_task.return_value = {
#             'tasks': [{
#                 'taskArn': '001',
#                 'lastStatus': '',
#                 'desiredStatus': '',
#                 'containers': [{'name': 'some-ecs-container'}]}
#             ],
#             'failures': []
#         }
#
#         self.assertEqual(0, len(self.executor.pending_tasks))
#         self.executor.execute_async(airflow_key, airflow_cmd)
#         self.assertEqual(1, len(self.executor.pending_tasks))
#
#         self.executor.attempt_task_runs()
#
#         # ensure that run_task is called correctly as defined by Botocore docs
#         self.executor.ecs.run_task.assert_called_once()
#         self.assert_botocore_call('RunTask', *self.executor.ecs.run_task.call_args)
#
#         # task is stored in active worker
#         self.assertEqual(1, len(self.executor.active_workers))
#         self.assertIn(self.executor.active_workers.task_by_key(airflow_key).task_arn, '001')
#
#     def test_failed_execute_api(self):
#         """Test what happens when FARGATE refuses to execute a task"""
#         self.executor.ecs.run_task.return_value = {
#             'tasks': [],
#             'failures': [{
#                 'arn': '001',
#                 'reason': 'Sample Failure',
#                 'detail': 'UnitTest Failure - Please ignore'
#             }]
#         }
#
#         airflow_key = mock.Mock(spec=tuple)
#         airflow_cmd = mock.Mock(spec=list)
#         self.executor.execute_async(airflow_key, airflow_cmd)
#
#         # no matter what, don't schedule until run_task becomes successful
#         for _ in range(self.executor.MAX_FAILURE_CHECKS * 2):
#             self.executor.attempt_task_runs()
#             # task is not stored in active workers
#             self.assertEqual(len(self.executor.active_workers), 0)
#
#     @mock.patch('airflow.executors.base_executor.BaseExecutor.fail')
#     @mock.patch('airflow.executors.base_executor.BaseExecutor.success')
#     def test_sync(self, success_mock, fail_mock):
#         """Test synch from end-to-end"""
#         after_fargate_json = self.__mock_sync()
#         loaded_fargate_json = BotoTaskSchema().load(after_fargate_json)
#         self.assertFalse(loaded_fargate_json.errors, msg='Mocked message is not like defined schema')
#         self.assertEqual(State.SUCCESS, loaded_fargate_json.data.get_task_state())
#
#         self.executor.sync_running_tasks()
#
#         # ensure that run_task is called correctly as defined by Botocore docs
#         self.executor.ecs.describe_tasks.assert_called_once()
#         self.assert_botocore_call('DescribeTasks', *self.executor.ecs.describe_tasks.call_args)
#
#         # task is not stored in active workers
#         self.assertEqual(len(self.executor.active_workers), 0)
#         # Task is immediately succeeded
#         success_mock.assert_called_once()
#         self.assertFalse(fail_mock.called)
#
#     @mock.patch('airflow.executors.base_executor.BaseExecutor.fail')
#     @mock.patch('airflow.executors.base_executor.BaseExecutor.success')
#     def test_failed_sync(self, success_mock, fail_mock):
#         """Test success and failure states"""
#         after_fargate_json = self.__mock_sync()
#
#         # set container's exit code to failure
#         after_fargate_json['containers'][0]['exitCode'] = 100
#         self.assertEqual(State.FAILED, BotoTaskSchema().load(after_fargate_json).data.get_task_state())
#         self.executor.sync()
#
#         # ensure that run_task is called correctly as defined by Botocore docs
#         self.executor.ecs.describe_tasks.assert_called_once()
#         self.assert_botocore_call('DescribeTasks', *self.executor.ecs.describe_tasks.call_args)
#
#         # task is not stored in active workers
#         self.assertEqual(len(self.executor.active_workers), 0)
#         # Task is immediately succeeded
#         fail_mock.assert_called_once()
#         self.assertFalse(success_mock.called)
#
#     @mock.patch('airflow.executors.base_executor.BaseExecutor.fail')
#     @mock.patch('airflow.executors.base_executor.BaseExecutor.success')
#     def test_failed_sync_api(self, success_mock, fail_mock):
#         """Test what happens when ECS sync fails for certain tasks repeatedly"""
#         self.__mock_sync()
#         self.executor.ecs.describe_tasks.return_value = {
#             'tasks': [],
#             'failures': [{
#                 'arn': 'ABC',
#                 'reason': 'Sample Failure',
#                 'detail': 'UnitTest Failure - Please ignore'
#             }]
#         }
#
#         # Call Sync 3 times with failures
#         for check_count in range(AwsEcsFargateExecutor.MAX_FAILURE_CHECKS):
#             self.executor.sync_running_tasks()
#             # ensure that run_task is called correctly as defined by Botocore docs
#             self.assertEqual(self.executor.ecs.describe_tasks.call_count, check_count + 1)
#             self.assert_botocore_call('DescribeTasks', *self.executor.ecs.describe_tasks.call_args)
#
#             # Ensure task arn is not removed from active
#             self.assertIn('ABC', self.executor.active_workers.get_all_arns())
#
#             # Task is not failed or succeeded
#             self.assertFalse(fail_mock.called)
#             self.assertFalse(success_mock.called)
#
#         # Last call should fail the task
#         self.executor.sync_running_tasks()
#         self.assertNotIn('ABC', self.executor.active_workers.get_all_arns())
#         self.assertTrue(fail_mock.called)
#         self.assertFalse(success_mock.called)
#
#     def test_terminate(self):
#         """Test that executor can shut everything down; forcing all tasks to unnaturally exit"""
#         after_fargate_task = self.__mock_sync()
#         after_fargate_task['containers'][0]['exitCode'] = 100
#         self.assertEqual(State.FAILED, BotoTaskSchema().load(after_fargate_task).data.get_task_state())
#
#         self.executor.terminate()
#
#         self.assertTrue(self.executor.ecs.stop_task.called)
#         self.assert_botocore_call('StopTask', *self.executor.ecs.stop_task.call_args)
#
#     def assert_botocore_call(self, method_name, args, kwargs):
#         assert_botocore_call(self.ecs_model, method_name, args, kwargs)
#
#     def test_end(self):
#         """Test that executor can end successfully; awaiting for all tasks to naturally exit"""
#         sync_call_count = 0
#         sync_func = self.executor.sync
#
#         def sync_mock():
#             """Mock won't work here, because we actually want to call the 'sync' func"""
#             nonlocal sync_call_count
#             sync_func()
#             sync_call_count += 1
#
#         self.executor.sync = sync_mock
#         after_fargate_task = self.__mock_sync()
#         after_fargate_task['containers'][0]['exitCode'] = 100
#         self.executor.end(heartbeat_interval=0)
#
#         self.executor.sync = sync_func
#
#     def setUp(self) -> None:
#         """Creates Botocore Loader (used for asserting botocore calls) and a mocked ecs client"""
#         self.ecs_model = get_botocore_model('ecs')
#         self.__set_mocked_executor()
#
#     def __set_mocked_executor(self):
#         """Mock ECS such that there's nothing wrong with anything"""
#         from airflow.configuration import conf
#         conf.set('ecs_fargate', 'region', 'us-west-1')
#         conf.set('ecs_fargate', 'cluster', 'some-ecs-cluster')
#         conf.set('ecs_fargate', 'task_definition', 'some-ecs-task-definition')
#         conf.set('ecs_fargate', 'container_name', 'some-ecs-container')
#         conf.set('ecs_fargate', 'launch_type', 'FARGATE')
#         executor = AwsEcsFargateExecutor()
#         executor.start()
#
#         # replace boto3 ecs client with mock
#         ecs_mock = mock.Mock(spec=executor.ecs)
#         run_task_ret_val = {
#             'tasks': [{'taskArn': '001'}],
#             'failures': []
#         }
#         ecs_mock.run_task.return_value = run_task_ret_val
#         executor.ecs = ecs_mock
#
#         self.executor = executor
#
#     def __mock_sync(self):
#         """Mock ECS such that there's nothing wrong with anything"""
#
#         # create running fargate instance
#         before_fargate_task = mock.Mock(spec=EcsFargateTask)
#         before_fargate_task.task_arn = 'ABC'
#         before_fargate_task.api_failure_count = 0
#         before_fargate_task.get_task_state.return_value = State.RUNNING
#
#         airflow_cmd = mock.Mock(spec=list)
#         airflow_key = mock.Mock(spec=tuple)
#         airflow_exec_conf = mock.Mock(spec=dict)
#         self.executor.active_workers.add_task(before_fargate_task, airflow_key, airflow_cmd, airflow_exec_conf)
#
#         after_task_json = {
#             'taskArn': 'ABC',
#             'desiredStatus': 'STOPPED',
#             'lastStatus': 'STOPPED',
#             'startedAt': dt.datetime.now(),
#             'containers': [{
#                 'name': 'some-ecs-container',
#                 'lastStatus': 'STOPPED',
#                 'exitCode': 0
#             }]
#         }
#         self.executor.ecs.describe_tasks.return_value = {
#             'tasks': [after_task_json],
#             'failures': []
#         }
#         return after_task_json
