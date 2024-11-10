from setuptools import setup, find_packages

setup(
    name="qrgrader",
    version="0.0.1",
    packages=find_packages(where="src"),  # Specify src directory
    package_dir={"": "src"},  # Tell setuptools that packages are under src
    install_requires=[
        "fonttools",
        "gspread",
        "opencv-python-headless",
        "pandas",
        "pydrive",
        "pyminizip",
        "pymupdf",
        "pyqt5",
        "pyyaml",
        "pyzbar",
        "zxing-cpp",
        "cryptography",
        "pyopenssl",
        "psutil",
        "asn1crypto",
        "pillow",
        "pylatexenc"
    ],
    author="Danilo Tardioli, Alejandro R. Mosteo",
    author_email="dantard@unizar.es",
    description="The QRGRADER",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dantard/qrgrader",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'qrgrader=qrgrader.qrgrader:main',
            'qrscanner=qrgrader.qrscanner:main',
            'qrworkspace=qrgrader.qrworkspace:main',
            'qrgenerator=qrgrader.qrgenerator:main',
        ],
    },
)
