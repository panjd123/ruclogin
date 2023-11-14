from setuptools import setup, find_packages

setup(
    name="ruclogin",
    version="0.1",
    packages=find_packages(),
    description="Login to v.ruc.edu.cn, get cookies.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="panjd123",
    author_email="xm.jarden@gmail.con",
    license="MIT",
    url="https://github.com/panjd123",
    install_requires=[
        "requests",
        "selenium",
        "webdriver_manager",
        "ddddocr",
        "docopt",
        "Pillow==9.5.0",
    ],
    package_data={"ruclogin": ["config.ini"]},
    entry_points={
        "console_scripts": [
            "ruclogin=ruclogin.ruclogin:main",
        ]
    },
)
