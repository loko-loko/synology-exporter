from setuptools import setup

setup(
    name="synology-exporter",
    version="0.0.1",
    description="Exports to Prometheus DSM Synology metrics",
    url="https://github.com/loko-loko/synology-exporter.git",
    author="loko-loko",
    author_email="loko-loko@github.com",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.8",
    ],
    packages=["synology_exporter"],
    include_package_data=True,
    install_requires=[
        "python-synology==0.9.0",
        "loguru==0.5.0",
        "prometheus-client==0.7.1",
        "PyYAML==5.3.1"
    ],
    entry_points={
        "console_scripts": [
            "synology-exporter=synology_exporter.__main__:main",
        ]
    },
)
