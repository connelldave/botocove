import pathlib

import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setuptools.setup(
    name="botocove",
    version="0.0.1",
    author="Dave Connell",
    author_email="daveconn41@gmail.com",
    license="GPL",
    description="A decorator to run boto3 functions against an AWS organization",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/connelldave/botocove",
    packages=setuptools.find_packages(exclude=("tests",)),
    include_package_data=True,
    install_requires=["boto3"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
