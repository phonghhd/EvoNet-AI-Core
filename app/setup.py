import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read_requirements():
    req_path = os.path.join(here, '..', 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path) as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []


setup(
    name="evonet",
    version="2.0.0",
    description="Autonomous AI Security Agent",
    packages=find_packages(where=here),
    package_dir={"": "."},
    install_requires=read_requirements() + ["typer>=0.9.0", "rich>=13.0.0"],
    entry_points={
        "console_scripts": [
            "evonet=cli:main",
        ],
    },
    python_requires=">=3.11",
)
