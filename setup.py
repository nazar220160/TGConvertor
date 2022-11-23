import setuptools
with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    "opentele==1.15.1",
    "tgcrypto==1.2.3",
    "pyrogram",
    "aiosqlite==0.17.0"
]

setuptools.setup(
    name="TGSessionsConverter",
    version="0.0.1",
    author="nazar",
    author_email="nazar.fedorowych@gmail.com",
    description="This module is small util for converting Telegram sessions  to various formats (Telethon, Pyrogram, Tdata)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nazar220160/TGConvertor/",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
