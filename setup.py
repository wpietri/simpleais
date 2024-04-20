from setuptools import setup, find_packages

with open('README.rst') as r:
    readme = r.read()

setup(name='simpleais',
      version='0.7.3',
      description='a simple ais parser',
      long_description=readme,
      url='https://github.com/wpietri/simpleais',
      author='William Pietri',
      author_email='william-simpleais-0_7@scissor.com',
      license='Apache 2.0',
      packages=find_packages(),
      install_requires=['bitstring', 'testfixtures', 'Click<8.1.3', 'numpy', 'python-dateutil'],
      extras_require={
          'dev': ['beautifulsoup4', 'nose'],  # if you'll be developing, you may need this
      },
      package_data={'simpleais': ['aivdm.json']},
      entry_points={
          'console_scripts': [
              'aiscat = simpleais.tools:cat',
              'aisgrep = simpleais.tools:grep',
              'aist = simpleais.tools:as_text',
              'aisburst = simpleais.tools:burst',
              'aisinfo = simpleais.tools:info',
              'aisdump = simpleais.tools:dump',
              'aisstat = simpleais.tools:stat',
              'aisrefine = simpleais.tools:refine',
              'ais2json = simpleais.tools:to_json',
          ],
      },
      )
