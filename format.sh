autoflake --remove-all-unused-imports -r --exclude __init__.py --in-place plana
black plana
isort --profile black plana