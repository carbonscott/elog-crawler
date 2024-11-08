import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="elog-crawler",
    version="24.09.02",
    author="Cong Wang",
    author_email="wangimagine@gmail.com",
    description="An elog crwaler.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/carbonscott/peaknet",
    keywords = ['LCLS', 'eLog'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points = {
        'console_scripts' : [
            'elog-crawler.file_manager=elog_crawler.app_crawl_file_manager:main',
            'elog-crawler.elog=elog_crawler.app_crawl_elog:main',
        ],
    },
    python_requires='>=3.6',
    include_package_data=True,
)
