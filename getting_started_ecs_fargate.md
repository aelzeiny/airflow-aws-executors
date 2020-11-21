# Getting Started ECS & Fargate

This is for users who want to setup an Airflow Executor that is directly integrated with either AWS Fargate or AWS ECS.
We recommend that users that want to provision and ECS cluster use AWS Batch Executor instead of using this executor, in
order to benefit from provisioned auto-scaling of workers. This executor is best-used for administrating serverless 
FARGATE clusters, but can also be used for standard ECS clusters as well.

1. The first thing you want to do (if you haven't already) is setup AWS credentials on the machine running the executor. 
Perhaps this means creating a configuration file, loading environmental variables, 
or creating a new IAM role on EC2 [(see link)][boto_conf].

2. In your `$AIRFLOW_HOME/plugins` folder create a file called `aws_executors_plugin.py`.
    ```python
    from airflow.plugins_manager import AirflowPlugin
    from airflow_aws_executors import AwsBatchExecutor, AwsEcsFargateExecutor
    
    
    class EcsFargatePlugin(AirflowPlugin):
        """AWS ECS & AWS FARGATE Plugin"""
        name = "aws_executors_plugin"
        executors = [AwsBatchExecutor, AwsEcsFargateExecutor]
    ```

3. Now we setup our container. I'm using [Puckle's Docker Image](https://github.com/puckel/docker-airflow) for mine.
Build this image and upload it to a private repository. You may want to use DockerHub or AWS ECR for this.
Contrary to "good style", I'm hard-coding my environmental variables in my docker image instead of passing them in on
docker-run initialization.
    ```dockerfile
    FROM puckel/docker-airflow
    
    RUN pip3 install --no-cache-dir boto3  airflow-aws-exeecutors
    ENV AIRFLOW__CORE__FERNET_KEY [fernet key]
    ENV AIRFLOW__CORE__SQL_ALCHEMY_CONN postgresql+psycopg2://[username]:[password]@[rds-host]:5432/airflow_metadb
    ENV AIRFLOW__CORE__EXECUTOR aws_executors_plugin.AwsEcsFargateExecutor
    ENV AIRFLOW__CORE__PARALLELISM 30
    ENV AIRFLOW__CORE__DAG_CONCURRENCY 30
   
    ENV AIRFLOW__ECS_FARGATE__REGION us-west-1
    ENV AIRFLOW__ECS_FARGATE__CLUSTER airflow-cluster
    ENV AIRFLOW__ECS_FARGATE__CONTAINER_NAME airflow-container
    ENV AIRFLOW__ECS_FARGATE__TASK_DEFINITION airflow-task-def
    ENV AIRFLOW__ECS_FARGATE__LAUNCH_TYPE FARGATE
    ENV AIRFLOW__ECS_FARGATE__PLATFORM_VERSION LATEST
    ENV AIRFLOW__ECS_FARGATE__ASSIGN_PUBLIC_IP NO
    ENV AIRFLOW__ECS_FARGATE__SECURITY_GROUPS XXX,YYY,ZZZZ
    ENV AIRFLOW__ECS_FARGATE__SUBNETS AAA,BBB
   
    RUN airflow connections -a --conn_id remote_logging --conn_type s3
    ENV AIRFLOW__CORE__REMOTE_LOGGING True
    ENV AIRFLOW__CORE__REMOTE_LOG_CONN_ID remote_logging
    ENV AIRFLOW__CORE__REMOTE_BASE_LOG_FOLDER s3://[bucket/path/to/logging/folder] 
    
    COPY plugins ${AIRFLOW_HOME}/plugins/
    COPY dags ${AIRFLOW_HOME}/dags/
    ```

    **NOTE: Custom Containers** You can use a custom container provided that the entrypoint will accept and run airflow commands. [Here's the
    most important line](https://github.com/puckel/docker-airflow/blob/master/script/entrypoint.sh#L133) in Puckle's 
    container! Meaning that the command "docker run [image] airflow version" will execute "airflow version" on 
    the container. *BE SURE YOU HAVE THIS*!  It's heavily important that commands like 
    `["airflow", "run", <dag_id>, <task_id>, <execution_date>]` are accepted by your container's entrypoint script.
 
 4. Run through the AWS Fargate Creation Wizard on AWS Console. The executor only requires that all airflow tasks be launched
 with the same cluster and task definition. I'll refer you to the 
 [AWS Docs' Getting Started with Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html).
 If you want to use ECS directly without Fargate then I would encourage you to use the AWS Batch Executor. However, if you
 insist, then go ahead and take a peek at the [AWS Docs' for Getting Started with ECS](https://aws.amazon.com/ecs/getting-started/).
 Configure your Cluster and Task Definition. You *DO NOT* need to configure a Service. 
 You will need to assign the right IAM roles for the remote S3 logging. 
 Also, your dynamically provisioned EC2 instances do not need to be connected to the public internet, 
 private subnets in private VPCs are encouraged. However, be sure that all instances has access to your Airflow MetaDB.
 
 5. When creating a Task Definition point to the private Docker repo. The 'commands' array is
 optional on the task-definition level. At runtime, Airflow commands will be injected here by the AwsFargateExecutor!
 
 6. Let's go back to that machine in step #1 that's running the Scheduler. We'll use the same docker container as 
 before; except we'll do something like `docker run ... airflow webserver` and `docker run ... airflow scheduler`. It's
 critically important that the same container is used for the task definition and scheduler. 
 Here are the minimum IAM roles that the executor needs to launch tasks, feel free to tighten the resources around the 
 clusters and task-definitions that you'll use.
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AirflowEcsFargateRole",
                "Effect": "Allow",
                "Action": [
                    "ecs:DescribeTasks",
                    "ecs:RunTask",
                    "ecs:StopTask"
                ],
                "Resource": "*"
            }
        ]
    }
    ```
 7. You're done. Configure & launch your scheduler. However, maybe you did something real funky with your AWS Fargate/ECS 
 clusters or task-definitions. The good news is that you have full control over how the executor submits tasks. 
 See the [#Extensibility](./readme.md) section in the readme. Thank you for taking the time to set this up!


[boto_conf]: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html