from setuptools import setup

setup(
    entry_points={
        'console_scripts': [
            'jeracli=jera_cli:cli',
        ],
    },
) 