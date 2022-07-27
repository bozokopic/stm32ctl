from pathlib import Path
from setuptools import setup


readme = (Path(__file__).parent / 'README.rst').read_text()


setup(
    name='stm32ctl',
    version='0.0.1',
    description='STM32 system bootloader control',
    long_description=readme,
    long_description_content_type='text/x-rst',
    url='https://github.com/bozokopic/stm32ctl',
    packages=['stm32ctl'],
    license='GPLv3',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'],
    install_requires=['hat-aio~=0.6.3',
                      'hat-drivers~=0.5.15'],
    entry_points={'console_scripts': ['stm32ctl = stm32ctl.main:main']})
