from setuptools import setup, find_packages

setup(
    name="omi-gateway",
    version="2025.1.0",
    description="OMI Universal Intelligence Gateway SDK",
    long_description=open("README_CUSTOMERS.md").read(),
    long_description_content_type="text/markdown",
    author="OMI Labs",
    author_email="support@omi-api.com",
    url="https://github.com/omichauhan-lgtm/omi-gateway",
    py_modules=["omi_client"],
    install_requires=[
        "requests>=2.25.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
