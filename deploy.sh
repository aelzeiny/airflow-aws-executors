rm -rf dist
rm -rf apache_airflow_ecs_fargate_executor.egg-info
python setup.py sdist
pip uninstall apache-airflow-ecs-fargate-executor -y
pip install -e .
twine upload dist/* --verbose