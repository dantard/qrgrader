# QRGRADER

<img src="images/logo.png" alt="drawing" width="300"/>

## Index

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Instalación](#installation)
    - [Installation from PyPI](#installation-from-pypi)
    - [Installation from source](#installation-from-source)
- [Usage](#usage)
    - [Creating a new workspace](#creating-a-new-workspace)
    - [Preparing the exam](#preparing-the-exam)
    - [Generating the exams](#generating-the-exams)
    - [Grading the exams](#grading-the-exams)
    - [Graphical user interface](#graphical-user-interface)
    - [Annotating the exams](#annotating-the-exams)
- [First Exam: Simulation](#first-exam-simulation)
    - [First step: generate the simulated exam](#first-step-generate-the-simulated-exam)
    - [Second step: simulate the exam](#second-step-simulate-the-exam)
    - [Third step: grading the exams](#third-step-grading-the-exams)
    - [Fourth step: check the results](#fourth-step-check-the-results)
    - [Fifth step: annotate the exams](#fifth-step-annotate-the-exams)
- [CSV files format details](#csv-files-format-details)

## Introduction

QRGrader is a set of scripts that allows you to generate and grade multiple choice exams using QR codes. The script will generate a QR code for each question
and the correct answer. Students can scan the QR code to check their answers. The script will also generate a summary of the results for each question.

This README file is a guide to use the scripts. The scripts are designed to be used in a specific order, so it is important to follow the instructions
carefully.

In the following sections, we will explain how to install and use the scripts, how to generate the exams, how to grade the exams, and how to annotate the exams.

You can also jump to the [First Exam: Simulation](#first-exam-simulation) which is designed to verify that everything is functioning properly. We will simulate
an exam scenario to ensure the scripts perform as expected. Running this test beforehand helps confirm that everything is working correctly before deploying the
scripts in a real exam setting.

QRGrader is a simple python script that allows you to grade
multiple choice questions using QR codes. The script will generate a QR code for each question and the correct answer.
Students can scan the QR code to check their answers. The script will also generate a summary of the results for each
question.

The exam must the prepared in a latex file using the style document provided.

## Prerequisites (Linux)

- Python 3.12
- `texlive-full`

To install `texlive-full` on Ubuntu, run the following command:

```bash
sudo apt install texlive-full
```

## Prerequisites (Windows)

- Python 3.12
- [Miktex](https://miktex.org/)
- [Visual C++ Redistributable for Visual Studio 2015](https://www.microsoft.com/en-us/download/details.aspx?id=48145)
- [Media Feature Pack for Windows](https://support.microsoft.com/en-us/topic/media-feature-pack-list-for-windows-n-editions-c1c6fffa-d052-8338-7a79-a4bb980a700a)

## Installation

### Installation from PyPI

To install the scripts from the Python Packages Index, run the following command:

```bash
$ pip install qrgrader
```

### Installation from source

In this case you need to have `git`already installed. To install the scripts from source, run the following command:

```bash
$ git clone https://github.com/dantard/qrgrading.git
$ cd qrgrader
$ pip install .
```

## Usage

All the script command must be executed inside the so-called qr workspace which is
a directory tree called `qrgrading-DDDDDD` with the following structure:

```

qrgrading-250212
├── data
├── source
├── generated
├── scanned
├── results
├── xls
├── pdf

```

### Creating a new workspace

To create a new workspace, run the following command in a terminal:

```bash
$ qrworkspace -d 250312
Workspace 'qrgrader-250312' created successfully.
```

Generally, the number is the date of the exam. If the scripts is called
without the `-d` option, the current date will be used.

Once created the workspace, the source directory will contain a file called `qrgrading.sty` which is the style file used to generate the exams and another file
called `main.tex` which is a sample exam that can be personalized according to the needs of the exam.

### Preparing the exam

The following is preparing the exam. The source files must be in the `source` directory.

The exam has the following structure:

```latex
\documentclass[oneside,spanish]{article}
\usepackage[aztec, draft]{qrgrading}
\qrgraderpagestyle{Subject name or exam title}

\begin{document}

    \IDMatrix{0.6cm}{\uniqueid}{Student ID figure}

    \begin{exam}[shuffle=all, style=matrix, showcorrect=no, encode=yes]

        \question[score=0.5, penalty=0.125, brief=first]{1}
        {Stem 1}
        {Key}
        {Distractor 1}
        {Distractor 2}
        {Distractor 3}

%%

        \question[score=0.5, penalty=0.125, brief=second, style=horizontal]{2}
        {Stem 2}
        {Key}
        {Distractor 1}
        {Distractor 2}
        {Distractor 3}

%%

        \question[score=0.5, penalty=0.125, brief=third, style=list]{3}
        {Stem 3}
        {Key}
        {Distractor 1}
        {Distractor 2}
        {Distractor 3}
    \end{exam}
\end{document} 
```

For the moment it is only possible to have four possible answers.

The main file must be called `main.tex`.

The exam environment has the following options:

- `shuffle`: The questions can be shuffled. The options are `all`, `questions`, `answers`, and `none`.
- `style`: The default style of the exam. The options are `matrix`, `horizontal`, and `list`.
- `showcorrect`: Show the correct answers. The options are `yes` and `no`.
- `encode`: Encode the answers in the QR code. The options are `yes` and `no`.

The `question` has six parameters:

- Question number (must be a number and they must be consecutive)
- Stem of the question
- Four answer options (key and distractors)

Its environment has the following options (all are optional):

- `score`: The score of the question.
- `penalty`: The penalty of the question.
- `brief`: A brief description of the question.
- `style`: The style of the question. The options are `matrix`, `horizontal`, and `list`.

Any Latex code that works inside an environment can be used inside the `question` environment. On the other cases, it is useful to prepare the code in a
different file and use the `\input` command inside the `question` environment.

### Generating the exams

To generate the exams run the following command:

```bash
$ qrgenerator -n 10
** Starting parallelized generation (using 4 threads)
Creating exam 250327001 (0 ready)
Creating exam 250327002 (0 ready)
Creating exam 250327003 (0 ready)
Creating exam 250327004 (0 ready)
Creating exam 250327005 (1 ready)
Creating exam 250327006 (2 ready)
Creating exam 250327007 (3 ready)
Creating exam 250327008 (4 ready)
Creating exam 250327009 (5 ready)
Creating exam 250327010 (6 ready)
Done (10 exams generated).
Creating generated.csv file...Done.
Creating questions.csv file...Done.
``` 

Where `-n` is the number `N` of exams to generate.
In this example the `qrgenerator` will generate 10 exams in the `generated` directory in PDF format. Both the order of the questions and the answers will be
different for
each exam. The file name will have the format `DDDDDDNNN.pdf` where `DDDDDD` is the date of the exam
and `NNN` is the number of the exam from `001` to `NNN`, in this case `010`.

They will have the following aspect (naturally, the content can be personalized):

![images/img_3.png](images/img_3.png)

### Marking the exams

The exams must be printed in a normal printer. The students must mark the answers with a pen or a pencil over the QR code. The system is robust and basically
any mark will do.

The only thing that must be taken into account is that the QR code must be marked with a pen or a pencil and the marks must be inside the QR code.

### Grading the exams

Once the students have answered the exam, the exams must be scanned at 400dpi/color with a normal scanner.
The scanned files must be put afterwards in the `scanned` directory.
The grading is carried out with the following command:

```bash
$ qrscanner -p
qrscanner -p 
Processing file 250327001.pdf
Processing file 250327002.pdf
Processed /home/danilo/work/qrgrader/qrgrader-250327/scanned/250327001.pdf page 1 
Processed /home/danilo/work/qrgrader/qrgrader-250327/scanned/250327002.pdf page 1 
Processed /home/danilo/work/qrgrader/qrgrader-250327/scanned/250327001.pdf page 0 
Processed /home/danilo/work/qrgrader/qrgrader-250327/scanned/250327002.pdf page 0 
Reconstructing exams
Creating NIA xls file
Creating RAW xls file
All done :)
```

This command will process the and generate a set of files in the `results` directory.
Specifically, the `results/pdf` directory will contain the recontructed pdf files named in the same
way as the generated files.

On the other hand, the `results/xls` directory will contain the results in a set of
csv files as follows:

- `DDDDDD_raw.csv`: A file in which each row contains the exam number, and a set of `1 and `0` and values organized in group of
  4 that resent wether or not the student has marked a specific question
- `DDDDDD_nia.csv`: A file in which each row contains the exam number and the student ID
- `DDDDDD_questions.csv`: A file in which each row contains a information about the questions (actually generated by ```qrgenerator```during the generation
  step)

These files opened with a spreadsheet program will allow to grade the exams.

### Graphical user interface

Sometimes, students mark an answer, and later they want to modify that answer.
Since it is impossible to erase the QR code, in these cases they are instructed to mark  
also the chosen answer and write "NO" beside the answer they want to erase.
It will result in an question with two marked answers that can be easily identified.
To facilitate the grading of these cases, we created a graphical user interface that allows to
unmark the answer that has been marked by mistake.
To use the graphical user interface, run the following command from within the workspace directory

```bash
$ qrgrader
```

The graphical user interface will open as follows:
![img.png](images/img_1.png)

On the left side the exam number is shown, and the PDF file is displayed on the right side.
The marked answers are shown in green and red. When a question has two marks,
both answers are shown in yellow. Double-clicking on the answer will unmark it.

### Annotating the exams

Once all the double marks have been removed, the exams can be annotated to show
the correctly and incorrecly marked answers in the PDF itself that can be given to the students as a feedback. To do this, run the following command:

```bash
$ qrscanner -a
Annotating exams
All done :)
```

This will annotate the PDF files in the `results/pdf` directory with the correct and incorrect answers. The questions will be marked in green and red,
respectively as follows:

![images/img_4.png](images/img_4.png)

## First Exam: Simulation

To check that everything is working correctly, you can run the whole process on a simulated exam.

### First step: generate the simulated exam

Since when the qrworkspace is created, the a bogus `main.tex` and `qrgrading.sty` files are created, you can run the following command to generate a simulated
exam:

```bash
$ qrworkspace -d 250312
$ Workspace 'qrgrader-250312' created successfully.
```

As commented earlier, the `qrworkspace` command will create a directory called `qrgrading-250312`.

Change to the `qrgrading-250312` directory by running the following command:

```bash
$ cd qrgrader-250312
```

Then, you can run the following command to generate a ten bogus exams:

```bash
$ qrgenerator -n 10
```

This will generate 10 exams in the `generated` directory.

### Second step: simulate the exam

Now, it is possible to use the qrscanner application to randomly mark these exams and copy them into
the scanned directory as if they were scanned exams. This can be done as follows:

```bash
$ qrscanner -S 10
```

This will create 10 randomly marked exams in the `scanned` directory.

### Third step: grading the exams

Now, you can run the grading process as follows:

```bash
$ qrscanner -p
```

This will process the scanned exams and generate the results in the `results` directory.

### Fourth step: check the results

Subsequently, you can run the graphical user interface to check the results:

```bash
$ qrgrader
```

With the interface you can unmark the hypothetical double marks.

### Fifth step: annotate the exams

Once done, you can annotate the exams with the correct and incorrect answers as follows:

```bash
$ qrscanner -a
```

and you are done!

## CSV files format details

The `DDDDDD_raw.csv` file has the following format (the space are \t  (tabs) in the file):

```
DDDDDD NNN Q1A Q1B Q1C Q1D Q2A Q2B Q2C Q2D Q3A Q3B Q3C Q3D
```

as for example:

```
250319 1 0 0 1 0 1 0 0 0 1 0 0 0
```

Where `DDDDDD` is the date of the exam, `NNN` is the number of the exam, and
`Q1A` is the `A` option, Q1B is the `B` option, and so on. If the student has marked the option, the value is `1`,
otherwise `0`.

-----
The `nia.csv` file has the following format:

```
DDDDDDNNN NIA
```

as for example:

```
250319001 123456
```

Where `DDDDDD` is the date of the exam, `NNN` is the number of the exam, and `NIA` is
the student ID. Notice that in this case the
-----

The `questions.csv` file has the following format:

```
N TYPE SA SB SC SD BRIEF
```

as for example:

``` 
1 Q 0.5 -0.1 -0.1 -0.1 for_loop
2 Q 0.5 -0.1 -0.1 -0.1 error_handling
3 Q 0.5 -0.1 -0.1 -0.1 sintax_error
```

Where `N` is the question number, `TYPE` is the question type, `SA`, `SB`, `SC`, and `SD` are the scores for each
option, and `BRIEF` is a brief description of the question that are all recovered automatically from
the latex file.
