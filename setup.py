# setup.py
from setuptools import setup, find_packages

setup(
    name='fcstverif',
    version='0.1',
    description='Seasonal forecast verification framework',
    author='APCC',
    packages=find_packages(),  # fcstverif 패키지를 포함
    install_requires=[
        'xarray',
        'numpy',
        'pandas',
        'matplotlib',
        'scikit-learn',
        'xskillscore',
        'streamlit'
    ],
)

