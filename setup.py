from setuptools import setup, find_packages
from rgc.version import __version__

setup(
    name='rgc',
    version=__version__,
    description='Cleanup old tags from docker-registry provided with GitLab',
    url='https://github.com/mvisonneau/docker-registry-gitlab-cleanup',
    author='Maxime VISONNEAU, Jiří Pinkava',
    author_email='maxime.visonneau@gmail.com, j-pi@seznam.cz',
    license='AGPL-3.0',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=[
        'requests',
        'python-gitlab>=1.8.0',
        'termcolor'
    ],
    entry_points={
        'console_scripts': [
            'rgc=rgc.cli:main'
        ],
    }
)
