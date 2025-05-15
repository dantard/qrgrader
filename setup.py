from setuptools import setup, find_packages

setup(
    name='qrgrader',
    version='0.0.9',
    packages=find_packages(where='src'),  # Specify src directory
    package_dir={'': 'src'},  # Tell setuptools that packages are under src
    install_requires=[
        'pyqt5',
        'pymupdf >= 1.18.17',
        'easyconfig2',
        'zxing-cpp',
        'gspread',
        'pydrive2',
        'opencv-python-headless',
        'pandas',
        'swikv4-minimal'
    ],
    author='Danilo Tardioli',
    author_email='dantard@unizar.es',
    description='A framwork for automatic grading of exams using QR codes',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/dantard/qrgrader',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'qrscanner=qrgrader.qrscanner:main',
            'qrgrader=qrgrader.qrgui:main',
            'qrsheets=qrgrader.qrsheets:main',
            'qrgenerator=qrgrader.qrgenerator:main',
            'qrworkspace=qrgrader.qrworkspace:main',
            'qrtable=qrgrader.qrtable:main',
        ],
    },
    package_data={
        "qrgrader": ["latex/*"],
    },
    include_package_data=True,
)
