from setuptools import setup, find_packages

setup(
    name="dfs",
    version="0.1.0",
    description="Sistema de Archivos Distribuidos con Replicación",
    author="Cardanivelez",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'dfs-namenode=src.namenode.server:main',
            'dfs-datanode=src.datanode.server:main',
            'dfs-cli=src.client.cli:main',
        ],
    },
    python_requires='>=3.8',
)