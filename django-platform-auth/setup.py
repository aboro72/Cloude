from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="django-platform-auth",
    version="0.1.0",
    author="Your Organization",
    author_email="your-email@example.com",
    description="Unified authentication package for Django multi-app platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/django-platform-auth",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Framework :: Django :: 5.0",
    ],
    python_requires=">=3.10",
    install_requires=[
        "Django>=5.0",
        "djangorestframework>=3.14",
        "djangorestframework-simplejwt>=5.3",
        "Pillow>=10.0",
    ],
    include_package_data=True,
    zip_safe=False,
)
