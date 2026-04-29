import os
from setuptools import setup, find_packages

# Đọc requirements từ file requirements.txt
def read_requirements():
    with open(os.path.join(os.path.dirname(__file__), '..', 'requirements.txt')) as f:
        return f.read().splitlines()

setup(
    name="evonet",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["app.cli"],
    install_requires=read_requirements() + ["typer", "rich"],
    entry_points={
        "console_scripts": [
            "evonet=app.cli:main", # Gõ 'evonet' sẽ gọi hàm 'main' trong 'app/cli.py'
        ],
    },
)