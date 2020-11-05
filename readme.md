# AWS ECS and Fargate Executor
This is an AWS Executor that delegates every task to a scheduled container on either AWS ECS or AWS Fargate. By default, AWS Fargate will let you run
2000 simultaneous containers, with each container representing 1 Airflow Task.

## Getting Started

## Extensibility

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