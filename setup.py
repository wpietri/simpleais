from setuptools import setup, find_packages

setup(name='simpleais',
      version=0.1,
      description='a simple ais parser',
      url='https://github.com/wpietri/simpleais',
      author='William Pietri',
      license='Apache 2.0',
      packages=find_packages(),
      install_requires=['bitstring', 'testfixtures', 'Click'],
      entry_points={
          'console_scripts': [
              'aisgrep = simpleais.tools:grep',
              'aist = simpleais.tools:as_text',
          ],
      },
      )
