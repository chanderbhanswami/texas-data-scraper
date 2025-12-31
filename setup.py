"""
Setup configuration for Texas Data Scraper
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="texas-data-scraper",
    version="1.5.1",
    author="Chanderbhan Swami",
    author_email="chanderbhanswami29@gmail.com",
    description="Comprehensive toolkit for scraping Texas government data from Socrata and Comptroller APIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chanderbhanswami/texas-data-scraper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "gpu": [
            "cupy-cuda11x>=12.0.0",
            "cudf-cu11>=23.10.0",
            "dask-cudf>=23.10.0",
            "torch>=2.1.0",
            "numba>=0.58.0",
            "pynvml>=11.5.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "texas-scraper-socrata=scripts.socrata_scraper:main",
            "texas-scraper-comptroller=scripts.comptroller_scraper:main",
            "texas-scraper-combine=scripts.data_combiner:main",
            "texas-scraper-dedupe=scripts.deduplicator:main",
            "texas-scraper-test=scripts.api_tester:main",
        ],
    },
    include_package_data=True,
    package_data={
        "texas-data-scraper": [
            "config/.env.example",
            "README.md",
            "requirements.txt",
            "requirements-gpu.txt",
        ],
    },
    zip_safe=False,
    keywords=[
        "texas",
        "government",
        "data",
        "scraper",
        "socrata",
        "comptroller",
        "api",
        "open-data",
        "franchise-tax",
        "sales-tax",
        "gpu",
        "cuda",
    ],
    project_urls={
        "Bug Reports": "https://github.com/chanderbhanswami/texas-data-scraper/issues",
        "Source": "https://github.com/chanderbhanswami/texas-data-scraper",
        "Documentation": "https://github.com/chanderbhanswami/texas-data-scraper/blob/main/README.md",
    },
)