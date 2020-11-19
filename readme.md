# Apache Airflow: Native AWS Executors
[![Build Status](https://travis-ci.com/aelzeiny/airflow-aws-executors.svg?branch=master)](https://travis-ci.com/aelzeiny/airflow-aws-executors)

This is an AWS Executor that delegates every task to a scheduled container on either AWS ECS or AWS Fargate. By default, AWS Fargate will let you run
2000 simultaneous containers, with each container representing 1 Airflow Task.

```bash
pip install airflow-aws-executors
```

## Getting Started

In your `$AIRFLOW_HOME/plugins` folder create a file called `ecs_fargate_plugin.py`.

```python
from airflow.plugins_manager import AirflowPlugin
from airflow_aws_executors import EcsFargateExecutor


class EcsFargatePlugin(AirflowPlugin):
    """AWS ECS & AWS FARGATE Plugin"""
    name = "aws_ecs_plugin"
    executors = [EcsFargateExecutor]
```

For more information on any of these execution parameters, see the link below: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.run_task

For boto3 credential management, seed https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html


## How It Works
Everytime Apache Airflow wants to run a task, this executor will use Boto3's [ECS.run_task()]() function to schedule a container on an existing cluster. Then every scheduler heartbeat the executor will check the status of every running container, and sync it with Airflow.

## But Why?
* Pay for what you use. With Celery, there is no predefined concept of auto-scaling. Therefore the number of worker servers one must constantly provision, pay for, and maintain is a static number. Due to the sporadic nature of batch-processing, most of the time most of these servers are not in use. However, during peak hours, these servers become overloaded.
* Servers require up-keep and maintenance. For example, just one cpu-bound or memory-bound Airflow Task could overload the resources of a server and starve out the celery or scheduler thread; [thus causing the entire server to go down](https://docs.docker.com/config/containers/resource_constraints/#understand-the-risks-of-running-out-of-memory). This executor mitigates this risk.
* Simplicity in Setup.
* No new libaries are introduced

If you're on the Fargate executor it may take 4 minutes for a task to pop up, but at least it's a contant number.  This way, the concept of tracking DAG Landing Times becomes unneccessary. If you have more than 2000 concurrent tasks (which is a lot) then you can always contact AWS to provide an increase in this soft-limit.

## AWS ECS v AWS Fargate?
`AWS Fargate` - Is a serverless container orchistration service; comparable to a proprietary AWS version of Kubernetes. Launching a Fargate Task is like saying "I want these containers to be launched somewhere in the cloud with X CPU and Y memory, and I don't care about the server". AWS Fargate is built on top of AWS ECS, and is easier to manage and maintain. However, it provides less flexibility.

`AWS ECS` - Is known as "Elastic Container Service", which is a container orchistration service that uses a designated cluster of EC2 instances that you operate, own, and maintain.

I almost always recommend that you go the AWS Fargate route unless you need the custom flexibility provided by ECS.

|                   | ECS                                                           | Fargate                                 |
|-------------------|---------------------------------------------------------------|-----------------------------------------|
| Start-up per task | Instantaneous if capacity available                           | 2-4 minutes per task; O(1) constant time|
| Maintenance       | You patch the own, operate, and patch                         | Serverless                              |
| Capacity          | Depends on number of machines with available space in cluster | ~2000 containers. See AWS Limits        |
| Flexibility       | High                                                          | Low                                     |

### Airflow Configurations
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
    * **description**: Name of AWS Task Definition. For more info see url to Boto3 docs above.
* `launch_type` 
    * **description**: Launch type can either be 'FARGATE' OR 'EC2'. For more info see url to Boto3 docs above.
    * **default**: FARGATE
* `platform_version`
    * **description**: AWS Fargate is versioned. [See this page for more details](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/platform_versions.html)
    * **default**: LATEST
* `assign_public_ip` 
    * **description**: Assign public ip. For more info see url to Boto3 docs above.
* `security_groups` 
    * **description**: Security group ids for task to run in (comma-separated). For more info see url to Boto3 docs above.
* `subnets` 
    * **description**: Subnets for task to run in (comma-separated). For more info see url to Boto3 docs above.
    * **example**: subnet-XXXXXXXX,subnet-YYYYYYYY
* `run_task_kwargs`
    * **description**: This is the default configuration for calling the ECS `run_task` function API (see url above).
    To change the parameters used to run a task in FARGATE or ECS, the user can overwrite the path to
    specify another jinja-templated JSON. More documentation can be found in the `Extensibility` section below.
    * **mandatory**: even with a custom run_task_kwargs
    * **default**: default_aws_ecs.DEFAULT_AWS_ECS_CONFIG


*NOTE: Modify airflow.cfg or export environmental variables. For example:* 
```bash
AIRFLOW__ECS_FARGATE__REGION="us-west-2"
```
## Extensibility
There are many different ways to run an ECS or Fargate Container. You may want specific container overrides, environmental variables, subnets, etc. This project does not attempt to wrap around the AWS API. Instead, it allows the user to offer their own configuration in the form of Python dictionary, which are then passed in to Boto3's run_task function as **kwargs.

In this example we will modify the DEFAULT_AWS_ECS_CONFIG. Note, however, there is nothing that's stopping us from complete overriding it and providing our own config. If we do so, the only manditory Airflow Configurations are `region`, `cluster`, `container_name`, and `run_task_kwargs`.

For example:

```bash
export AIRFLOW__AWS_ECS__RUN_TASK_KWARGS="aws_ecs_configs.AWS_ECS_CONFIG"
```

```python
# filename: AIRFLOW_HOME/plugins/aws_ecs_config.py
from aws_ecs_default_configs import DEFAULT_AWS_ECS_CONFIG

# Add environmental variables to contianer overrides
AWS_ECS_CONFIG = DEFAULT_AWS_ECS_CONFIG
AWS_ECS_CONFIG['overrides']['containerOverrides'][0]['environment'] = ['SOME_ENV_A', 'SOME_ENV_B']
```

## Custom Container Requirements
This means that you can specify CPU, Memory, and GPU requirements on a task.
```python
task = PythonOperator(
    python_callable=lambda *args, **kwargs: print('hello world'),
    task_id='say_hello',
    executor_config=dict(
        cpu=256,
        memory=512
    ),
    dag=dag
)
```

## Issues & Bugs
Please file a ticket in github for issues. Be persistant and be polite.

## Contribution & Development
This repository uses Travis-CI for CI, pytest for Integration/Unit tests, and isort+pylint for code-style. 
Pythonic Type-Hinting is encouraged. It's my hope that 
