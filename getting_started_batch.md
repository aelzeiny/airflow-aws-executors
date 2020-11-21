# Getting Started with AWS Batch

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
    ```dockerfile
    FROM puckel/docker-airflow
    
    RUN pip3 install --no-cache-dir boto3 airflow-aws-exeecutors
    ENV AIRFLOW__CORE__FERNET_KEY [fernet key]
    ENV AIRFLOW__CORE__SQL_ALCHEMY_CONN postgresql+psycopg2://[username]:[password]@[rds-host]:5432/airflow_metadb
    ENV AIRFLOW__CORE__EXECUTOR aws_executors_plugin.AwsBatchExecutor
    ENV AIRFLOW__CORE__PARALLELISM 30
    ENV AIRFLOW__CORE__DAG_CONCURRENCY 30
   
    ENV AIRFLOW__BATCH__REGION us-west-1
    ENV AIRFLOW__BATCH__JOB_NAME airflow-task
    ENV AIRFLOW__BATCH__JOB_QUEUE airflow-job-queue
    ENV AIRFLOW__BATCH__JOB_DEFINITION airflow-job-defined
   
    RUN airflow connections -a --conn_id remote_logging --conn_type s3
    ENV AIRFLOW__CORE__REMOTE_LOGGING True
    ENV AIRFLOW__CORE__REMOTE_LOG_CONN_ID remote_logging
    ENV AIRFLOW__CORE__REMOTE_BASE_LOG_FOLDER s3://[bucket/path/to/logging/folder] 
    
    COPY plugins ${AIRFLOW_HOME}/plugins/
    COPY dags ${AIRFLOW_HOME}/dags/
    ```

    **NOTE: Custom Containers** You can use a custom container provided that the entrypoint will accept and run airflow commands. [Here's the
    most important line](https://github.com/puckel/docker-airflow/blob/master/script/entrypoint.sh#L133) in Puckle's 
    container! Meaning that the command "docker run [image] airflow version" will execute "airflow version" locally on 
    the container. *BE SURE YOU HAVE THIS*!  It's heavily important that commands like 
    `["airflow", "run", <dag_id>, <task_id>, <execution_date>]` are accepted by your container's entrypoint script.
 
 4. Run through the AWS Batch Creation Wizard on AWS Console. The executor does not have any
 prerequisites to how you create your Job Queue or Compute Environment. Go nuts; have at it. I'll refer you to the 
 [AWS Docs' Getting Started with Batch](https://docs.aws.amazon.com/batch/latest/userguide/Batch_GetStarted.html).
 You will need to assign the right IAM roles for the remote S3 logging. 
 Also, your dynamically provisioned EC2 instances do not need to be connected to the public internet, 
 private subnets in private VPCs are encouraged. However, be sure that all instances has access to your Airflow MetaDB.
 
 5. When creating a Job Definition choose the 'container' type and point to the private repo. The 'commands' array is
 optional on the task-definition level. At runtime, Airflow commands will be injected here by the AwsBatchExecutor!
 
 6. Let's go back to that machine in step #1 that's running the Scheduler. We'll use the same docker container as 
 before; except we'll do something like `docker run ... airflow webserver` and `docker run ... airflow scheduler`. 
 Here are the minimum IAM roles that the executor needs to launch tasks, feel free to tighten the resources around the 
 job-queues and compute environments that you'll use.
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AirflowBatchRole",
                "Effect": "Allow",
                "Action": [
                    "batch:SubmitJob",
                    "batch:DescribeJobs",
                    "batch:TerminateJob"
                ],
                "Resource": "*"
            }
        ]
    }
    ```
 7. You're done. Configure & launch your scheduler. However, maybe you did something real funky with your AWS Batch compute
 environment. The good news is that you have full control over how the executor submits jobs. 
 See the [#Extensibility](./readme.md) section in the readme. Thank you for taking the time to set this up!


[boto_conf]: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
