from distutils.core import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = ['opentele==1.15.1', "aiosqlite==0.17.0", "pyrogram"]

setup(name='TGConvertor',
      version='0.0.7',
      description='This module is small util for easy converting Telegram sessions to various formats',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='nazar220160',
      author_email='nazar.fedorowych@gmail.com',
      url='https://github.com/nazar220160/TGConvertor',
      packages=['TGConvertor', "TGConvertor/manager", "TGConvertor/manager/sessions"],
      install_requires=requirements,
      classifiers=[
          "Programming Language :: Python :: 3.8",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
      ],
      python_requires='>=3.9',
      )
