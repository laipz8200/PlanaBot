autoflake --remove-all-unused-imports -r --exclude __init__.py --in-place plana
autoflake --remove-all-unused-imports -r --exclude __init__.py --in-place plugins
isort --profile black plana
isort --profile black plugins
black .