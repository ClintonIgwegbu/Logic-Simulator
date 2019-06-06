"""Parse the definition file and build the logic network.

Used in the Logic Simulator project to analyse the syntactic and semantic
correctness of the symbols received from the scanner and then builds the
logic network.

Classes
-------
Parser - parses the definition file and builds the logic network.
"""


class Parser:

    """Parse the definition file and build the logic network.

    The parser deals with error handling via the ErrorHandling class. It
    analyses the syntactic and semantic correctness of the symbols it receives
    from the scanner, and then builds the logic network. If there are errors
    in the definition file, the parser detects this and tries to recover from
    it, giving helpful error messages.

    Parameters
    ----------
    names: instance of the names.Names() class.
    devices: instance of the devices.Devices() class.
    network: instance of the network.Network() class.
    monitors: instance of the monitors.Monitors() class.
    scanner: instance of the scanner.Scanner() class.

    Public methods
    --------------
    parse_network(self): Parses the circuit definition file.

    devicelist(self): Determine the device list from the definiton file.

    connectionlist(self, semantic_checks=True): Determine the connection list
                                                from the definition file.

    monitorlist(self, semantic_checks=True): Determine the monitor list
                                             from the definition file.

    device(self): Parse through device details, and make device.

    connect(self): Parse through connection details, and make connection.

    connect_syntax(self): Parse through connection details, checking the
                          syntax.

    monitor(self): Parse through outputs to monitor, making new monitor
                   points.

    monitor_syntax(self): Parse through outputs to monitor, checking the
                          syntax.

    check_keyword(self, keyword): Checks to see if keyword is present.

    build_list(self, expected_type, method): Build up list using the
                                             method provided.

    check_syntax(self, expected_type, method): Check the syntax for the
                                               current list.

    check_end(self, error_recovery=True): Checks to see if END is present.

    check_valid_name(self, id): Checks to see if name is valid.

    get_property(self, type): Check that the current symbol is a valid
                              property. type determines whether the
                              property should be a number,
                              or the INISTATE "OFF" or "ON".

    get_io(self, io): Retrieves corresponding port ID for current symbol.
                      io is either self.OUTPUT or self.INPUT.
                      Returns (device_id, port_id).

    check_io(self, io): Check syntax for io.

    error(self, error_type, advance_symbol, vararg=None): Handle the error
                                                          the parser has
                                                          encountered.

    error_report(self): Build and display the error report.
    """

    def __init__(self, names, devices, network, monitors, scanner):
        """Initialise constants."""

        self.names = names
        self.devices = devices
        self.network = network
        self.monitors = monitors
        self.scanner = scanner

        self.error_count = 0
        self.error_messages = []

        self.missing_end = False
        self.reached_eof = False

        [self.SYNTAX_COLON, self.KEYWORD_ERROR,
         self.SYMBOL_TYPE_ERROR, self.NO_DEVICE,
         self.BAD_NAME, self.NOT_VALID_NAME,
         self.SYNTAX, self.END_ERROR,
         self.IDENTIFIER_PRESENT, self.UNCONNECTED_INPUTS,
         self.NO_MONITOR, self.NO_IDENTIFIER,
         self.NO_EOF] = self.names.unique_error_codes(13)

        [self.INPUT, self.OUTPUT] = range(2)

        self.symbol_types = [self.KEYWORDS, self.DEVICETYPE,
                             self.NAMES, self.PROPERTY,
                             self.NUMBER, self.CL, self.SCL,
                             self.AR, self.PE] = ["KEYWORD", "DEVICE TYPE",
                                                  "NAME", "INITIAL STATE",
                                                  "NUMBER", "COLON",
                                                  "SEMI COLON", "ARROW (->)",
                                                  "PERIOD (.)"]

    def parse_network(self):
        """Parse the circuit definition file."""

        self.symbol = self.scanner.get_symbol()

        # Start parsing file. First declaration must be a device list
        if not self.devicelist():
            print("Errors encountered in device list. "
                  "Will now check for syntax errors in rest of file.")
            self.connectionlist(False)
            self.monitorlist(False)
        else:
            if not self.connectionlist():
                print("Errors encountered in connection list. "
                      "Will now check for syntax errors in monitor list.")
                self.monitorlist(False)
            else:
                self.monitorlist()

        if (self.symbol.id == self.scanner.EOF and
                not self.error_count):
            print("Parsing complete.")
            return True

        # Errors encountered whilst parsing
        error_string = ("Parsing complete. Unable to build network. " +
                        str(self.error_count) +
                        " error(s) found:")
        dashes = "-" * len(error_string)
        print("\n".join([dashes, error_string, dashes]))
        self.error_report()
        return False

    def devicelist(self):
        """Determine the device list from the definiton file."""

        if self.reached_eof:
            return

        print("Parsing device list...")

        # First symbol expected is "DEVICE_LIST"
        if not self.check_keyword(self.scanner.DEVICE_LIST):
            return False

        # Build list
        if not self.build_list(self.scanner.DEVICETYPE, self.device):
            if not self.missing_end:
                self.check_end()
            else:
                self.missing_end = False
            return False

        # Expect the "END" keyword
        self.check_end()

        return True

    def connectionlist(self, semantic_checks=True):
        """Determine the connection list from the definition file."""

        if self.reached_eof:
            return True

        print("Parsing connection list...")

        # Symbol expected is "CONNECTION_LIST"
        if not self.check_keyword(self.scanner.CONNECTION_LIST):
            return False

        # Build list
        if semantic_checks:
            if not self.build_list(self.scanner.NAMES, self.connect):
                if not self.missing_end:
                    self.check_end()
                else:
                    self.missing_end = False
                return False
        else:
            self.check_syntax(self.scanner.NAMES, self.connect_syntax)
            if self.missing_end:
                self.missing_end = False
                return

        if semantic_checks and not self.network.check_network():
            self.error(self.UNCONNECTED_INPUTS, False)
            self.check_end()
            return False

        # Expect the "END" keyword
        self.check_end()

        return True

    def monitorlist(self, semantic_checks=True):
        """Determine the monitor list from the definition file."""

        if self.reached_eof:
            return

        print("Parsing monitor list...")

        # Symbol expected is "MONITOR_LIST"
        if not self.check_keyword(self.scanner.MONITOR_LIST):
            return

        # Build list
        if semantic_checks:
            self.build_list(self.scanner.NAMES, self.monitor)
            if not self.monitors.monitors_dictionary:
                self.error(self.NO_MONITOR, False)
        else:
            self.check_syntax(self.scanner.NAMES, self.monitor_syntax)

        # Expect the "END" keyword
        self.check_end(False)

        # Expect EOF
        if self.symbol.id != self.scanner.EOF:
            self.error(self.NO_EOF, False)

    def device(self):
        """Parse through device details, and make device."""

        # Check to see if device type is valid
        type = self.symbol.id
        if type not in self.scanner.device_keywords:
            self.error(self.NO_DEVICE, True)
            return False

        self.symbol = self.scanner.get_symbol()

        # Expecting a name
        if self.symbol.type == self.scanner.NAMES:
            id = self.symbol.id

            # Check to see if name is valid
            if not self.check_valid_name(id):
                self.error(self.NOT_VALID_NAME, True)
                return False

            property = None
            self.symbol = self.scanner.get_symbol()

            # Not all devices require PROPERTY
            if (self.symbol.type == self.scanner.PROPERTY or
                    self.symbol.type == self.scanner.NUMBER):
                property = self.get_property(type)
                self.symbol = self.scanner.get_symbol()

            # Make device
            error_type = self.devices.make_device(id,
                                                  type,
                                                  property)

            if error_type is not self.devices.NO_ERROR:
                self.error(error_type, True, type)
                return False

            if self.symbol.type == self.scanner.SCL:
                self.symbol = self.scanner.get_symbol()
            else:
                self.error(self.SYNTAX, True, self.scanner.SEMI_COLON)
                return False
        else:
            self.error(self.BAD_NAME, True)
            return False

        return True

    def connect(self):
        """Parse through connection details, and make connection."""

        # Expecting output
        output_id, output_port_id = self.get_io(self.OUTPUT)
        if (output_id, output_port_id) == (None, None):
            return False

        if self.symbol.type == self.scanner.AR:
            self.symbol = self.scanner.get_symbol()

            # Expecting input
            if self.symbol.type == self.scanner.NAMES:
                input_id, input_port_id = self.get_io(self.INPUT)
                if (input_id, input_port_id) == (None, None):
                    return False

                # Make connection
                error_type = self.network.make_connection(input_id,
                                                          input_port_id,
                                                          output_id,
                                                          output_port_id)
                if error_type is not self.network.NO_ERROR:
                    self.error(error_type, True)
                    return False

                if self.symbol.type == self.scanner.SCL:
                    self.symbol = self.scanner.get_symbol()
                else:
                    self.error(self.SYNTAX, True, self.scanner.SEMI_COLON)
                    return False
            else:
                self.error(self.SYMBOL_TYPE_ERROR, True, self.NAMES)
                return False
        else:
            self.error(self.SYNTAX, True, self.scanner.ARROW)
            return False

        return True

    def connect_syntax(self):
        """Parse through connection details, checking syntax."""

        # Expecting output
        if not self.check_io(self.OUTPUT):
            return

        if self.symbol.type == self.scanner.AR:
            self.symbol = self.scanner.get_symbol()

            # Expecting input
            if self.symbol.type == self.scanner.NAMES:
                if not self.check_io(self.INPUT):
                    return

                if self.symbol.type == self.scanner.SCL:
                    self.symbol = self.scanner.get_symbol()
                else:
                    self.error(self.SYNTAX, True, self.scanner.SEMI_COLON)
            else:
                self.error(self.SYMBOL_TYPE_ERROR, True, self.NAMES)
        else:
            self.error(self.SYNTAX, True, self.scanner.ARROW)

    def monitor(self):
        """Parse through outputs to monitor, making monitor points."""

        # Expecting output
        output_id, output_port_id = self.get_io(self.OUTPUT)
        if (output_id, output_port_id) == (None, None):
            return

        # Make monitor
        error_type = self.monitors.make_monitor(output_id, output_port_id)
        if error_type is not self.monitors.NO_ERROR:
            self.error(error_type, True)
            return

        if self.symbol.type == self.scanner.SCL:
            self.symbol = self.scanner.get_symbol()
        else:
            self.error(self.SYNTAX, True, self.scanner.SEMI_COLON)

    def monitor_syntax(self):
        """Parse through outputs to monitor, checking syntax."""

        # Expecting output
        if not self.check_io(self.OUTPUT):
            return

        if self.symbol.type == self.scanner.SCL:
            self.symbol = self.scanner.get_symbol()
        else:
            self.error(self.SYNTAX, True, self.scanner.SEMI_COLON)

    def check_keyword(self, keyword):
        """Checks to see if keyword is present."""

        if self.symbol.id == keyword:
            self.symbol = self.scanner.get_symbol()
            if self.symbol.type == self.scanner.CL:
                self.symbol = self.scanner.get_symbol()
                return True
            else:
                self.error(self.SYNTAX_COLON, True)
        else:
            self.error(self.KEYWORD_ERROR, True, keyword)

        return False

    def build_list(self, expected_type, method):
        """Build up list using the method provided."""

        success = True

        while (self.symbol.id != self.scanner.END and
                self.symbol.id != self.scanner.EOF):

            if self.symbol.type == expected_type:
                if not method():
                    success = False
            elif (self.symbol.type == self.scanner.KEYWORDS or
                    self.symbol.type == self.scanner.CL):
                self.error(self.END_ERROR, False)
                success = False
                self.missing_end = True
                break
            else:
                self.error(self.SYMBOL_TYPE_ERROR, True,
                           self.symbol_types[expected_type])
                success = False

        return success

    def check_syntax(self, expected_type, method):
        """Check the syntax for the current list."""

        while (self.symbol.id != self.scanner.END and
                self.symbol.id != self.scanner.EOF):
            if self.symbol.type == expected_type:
                method()
            elif (self.symbol.type == self.scanner.KEYWORDS or
                    self.symbol.type == self.scanner.CL):
                self.error(self.END_ERROR, False)
                self.missing_end = True
                break
            else:
                self.error(self.SYMBOL_TYPE_ERROR, True,
                           self.symbol_types[expected_type])

    def check_end(self, error_recovery=True):
        """Checks to see if END is present."""

        # Expect the "END" keyword
        if self.symbol.id == self.scanner.END:
            self.symbol = self.scanner.get_symbol()
        else:
            self.error(self.END_ERROR, error_recovery)

    def check_valid_name(self, id):
        """Checks to see if name is valid."""

        if not self.devices.get_device(id):
            return True

        return False

    def get_property(self, type):
        """Check that the current symbol is a valid property.

        type determines whether the property should be a number,
        or the INISTATE "OFF" or "ON".
        """

        property = self.symbol.id

        # Check if device is switch
        if (type == self.devices.SWITCH and
                property in self.scanner.initial_states):
            if property == self.scanner.OFF:
                return self.devices.LOW
            return self.devices.HIGH

        elif self.symbol.type == self.scanner.NUMBER:
            prop = self.names.get_name_string(property)
            # If device is siggen, keep property as str,
            # otherwise cast it into an int
            if type == self.devices.SIGGEN:
                property = prop
            else:
                property = int(prop)
            return property

        return None

    def get_io(self, io):
        """Retrieves corresponding port ID for current symbol.

        io is either self.OUTPUT or self.INPUT.
        Returns (device_id, port_id).
        """

        id = self.symbol.id
        device = self.devices.get_device(id)
        if device is None:
            self.error(self.NO_DEVICE, True)
            return (None, None)

        port = None

        # Inputs must have identifiers; outputs don't, unless D_TYPE device
        expect_identifier = (io == self.INPUT or
                             device.device_kind == self.devices.D_TYPE)
        self.symbol = self.scanner.get_symbol()
        if self.symbol.type == self.scanner.PE:
            if expect_identifier:
                self.symbol = self.scanner.get_symbol()
                if self.symbol.type == self.scanner.NAMES:
                    port = self.symbol.id
                    self.symbol = self.scanner.get_symbol()
                else:
                    self.error(self.NO_IDENTIFIER, True)
                    return (None, None)
            else:
                self.error(self.IDENTIFIER_PRESENT, True)
                return (None, None)

        # Identifier expected but period symbol not found
        elif expect_identifier:
            self.error(self.SYNTAX, True, self.scanner.PERIOD)
            return (None, None)

        return (id, port)

    def check_io(self, io):
        """Check syntax for io."""

        self.symbol = self.scanner.get_symbol()
        if self.symbol.type == self.scanner.PE:
            self.symbol = self.scanner.get_symbol()
            if self.symbol.type == self.scanner.NAMES:
                self.symbol = self.scanner.get_symbol()
            else:
                self.error(self.NO_IDENTIFIER, True)
                return False

        return True

    def error(self, error_type, advance_symbol, vararg=None):
        """Handle the error the parser has encountered."""

        self.error_count += 1
        error_message = "***Error: "
        stopping_symbol = [self.scanner.EOF]
        stop = None

        if error_type == self.NO_EOF:
            error_message += "End of file not reached."

        elif error_type == self.KEYWORD_ERROR:
            key = self.names.get_name_string(vararg)
            error_message += ("List declaration not made. Expected '" +
                              key + "'. "
                              "Advancing to next list.")
            stopping_symbol.append(self.scanner.END)
        elif error_type == self.SYNTAX_COLON:
            error_message += ("Expected a ':' "
                              "after a list declaration. "
                              "Advancing to next list.")
            stopping_symbol.append(self.scanner.END)
        elif error_type == self.SYMBOL_TYPE_ERROR:
            type = vararg
            error_message += "Expected a " + type + "."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.NO_DEVICE:
            error_message += "This does not match a known device."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.BAD_NAME:
            error_message += ("Expected a name for the device. "
                              "Make sure it is not one of the "
                              "reserved keywords and follows "
                              "the correct syntax.")
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.NOT_VALID_NAME:
            error_message += "Already used as a name for another device."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.SYNTAX:
            syn = self.names.get_name_string(vararg)
            error_message += "Expected a '" + syn + "'."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.END_ERROR:
            error_message += ("Expected either another item in list "
                              "or the keyword END.")
            stopping_symbol.extend(self.scanner.keywords_list)
        elif error_type == self.IDENTIFIER_PRESENT:
            error_message += "Not expecting an identifier."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.NO_IDENTIFIER:
            error_message += "No identifier present."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.UNCONNECTED_INPUTS:
            error_message += "Not all inputs are connected."
        elif error_type == self.NO_MONITOR:
            error_message += ("No monitor points chosen. "
                              "At least one output must be monitored.")

        # Errors defined in Monitors
        elif error_type == self.monitors.NOT_OUTPUT:
            error_message += ("This point cannot be monitored "
                              "as it is not an output.")
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.monitors.MONITOR_PRESENT:
            error_message += "This point is already being monitored."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])

        # Errors defined in Network
        elif error_type == self.network.INPUT_TO_INPUT:
            error_message += "Cannot connect an input to an input."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.network.OUTPUT_TO_OUTPUT:
            error_message += "Cannot connect an output to an output."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.network.INPUT_CONNECTED:
            error_message += "The input is already connected elsewhere."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.network.PORT_ABSENT:
            error_message += "One of the ports does not exist."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.network.DEVICE_ABSENT:
            error_message += "One of the devices does not exist in network."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])

        # Errors defined in Devices
        elif error_type == self.devices.INVALID_QUALIFIER:
            error_message += "Property not recognised for device."
            if vararg == self.devices.SWITCH:
                error_message += (" Make sure property is "
                                  "either 'OFF' or 'ON'.")
            elif vararg == self.devices.CLOCK:
                error_message += " Make sure property is a positive integer."
            elif vararg == self.devices.SIGGEN:
                error_message += (" Make sure property contains "
                                  "only '0's and '1's.")
            elif (vararg in self.devices.gate_types and
                  vararg != self.devices.XOR):
                error_message += (" Make sure property is "
                                  "an integer less than 17 "
                                  "(and greater than 0).")
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.devices.NO_QUALIFIER:
            error_message += "Expected a property for the device."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.devices.BAD_DEVICE:
            error_message += ("Something went wrong adding this device "
                              "to the network.")
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.devices.QUALIFIER_PRESENT:
            error_message += "Property not required for this device."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])
        elif error_type == self.devices.DEVICE_PRESENT:
            error_message += "This device already exists."
            stopping_symbol.extend([self.scanner.SEMI_COLON,
                                    self.scanner.END])

        l = self.symbol.linenum
        c = self.symbol.colnum

        if advance_symbol:
            while self.symbol.id not in stopping_symbol:
                self.symbol = self.scanner.get_symbol()
            stop = self.symbol.id
            if self.symbol.id != self.scanner.EOF:
                self.symbol = self.scanner.get_symbol()
                error_message += (" Parsing resumed on line " +
                                  str(self.symbol.linenum) + ".")
            else:
                self.reached_eof = True

        error_message += "***\n"
        self.error_messages.append((error_message, l, c))
        return stop

    def error_report(self):
        """Build and display the error report."""

        for i in self.error_messages:
            s = self.scanner.print_line(i[1], i[2])
            message = "---------\n"
            message += "In line " + str(i[1]) + ":\n" + s + "\n"
            print(message + i[0] + "---------\n")
