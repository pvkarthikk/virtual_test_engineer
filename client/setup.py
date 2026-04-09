#!/usr/bin/env python3
"""
Setup script for Virtual Test Engineer Client
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vte-client",
    version="1.0.0",
    author="Virtual Test Engineer Team",
    author_email="team@vte.example.com",
    description="Python client for Virtual Test Engineer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/virtual-test-engineer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=1.8.0",
        "dataclasses>=0.6; python_version < '3.7'",
    ],
    extras_require={
        "dev": ["pytest>=6.0", "pytest-asyncio>=0.15"],
    },
    entry_points={
        "console_scripts": [
            "vte-client=example_client:main",
        ],
    },
)