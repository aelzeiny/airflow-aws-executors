# Apache Airflow: Native AWS Executors
[![Build Status](https://travis-ci.com/aelzeiny/airflow-aws-executors.svg?branch=master)](https://travis-ci.com/aelzeiny/airflow-aws-executors)

This is an AWS Executor that delegates every task to a scheduled container on either AWS Batch, AWS Fargate, or AWS ECS.

```bash
pip install airflow-aws-executors
```

## Getting Started
For `AWS Batch`: [Getting Started with AWS Batch ReadMe](getting_started_batch.md)

For `AWS ECS/Fargate`: [Getting Started with AWS ECS/Fargate ReadMe](getting_started_ecs_fargate.md)


## How Airflow Executors Work
Every time Apache Airflow wants to run a task, the Scheduler generates a shell command that needs to be executed **somewhere**. 
Under the hood this command will run Python code, and it looks something like this: 
```bash
airflow run <DAG_ID> <TASK_ID> <EXECUTION_DATE>
```
What people refer to as the Executor, is actually an API and not a thread/process. The process that runs is the Airflow
Scheduler, and the Executor API is part of that process. When the Scheduler process generates the shell command above, 
it is the executor that decides how this is ran. Here's how what different Executors handle this command: 
* **LocalExecutor**
    * `execute_async()` Uses Python's Subprocess library to spin up a new process with the shell command
    * `sync()` Monitors exit code on every heartbeat
* **CeleryExecutor**
    * `execute_async()` Uses the Celery library to put this shell command in a message queue
    * `sync()` Monitors the Celery Backend to determine task completion
* **KubernetesExecutor**
    * `execute_async()` Launches K8 Pod with the shell command
    * `sync()` Monitors K8 Pod
    
So, how do these executors work? Well, on the highest level, it just calls Boto3 APIs to schedule containers onto 
compute clusters.

* **AwsEcsFargateExecutor**
    * `execute_async()` Uses the Boto3 library to call [ECS.run_task()][run_task], and launches a container with the shell command onto a EC2 or Serverless cluster
    * `sync()` Uses the Boto3 library to call ECS.describe_tasks() to monitor the exit-code of the Airflow Container.
* **AwsBatchExecutor**
    * `executor_async()`Uses the Boto3 library to call [Batch.submit_job()][submit_job], and puts this message in a job-queue
    * `sync()` Uses the Boto3 library to call Batch.describe_jobs() to monitor the status of the Airflow Container


## But Why?
There's so much to unpack here.

#### In a Nut-Shell:
* Pay for what you use.
* Simplicity in Setup.
* No new libraries are introduced to Airflow
* Servers require up-keep and maintenance. For example, just one CPU-bound or memory-bound Airflow Task could overload the resources of a server and starve out the celery or scheduler thread; [thus causing the entire server to go down](https://docs.docker.com/config/containers/resource_constraints/#understand-the-risks-of-running-out-of-memory). All of these executors don't have this problem.

#### The Case for AWS Batch
AWS Batch can be seen as very similar to the Celery Executor, but WITH Autoscaling. AWS will magically provision and take-down instances. 
AWS will magically monitor each container store their status for ~24 hours. AWS will determine when to autoscale based off of amount of time and number of tasks in queue.

In contrast, Celery can scale up, but doesn't have a good scaling-down story (based off of personal experience). If you look at Celery's Docs about Autoscaling you'll find APIs about scaling the number of threads on one server; that doesn't even work. Each Celery workers is the user's responsibility to provision and maintain at fixed capacity.
The Celery Backend and worker queue also need attention and maintenance. I've tried autoscaling an ECS cluster on my own with CloudWatch Alarms on SQS, 
triggering CloudWatch Events, triggering capacity providers, triggering Application Autoscaling groups, 
and it was a mess that I never got to work properly.

#### The Case for AWS Batch on AWS Fargate, and AWS Fargate
If you're on the Fargate executor it may take ~2.5 minutes for a task to pop up, but at least it's a constant O(1) time. 
This way, the concept of tracking DAG Landing Times becomes unnecessary. 
If you have more than 2000 concurrent tasks (which is a lot) then you can always contact AWS to provide an increase in this soft-limit.


## AWS Batch v AWS ECS v AWS Fargate?
**I almost always recommend that you go the AWS Batch route**. Especially since, as of Dec 2020, AWS Batch supports Fargate deployments. So unless you need some very custom flexibility provided by ECS, or have a particular reason to use AWS Fargate directly, then go with AWS Batch.

`AWS Batch` - Is built on top of ECS, but has additional features for Batch-Job management. Including auto-scaling up and down servers on an ECS cluster based on jobs submitted to a queue. Generally easier to configure and setup than either option.

`AWS Fargate` - Is a serverless container orchestration service; comparable to a proprietary AWS version of Kubernetes. Launching a Fargate Task is like saying "I want these containers to be launched somewhere in the cloud with X CPU and Y memory, and I don't care about the server". AWS Fargate is built on top of AWS ECS, and is easier to manage and maintain. However, it provides less flexibility.

`AWS ECS` - Is known as "Elastic Container Service", which is a container orchestration service that uses a designated cluster of EC2 instances that you operate, own, and maintain.


|                   | Batch                                                                               | Fargate                                     |  ECS                                              |
|-------------------|-------------------------------------------------------------------------------------|---------------------------------------------|---------------------------------------------------|
| Start-up per task | Combines both, depending on if the job queue is Fargate serverless                  | 2-3 minutes per task; O(1) constant time    | Instant 3s, or until capacity is available.       |
| Maintenance       | You patch the own, operate, and patch the servers OR Serverless (as of Dec 2020)    | Serverless                                  | You patch the own, operate, and patch the servers |
| Capacity          | Autoscales to configurable Max vCPUs in compute environment                         | ~2000 containers. See AWS Limits            | Fixed. Not auto-scaling.                          |
| Flexibility       | Combines both, depending on if the job queue is Fargate serverless                  | Low. Can only do what AWS allows in Fargate | High. Almost anything that you can do on an EC2   |
| Fractional CPUs?  | Yes, as of Dec 2020 a task can have 0.25 vCPUs.                                     | Yes. A task can have 0.25 vCPUs.            | Yes. A task can have 0.25 vCPUs.                  |


## Optional Container Requirements
This means that you can specify CPU, Memory, env vars, and GPU requirements on a task.

#### AWS Batch
Specifying an executor config will be merged directly into the [Batch.submit_job()][submit_job] request kwarg.

For example:
```python

task = PythonOperator(
    python_callable=lambda *args, **kwargs: print('hello world'),
    task_id='say_hello',
    executor_config=dict(
        vcpus=1,
        memory=512
    ),
    dag=dag
)
```

#### AWS ECS/Fargate
Specifying an executor config will be merged into the [ECS.run_task()][run_task] request kwargs as a container override for the 
airflow container.
[Refer to AWS' documentation for Container Override for a full list of kwargs](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ContainerOverride.html)

For example: 
```python
task = PythonOperator(
    python_callable=lambda *args, **kwargs: print('hello world'),
    task_id='say_hello',
    executor_config=dict(
        cpu=256,  # 0.25 fractional CPUs 
        memory=512
    ),
    dag=dag
)
```


## Airflow Configurations
#### Batch
`[batch]`
* `region` 
    * **description**: The name of AWS Region
    * **mandatory**: even with a custom run_task_kwargs
    * **example**: us-east-1
* `job_name`
    * **description**: The name of airflow job
    * **example**: airflow-job-name
* `job_queue`
    * **description**: The name of AWS Batch Queue in which tasks are submitted
    * **example**: airflow-job-queue
* `job_definition`
    * **description**: The name of the AWS Batch Job Definition; optionally includes revision number
    * **example**: airflow-job-definition or airflow-job-definition:2
* `submit_job_kwargs`
    * **description**: This is the default configuration for calling the Batch [submit_job function][submit_job] API.
    To change the parameters used to run a task in Batch, the user can overwrite the path to
    specify another python dictionary. More documentation can be found in the `Extensibility` section below.
    * **default**: airflow_aws_executors.conf.BATCH_SUBMIT_JOB_KWARGS
* `adopt_task_instances`
    * **description**: Boolean flag. If set to True, the executor will try to adopt orphaned task instances from a
    SchedulerJob shutdown event (for example when a scheduler container is re-deployed or terminated).
    If set to False (default), the executor will terminate all active AWS Batch Jobs when the scheduler shuts down. 
    More documentation can be found in the [airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/scheduler.html#scheduler-tuneables).
    * **default**: False
#### ECS & FARGATE
`[ecs_fargate]`
* `region` 
    * **description**: The name of AWS Region
    * **mandatory**: even with a custom run_task_kwargs
    * **example**: us-east-1
* `cluster` 
    * **description**: Name of AWS ECS or Fargate cluster
    * **mandatory**: even with a custom run_task_kwargs
* `container_name` 
    * **description**: Name of registered Airflow container within your AWS cluster. This container will
    receive an airflow CLI command as an additional parameter to its entrypoint.
    For more info see url to Boto3 docs above.
    * **mandatory**: even with a custom run_task_kwargs
* `task_definition` 
    * **description**: Name of AWS Task Definition. [For more info see Boto3][run_task].
* `launch_type` 
    * **description**: Launch type can either be 'FARGATE' OR 'EC2'. [For more info see Boto3][run_task].
    * **default**: FARGATE
* `platform_version`
    * **description**: AWS Fargate is versioned. [See this page for more details](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/platform_versions.html)
    * **default**: LATEST
* `assign_public_ip` 
    * **description**: Assign public ip. [For more info see Boto3][run_task].
* `security_groups` 
    * **description**: Security group ids for task to run in (comma-separated). [For more info see Boto3][run_task].
    * **example**: sg-AAA,sg-BBB
* `subnets` 
    * **description**: Subnets for task to run in (comma-separated). [For more info see Boto3][run_task].
    * **example**: subnet-XXXXXXXX,subnet-YYYYYYYY
* `run_task_kwargs`
    * **description**: This is the default configuration for calling the ECS [run_task function][run_task] API.
    To change the parameters used to run a task in FARGATE or ECS, the user can overwrite the path to
    specify another python dictionary. More documentation can be found in the `Extensibility` section below.
    * **default**: airflow_aws_executors.conf.ECS_FARGATE_RUN_TASK_KWARGS
* `adopt_task_instances`
  * **description**: Boolean flag. If set to True, the executor will try to adopt orphaned task instances from a
    SchedulerJob shutdown event (for example when a scheduler container is re-deployed or terminated).
    If set to False (default), the executor will terminate all active ECS Tasks when the scheduler shuts down.
    More documentation can be found in the [airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/scheduler.html#scheduler-tuneables).
  * **default**: False


*NOTE: Modify airflow.cfg or export environmental variables. For example:* 
```bash
AIRFLOW__ECS_FARGATE__REGION="us-west-2"
```


## Extensibility
There are many different ways to schedule an ECS, Fargate, or Batch Container. You may want specific container overrides, 
environmental variables, subnets, retries, etc. This project does **not** attempt to wrap around the AWS API.
These technologies are ever evolving, and it would be impossible to keep up with AWS's innovations. 
Instead, it allows the user to offer their own configuration in the form of Python dictionaries, 
which are then directly passed to Boto3's [run_task][run_task] or [submit_job][submit_job] function 
as **kwargs. This allows for maximum flexibility and little maintenance.

#### AWS Batch
In this example we will modify the default `submit_job_kwargs` config. Note, however, there is 
nothing that's stopping us from completely overriding it and providing our own config. 
If we do so, be sure to specify the mandatory Airflow configurations in the section above.

For example:
```bash
# exporting env vars in this way is like modifying airflow.cfg
export AIRFLOW__BATCH__SUBMIT_JOB_KWARGS="custom_module.CUSTOM_SUBMIT_JOB_KWARGS"
```

```python
# filename: AIRFLOW_HOME/plugins/custom_module.py
from airflow_aws_executors.conf import BATCH_SUBMIT_JOB_KWARGS
from copy import deepcopy

# Add retries & timeout to default config
CUSTOM_SUBMIT_JOB_KWARGS = deepcopy(BATCH_SUBMIT_JOB_KWARGS)
CUSTOM_SUBMIT_JOB_KWARGS['retryStrategy'] = {'attempts': 3}
CUSTOM_SUBMIT_JOB_KWARGS['timeout'] = {'attemptDurationSeconds': 24 * 60 * 60 * 60}
```

"I need more levers!!! I should be able to make changes to how the API gets called at runtime!"

```python
class CustomBatchExecutor(AwsBatchExecutor):
    def _submit_job_kwargs(self, task_id, cmd, queue, exec_config) -> dict:
        submit_job_api = super()._submit_job_kwargs(task_id, cmd, queue, exec_config)
        if queue == 'long_tasks_queue':
            submit_job_api['retryStrategy'] = {'attempts': 3}
            submit_job_api['timeout'] = {'attemptDurationSeconds': 24 * 60 * 60 * 60}
        return submit_job_api
```

#### AWS ECS/Fargate
In this example we will modify the default `submit_job_kwargs`. Note, however, there is nothing that's stopping us 
from completely overriding it and providing our own config. If we do so, be sure to specify the mandatory Airflow configurations
in the section above.

For example:
```bash
# exporting env vars in this way is like modifying airflow.cfg
export AIRFLOW__BATCH__SUBMIT_JOB_KWARGS="custom_module.CUSTOM_SUBMIT_JOB_KWARGS"
```

```python
# filename: AIRFLOW_HOME/plugins/custom_module.py
from airflow_aws_executors.conf import ECS_FARGATE_RUN_TASK_KWARGS
from copy import deepcopy

# Add environmental variables to contianer overrides
CUSTOM_RUN_TASK_KWARGS = deepcopy(ECS_FARGATE_RUN_TASK_KWARGS)
CUSTOM_RUN_TASK_KWARGS['overrides']['containerOverrides'][0]['environment'] = [
    {'name': 'CUSTOM_ENV_VAR', 'value': 'enviornment variable value'}
]
```

"I need more levers!!! I should be able to make changes to how the API gets called at runtime!"

```python
class CustomFargateExecutor(AwsFargateExecutor):
    def _run_task_kwargs(self, task_id, cmd, queue, exec_config) -> dict:
        run_task_api = super()._run_task_kwargs(task_id, cmd, queue, exec_config)
        if queue == 'long_tasks_queue':
            run_task_api['retryStrategy'] = {'attempts': 3}
            run_task_api['timeout'] = {'attemptDurationSeconds': 24 * 60 * 60 * 60}
        return run_task_api
```

## Issues & Bugs
Please file a ticket in GitHub for issues. Be persistent and be polite.


## Contribution & Development
This repository uses Travis-CI for CI, pytest for Integration/Unit tests, and isort+pylint for code-style. 
Pythonic Type-Hinting is encouraged. From the bottom of my heart, thank you to everyone who has contributed 
to making Airflow better.


[boto_conf]: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
[run_task]: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.run_task
[submit_job]:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.submit_job
