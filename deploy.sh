rm -rf dist
rm -rf airflow_aws_executors.egg-info
python setup.py sdist
pip uninstall airflow-aws-executors -y
pip install -e .
twine upload dist/* --verbose