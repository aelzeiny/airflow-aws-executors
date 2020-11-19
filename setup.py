import pathlib
from setuptools import setup


description = "Apache Airflow Executor for AWS ECS, AWS Fargate, and AWS Batch"

try:
    with open(str(pathlib.Path.cwd() / "readme.md"), "r") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = description

setup(
    name="airflow-aws-executors",
    version="0.12",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aelzeiny/airflow-aws-executors",
    author="Ahmed Elzeiny",
    author_email="ahmed.elzeiny@gmail.com",
    license="MIT",
    keywords=['Apache', 'Airflow', 'AWS', 'Executor', 'Fargate', 'ECS', 'AWS ECS', 'AWS Batch', 'AWS Fargate'],
    python_requires='>=3.6.0',
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    packages=["airflow_aws_executors"],
    include_package_data=True,
    install_requires=["boto3", "apache-airflow"]
)
