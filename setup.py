from setuptools import setup, find_packages

setup(
    name="ruclogin",
    version="0.2.11",
    packages=find_packages(),
    description="Login to *.ruc.edu.cn, get cookies.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="panjd123",
    author_email="xm.jarden@gmail.com",
    license="MIT",
    url="https://github.com/panjd123/ruclogin",
    install_requires=[
        "requests",
        "selenium",
        "selenium-wire",
        "webdriver_manager",
        "ddddocr",
        "docopt",
    ],
    package_data={"ruclogin": ["config.ini", "v_cookies.pkl", "jw_cookies.pkl"]},
    entry_points={
        "console_scripts": [
            "ruclogin=ruclogin.ruclogin:main",
        ]
    },
)
