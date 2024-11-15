# qrgrader 
This framework allows generating multiple answers randomized exams and grade them.

## Overview
qrgrader is an innovative framework designed for generating and grading exams using 2D barcodes, specifically QR codes. This approach allows for the creation of multiple randomized versions of exams and provides an automated grading process. The primary goal is to streamline the examination process, making it more efficient and less prone to human error.

Key Features:
- Randomized Exam Generation: Easily create multiple versions of exams with randomized questions.
- Automated Grading: Scan completed exams and automatically grade them using QR codes embedded in the exam papers.
- Integration with LaTeX: Utilize LaTeX for formatting and generating exam documents.
- Google Drive Integration: Upload and manage exam results directly in Google Sheets for easy access and sharing.
- Interactive Grading Tool: Use a Qt-based application to manually review and adjust grades if necessary.
The framework includes several command-line tools (qrworkspace, qrgenerator, qrscanner, and qrgrader) to facilitate the entire process from exam creation to grading and result management.


## Installation

To install qrgrader clone the repository as (in a Linux machine):
```
git clone https://github.com/dantard/qrgrader.git
```

and then install the scripts:

```
cd qrgrader
pip install .
```

## qrworkspace ##

All the process must be execute inside a so-called _workspace_ which is a set of directory with a specific structure. To create a workspace the command `qrworkspace`:

```
$ qrworkspace 
Workspace qrgrading-220825 has been created correctly.
``` 
It is possible to specify the date with the paremeter `-d date`:

```
$ qrworkspace -d 221215
Workspace qrgrading-221215 has been created correctly.
```

In both cases a directory structure will be created:
```
$ ls qrgrading-221215
drwxrwxr-x 7 danilo danilo 4096 ago 25 14:26 ./
drwxrwxr-x 3 danilo danilo 4096 ago 25 11:53 ../
drwxrwxr-x 4 danilo danilo 4096 ago 25 11:53 generated/
drwxrwxr-x 4 danilo danilo 4096 ago 25 11:53 results/
drwxrwxr-x 2 danilo danilo 4096 ago 25 11:53 scanned/
drwxrwxr-x 3 danilo danilo 4096 ago 25 14:26 source/
```

In the example folder, you can find a workspace already set up in which source folder there is an example exam and in the scanned folder a PDF file with 4 exams scanned for you to try the framework following the instruction below.

## qrgenerator ##

Once the workspace has been created the latex project must be copied inside the `source` directory for the `qrgenerator` script to generate the randomized exams. The main latex file must be called `main.tex` or must be specified using the `-f` flag. Notice that the `qrgrader.sty` file included in the `latex` directory must be included using the `\usepackage{}` latex command.
Here un example of latex code that would generate a dummy exam (code available in the `example` directory):

```
\documentclass[oneside]{article}
\usepackage[aztec]{qrgrader} 
\qrgraderpagestyle{Subject name or exam title}

\begin{document}

\IDMatrix{0.6cm}{\uniqueid}{Student ID figure}

\begin{exam}[shuffle=off, style=matrix, showcorrect=no, encode=yes]

\question[score=0.5, penalty=0.125, brief=first]{1}
{Stem 1}
%%
{Key}
%%
{Distractor 1}
%%
{Distractor 2}
%%
{Distractor 3}
%%
\question[score=0.5, penalty=0.125, brief=second, style=horizontal]{2}
{Stem 2}
%%
{Key}
%%
{Distractor 1}
%%
{Distractor 2}
%%
{Distractor 3}
%
\question[score=0.5, penalty=0.125, brief=third, style=list]{3}
{Stem 3}
%%
{Key}
%%
{Distractor 1}
%%
{Distractor 2}
%%
{Distractor 3}
\end{exam}
\end{document}
```
Notice that the `\qrgraderpagestyle{}` command must also be used to guarantee the presence of the page-number-related QRs in every page.

The script takes several additional flags: 

```
  -p, --process         Process source folder (main.tex)
  -f FILENAME, --filename FILENAME
                        Specify .tex filename
  -n NUMBER, --number NUMBER
                        Number or exams to be generated (1)
  -j THREADS, --threads THREADS
                        Maximum number of threads to use (4)
  -b BEGIN, --begin BEGIN
                        First exam number
  -v, --verbose         Extra verbosity
  -k, --feedback        Generate feedback file
  -P PAGES, --pages PAGES
                        Acceptable number of pages of output PDF
```
All the script **must be run from the root of the workspace**. An example of basic use would be:

```
$ cd qrgrading-221215
$ qrgenerator -p -n 4 
```
where we are asking the script to generate 100 exams with filenames from `221215001.pdf` to `221215004.pdf`.

A more advanced use would be:
```
$ qrgenerator -p -n 100 -b 250 -p 10 -j 2
```
where we are instead asking it to generate 100 exams with filenames from `221215250.pdf` to `221215349.pdf` using only 2 threads and specifying that only 10-pages exams are acceptable (sometimes not all the examan have the same number of pages due to the different distribution of questions).

The script will generate the correpondent PDF files and the `results/xls/generated.txt` file that collects the information about all the QR generated by the `qrgenerator` for each exam (position and content).

The `-k` flag is automatically set when the `-p` is used and forces the generation of the `results/xls/221215_feedback.csv` file that contains the relationship between the actual questions with the exam-specific questions. This flag can also be used alone to re-creathe the cited file if it was lost.

## qrscanner ##

Once the exams have been filled by the students, all the pages must be scanned (generally at 400 DPI and using the color/text option) and scanned using the `qrscanner` script. The PDF file containing all the scanned exams must be put inside the `scanned` directory of the workspace. After that the script must be run from the root of the workspace:

```
$ qrscanner -p
```

With the `-p` flag, the script will process the PDF file and will scan **all the PDF files** in the `scanned` directory and will generate all the reconstructed exams in PDF format in the `results/publish` directory and the files `221215_raw.csv` and `221215_nia.csv` in the `results/xls` directory. The first file contains a matrix that collects all the answers given by the student sorted like in the original LaTex file and the second a table that associates the student identification number with the exam id number.

Thus, we will have:
```
$ ls qrgrading-221215/results/xls
-rw-rw-r-- 1 danilo danilo 16297 jul 19 12:28 221215_feedback.csv
-rw-rw-r-- 1 danilo danilo   702 jul 19 12:28 221215_nia.csv
-rw-rw-r-- 1 danilo danilo  8580 jul 19 12:28 221215_raw.csv
```
The `qrscanner` script has several flags that can modify its behavior:
```
  -T THRESHOLD [THRESHOLD ...]            Thresholding values (default: {50, 55, 60, 65, 70, 75, 80}, 0: no thresholding)
  -d DPI, --dpi DPI                       Input file DPI (default: 400)
  -z, --zxing                             Use ZXing
  -b, --zbar                              Use Zbar  
```
Usually, the default values are good enough so, processing using `-p` should be sufficient. The `-b` option forces the use of the `zbar` detector (instead of the default `zxing`) which is incapable of recognizing `Aztec` codes.

It is possible to specify the first and last page to be scanned (useful for debugging purposes):
```
  -B FIRST_PAGE, --first-page FIRST_PAGE  First page to be processed (default: 1)
  -E LAST_PAGE, --last-page LAST_PAGE     Last page to be processed (default: last)
```
The `-p` option also reconstruct the exams that can be found in the `results/pdf` folder.

The `-a` flag allows to annotate the reconstructed PDF files in different ways. 

``` 
  -a all: Annotates all the recognized QR/Aztec in blue
  -a answers: Annotates all and only the answers given by the students (red for wrong answer, green for correct answer)
  -a correct: Annotates the correct answer in green
```

This flag can also be multiples times and with different values **after** the scanned file have been processed but the new generated files will be overwritten.

## Google Drive ##

The `-W` flag allows specifying the Google Sheet Workbook where the data will be uploaded.

Assuming there is a workbook online called SAU2021-22 the command:
```
$ qrscanner -W SAU2021-22
```
will:

1. Creates a table called `221215_raw` table with the content of `results/xls/221215_raw.csv`
2. Creates a table called `221215_feedback` from the file `results/xls/221215_feedback.csv`
3. Creates a table called `221215_nia` from the file `results/xls/221215_nia.csv`


## qrgrader ##
To visualize the exams and being able to correct the mistakes that could have been made during the exam by the students (for example doble answer to a question) you can use the `qrgrader` tool.

Move to the qr workspace and type:

```
$ qrgrader
```
A Qt-based app will show up where you can modify the marks just clicking on the annotations shown in red or green. If multiple answers have been selected for the same question, all the annotation will be shown in yellow. You can click those that the student did not intend to mark to remove them.
