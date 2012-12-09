from setuptools import setup, find_packages
import os

version = '0.1'

setup(name='cmdhelper',
      version=version,
      description="Makes life easier when you need to write some command line utility which supports a lot of different commands",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='command line utility helper',
      author='Vitaliy Podoba',
      author_email='vitaliypodoba@gmail.com',
      url='',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
      ],
      entry_points={
          'cmdhelper.demo': [
              'demoprint = cmdhelper.command.demo:Demo',
          ],
      }
)
