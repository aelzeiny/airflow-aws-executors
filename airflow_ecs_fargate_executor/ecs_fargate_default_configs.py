"""
Default AWS ECS configuration
This is the default configuration for calling the ECS `run_task` function.
The AWS ECS Executor calls Boto3's run_task(**kwargs) function with the kwargs templated by this
dictionary. See the URL below for documentation on the parameters accepted by the Boto3 run_task function.
In other words, if you don't like the way Airflow calls the Boto3 RunTask API, then call it yourself by
overriding the airflow config file.
.. seealso::
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.run_task
:return: Dictionary kwargs to be used by ECS run_task() function.
"""

from airflow.configuration import conf


DEFAULT_ECS_FARGATE_CONFIG = {
    'cluster': conf.get('ecs_fargate', 'cluster'),
    'taskDefinition': conf.get('ecs_fargate', 'task_definition'),
    'platformVersion': 'LATEST',

    'overrides': {
        'containerOverrides': [{
            'name': conf.get('ecs_fargate', 'container_name'),
            # The executor will overwrite the 'command' property during execution.
            # Must always be the first container!
            'command': []
        }]
    },
    'count': 1
}

if conf.has_option('ecs_fargate', 'launch_type'):
    DEFAULT_ECS_FARGATE_CONFIG['launchType'] = conf.get('ecs_fargate', 'launch_type')

# Only build this section if 'subnets', 'security_groups', and 'assign_public_ip' are populated
if (conf.has_option('ecs_fargate', 'subnets') and conf.has_option('ecs_fargate', 'security_groups') and
        conf.has_option('ecs_fargate', 'assign_public_ip')):
    DEFAULT_ECS_FARGATE_CONFIG['networkConfiguration'] = {
        'awsvpcConfiguration': {
            'subnets': conf.get('ecs_fargate', 'subnets').split(','),
            'securityGroups': conf.get('ecs_fargate', 'security_groups').split(','),
            'assignPublicIp': conf.get('ecs_fargate', 'assign_public_ip')
        }
    }
