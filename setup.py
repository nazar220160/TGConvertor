from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = ["opentele", "aiosqlite", "pyrogram"]

setup(
    name="TGConvertor",
    version="0.0.8",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "mycommand = mypackage.mymodule:__main__",
        ],
    },
    description="This module is small util for easy converting Telegram sessions to various formats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="nazar220160",
    author_email="nazar.fedorowych@gmail.com",
    url="https://github.com/nazar220160/TGConvertor",
    requires=requirements,
    scripts=["TGConvertor/__main__.py"],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
