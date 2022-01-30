# NodeMerge

(c) Jukka Purma, 2022

This project contains attempts to build syntactic operation Merge and simple parsing from relatively simple computational nodes. Nodes assumed here are bit more complex than typical building blocks of artificial neural networks, but complexity of biological neurons leaves us some room for imagination.

Requires python 3.7 (probably) or newer, up to python 3.9, as gui library used for drawing does not yet support python 3.10. 

Install requirements () with `pip3 install -r requirements.txt`, then: 

    python3 main.py

The first attempt has still lots of glue logic, operations and states that happen because of the program/parser state instead of being triggered by node activation. Converting these imperfections to node activation will make the network more complicated and difficult to follow, so I will probably be creating next versions as modified copies of the current main.py.

The parser here is a simplification of parser being developed as TreesAreMemory3 -plugin in https://github.com/jpurma/Kataja