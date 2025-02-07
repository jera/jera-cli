from setuptools import setup, find_packages

setup(
    name='jera-cli',
    version='1.0.0',
    description='CLI simplificada para gerenciar recursos da Jera na AWS',
    packages=find_packages(),
    py_modules=['jera_cli'],
    install_requires=[
        'click==8.1.7',
        'kubernetes==29.0.0',
        'rich==13.7.0',
        'inquirer==3.1.3',
        'PyYAML==6.0.1',
        'setuptools>=65.5.1',  # Necessário para o distutils no Python 3.12
    ],
    entry_points={
        'console_scripts': [
            'jeracli=jera_cli:cli',
        ],
    },
    python_requires='>=3.8',
) 