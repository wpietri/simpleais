from setuptools import setup, find_packages

setup(name='simpleais',
      version='0.6.2',
      description='a simple ais parser',
      url='https://github.com/wpietri/simpleais',
      author='William Pietri',
      author_email='william-simpleais-0_6@scissor.com',
      license='Apache 2.0',
      packages=find_packages(),
      install_requires=['bitstring', 'testfixtures', 'Click', 'numpy'],
      extras_require={
          'dev': ['beautifulsoup4'],  # if you'll be developing, you may need this
      },
      package_data={'simpleais': ['aivdm.json']},
      entry_points={
          'console_scripts': [
              'aiscat = simpleais.devtools:cat',
              'aisgrep = simpleais.devtools:grep',
              'aist = simpleais.devtools:as_text',
              'aisburst = simpleais.devtools:burst',
              'aisinfo = simpleais.devtools:info',
              'aisdump = simpleais.devtools:dump',
          ],
      },
      )
