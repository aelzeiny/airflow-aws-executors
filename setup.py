import pathlib
from setuptools import setup


with open(str(pathlib.Path.cwd() / "readme.md"), "r") as fh:
    long_description = fh.read()


setup(
    name="airflow-ecs-fargate-executor",
    version="0.10",
    description="Apache Airflow Executor for AWS ECS and AWS Fargate",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aelzeiny/Airflow-AWS-ECS-Fargate-Executor",
    author="Ahmed Elzeiny",
    author_email="ahmed.elzeiny@gmail.com",
    license="MIT",
    keywords=['Apache', 'Airflow', 'AWS', 'Executor', 'Fargate', 'ECS'],
    python_requires='>=3.6.0',
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    packages=["airflow_ecs_fargate_executor"],
    include_package_data=True,
    install_requires=["boto3", "apache-airflow"]
)
