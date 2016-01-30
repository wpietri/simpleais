from setuptools import setup

setup(name='simpleais',
      version=0.1,
      description='a simple ais parser',
      url='https://github.com/wpietri/simpleais',
      author='William Pietri',
      license='Apache 2.0',
      packages=['simpleais'],
      install_requires=['bitstring', 'testfixtures'],
      scripts=['bin/aisgrep']
      )
