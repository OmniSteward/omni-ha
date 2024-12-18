from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="omni_ha",
    version="0.1.0",
    author="Elliott Zheng",
    author_email="admin@hypercube.top",
    description="万能智能管家的Home Assistant工具，用于控制Home Assistant中的智能设备",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OmniSteward/omni-ha",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests",
        "homeassistant_api",
        "openai",
    ]
)