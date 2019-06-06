"""Read the circuit definition file and translate the characters into symbols.

Used in the Logic Simulator project to read the characters in the definition
file and translate them into symbols that are usable by the parser.

Classes
-------
Scanner - reads definition file and translates characters into symbols.
Symbol - encapsulates a symbol and stores its properties.
"""

import os


class Symbol:
    """Encapsulate a symbol and store its properties.

    Parameters
    ----------
    type:    Symbol type
    id:      Symbol ID
    linenum: Line number in definition file
    colnum:  Column number in definition file

    Public methods
    --------------
    No public methods.
    """

    def __init__(self, type, id, linenum, colnum):
        """Initialise symbol properties."""
        self.type = type
        self.id = id
        self.linenum = linenum
        self.colnum = colnum


class Scanner:
    """Scanner: Read circuit definition file and translate the characters into
    symbols.

    Once supplied with the path to a valid definition file, the scanner
    translates the sequence of characters in the definition file into symbols
    that the parser can use. It also skips over comments and irrelevant
    formatting characters, such as spaces and line breaks.

    Parameters
    ----------
    path: path to the circuit definition file.
    names: instance of the names.Names() class.

    Public methods
    -------------
    get_next_character(self): getting the next character in definition file
    get_next_non_whitespace_character(self): getting the next non-white space
                                             character in definition file
    comment_check(self): function to set up the comment skipping
    get_symbol(self): Translates the next sequence of characters into a symbol
                      and returns the symbol.
    print_line(self, linnum, colnum): function which returns a formatted
                                      string at the specified location
                                      for error messages
    """

    def __init__(self, path, names):        # add path, names
        """Open specified file and initialise reserved words and IDs."""

        self.filesize = os.path.getsize(path)
        self.current_position = 0
        self.defi_file = open(path)
        self.names = names
        self.current_char = " "
        self.line_counter = 1
        self.col_counter = 0
        self.comment_switch = 0

        LIST_KEYWORD = ['DEVICE_LIST', 'CONNECTION_LIST', 'MONITOR_LIST',
                        'END']
        DEVICE_KEYWORD = ['AND', 'NAND', 'OR', 'NOR', 'XOR', 'DTYPE', 'CLOCK',
                          'SWITCH', 'SIGGEN']
        PUNCTUATION = [':', ';', '->', '.']
        INITIAL_STATE = ['OFF', 'ON']
        [self.EOF] = self.names.lookup([""])
        self.types = [self.KEYWORDS, self.DEVICETYPE, self.NAMES,
                      self.PROPERTY, self.NUMBER, self.CL, self.SCL,
                      self.AR, self.PE] = range(9)
        self.punctuation = [self.COLON, self.SEMI_COLON, self.ARROW,
                            self.PERIOD] = self.names.lookup(PUNCTUATION)
        self.initial_states = [self.OFF,
                               self.ON] = self.names.lookup(INITIAL_STATE)
        self.keywords_list = [self.DEVICE_LIST, self.CONNECTION_LIST,
                              self.MONITOR_LIST,
                              self.END] = self.names.lookup(LIST_KEYWORD)
        self.device_keywords = [self.AND, self.NAND, self.OR, self.NOR,
                                self.XOR, self.D_TYPE, self.CLOCK,
                                self.SWITCH, self.SIGGEN
                                ] = self.names.lookup(DEVICE_KEYWORD)

    def get_next_character(self):
        """getting the next character in definition file"""
        charac = self.defi_file.read(1)
        self.col_counter += 1
        self.current_position += 1
        if charac == "\n":
            self.line_counter += 1
            self.col_counter = 0
            if self.comment_switch == 1:
                self.comment_switch = 0
        return charac

    def get_next_non_whitespace_character(self):
        """getting the next non-white space character in definition file"""
        for i in range(self.current_position, self.filesize):
            charac = self.get_next_character()
            if not charac.isspace():
                return charac

    def comment_check(self):
        """function to set up the comment skipping"""
        if self.current_char == '/':
            self.current_char = self.get_next_character()
            if self.current_char == '/':                  # single line comment
                self.comment_switch = 1
            if self.current_char == '*':                  # multi line comment
                self.comment_switch = 2
            self.current_char = self.get_next_non_whitespace_character()
            while self.comment_switch != 0:
                if not self.current_char:
                    break
                if self.comment_switch == 2:
                    if self.current_char == '*':
                        self.current_char = self.get_next_character()
                        if self.current_char == '/':
                            self.comment_switch = 0
                self.current_char = self.get_next_non_whitespace_character()
            self.comment_check()

    def get_symbol(self):
        """function to return the next symbol and its parameters in a class
        for each symbol in the definition file
        """
        type = None
        id = None

        if not self.current_char:
            return Symbol(None, self.EOF, self.line_counter, self.col_counter)

        if self.current_char.isspace():
            self.current_char = self.get_next_non_whitespace_character()

        self.comment_check()

        colnum = self.col_counter
        linenum = self.line_counter

        if not self.current_char:
            return Symbol(None, self.EOF, self.line_counter, self.col_counter)

        if self.current_char.isdigit():
            num_string = ""
            while self.current_char.isdigit():
                num_string += str(self.current_char)
                self.current_char = self.get_next_character()
            type = self.NUMBER
            [id] = self.names.lookup([num_string])

        elif self.current_char.isalpha():
            word = ""
            while self.current_char.isalnum() or self.current_char == '_':
                word += self.current_char
                self.current_char = self.get_next_character()
            [id] = self.names.lookup([word])

            if id in self.keywords_list:
                type = self.KEYWORDS

            elif id in self.device_keywords:
                type = self.DEVICETYPE

            elif id in self.initial_states:
                type = self.PROPERTY

            else:
                type = self.NAMES

        else:
            if self.current_char == ':':
                type = self.CL
                id = self.COLON

            elif self.current_char == ';':
                type = self.SCL
                id = self.SEMI_COLON

            elif self.current_char == '.':
                type = self.PE
                id = self.PERIOD

            elif self.current_char == '-':
                self.current_char = self.get_next_character()
                if self.current_char == '>':
                    type = self.AR
                    id = self.ARROW

            else:
                [id] = self.names.lookup([str(self.current_char)])

            self.current_char = self.get_next_character()

        return Symbol(type, id, linenum, colnum)

    def print_line(self, linnum, colnum):
        """function which returns a formatted string at the specified location
        for error messages
        """
        self.defi_file.seek(0)
        line_string = ""
        i = 1
        for line in self.defi_file:
            if i == linnum:
                linesize = len(line)
                if colnum < 37 or linesize < 73:
                    line_string = line
                    blanks = " " * (colnum - 1)
                elif colnum + 37 > linesize:
                    line_string = "..." + line[linesize - 73:]
                    blanks = " " * (colnum - linesize + 75)
                else:
                    line_string = ("..." +
                                   line[colnum - 36: colnum + 37] +
                                   "...\n")
                    blanks = " " * 38
                print_string = "".join([line_string, blanks, "^"])
                return print_string
            i += 1
        return "\n^"
