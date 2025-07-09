"""Setup script for docker-swarm-ctl CLI"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="docker-swarm-ctl",
    version="0.1.0",
    author="Docker Swarm Control",
    author_email="admin@localhost.local",
    description="A kubectl-like CLI for Docker Swarm management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/docker-swarm-ctl/cli",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
        "pyyaml>=6.0",
        "tabulate>=0.9",
        "colorama>=0.4",
        "python-dateutil>=2.8",
    ],
    entry_points={
        "console_scripts": [
            "docker-swarm-ctl=docker_swarm_ctl.cli:cli",
            "dsctl=docker_swarm_ctl.cli:cli",  # Short alias
        ],
    },
)