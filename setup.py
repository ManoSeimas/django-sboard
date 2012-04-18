from setuptools import setup, find_packages

setup(name='django-sboard',
      version='0.1',
      packages=find_packages(),
      install_requires=[
          'anytorst',
          'psutil',
          'unidecode',
          'zope.component',
          'sqlalchemy',
      ])
