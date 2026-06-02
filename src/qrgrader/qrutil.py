import sys


def main():
    for i in range(int(sys.argv[1])):
        with open(f"open_{i+1:02d}.tex", "w", encoding='utf-8') as f:
            f.write("\\begin{lstlisting}[style=fundinf]\n# Su solucion debajo de la linea\n"
                    "#-------------------------------------------------------------------------------"
                    "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
                    "#-------------------------------------------------------------------------------"
                    "\n\\end{lstlisting}")
        with open(f"open_{i+1:02d}e.tex", "w", encoding='utf-8') as f:
            f.write("\\begin{lstlisting}[style=fundinf]\n\n\n\\end{lstlisting}")

    for i in range(int(sys.argv[2])):
        with open(f"quiz_{i+1:02d}.tex", "w", encoding='utf-8') as f:
            f.write("\\begin{lstlisting}[style=fundinf]\n\n\n\\end{lstlisting}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: qrutil.py <number_of_opens> <number_of_quizzes>")
        sys.exit(1)
    main()
