"""Test the Parse module"""
import pytest

from names import Names
from scanner import Scanner
from scanner import Symbol
from devices import Devices
from network import Network
from monitors import Monitors
from parse import Parser

file_no_errors = "testFiles/no_errors.txt"
file_errors = "testFiles/errors.txt"
file_io = "testFiles/io.txt"
file_device = "testFiles/device.txt"
file_connect = "testFiles/connect.txt"


@pytest.fixture
def parser():
    """Return a new instance of the Parse class."""
    new_names = Names()
    new_scanner = Scanner(file_no_errors, new_names)
    new_devices = Devices(new_names)
    new_network = Network(new_names, new_devices)
    new_monitors = Monitors(new_names, new_devices, new_network)
    new_parser = Parser(new_names, new_devices, new_network,
                        new_monitors, new_scanner)

    return new_parser


@pytest.fixture
def new_parser():
    """Return a new instance of the Parse class."""
    new_names = Names()
    new_scanner = Scanner(file_no_errors, new_names)
    new_devices = Devices(new_names)
    new_network = Network(new_names, new_devices)
    new_monitors = Monitors(new_names, new_devices, new_network)
    new_parser = Parser(new_names, new_devices, new_network,
                        new_monitors, new_scanner)

    # Initially populate new_devices with some devices
    [AND_ID, NOR_ID,
     CLK_ID, SW_ID] = new_parser.names.lookup(["foo", "bar",
                                               "b", "sw"])

    new_parser.devices.make_device(AND_ID, new_devices.AND, 3)
    new_parser.devices.make_device(NOR_ID, new_devices.NOR, 2)
    new_parser.devices.make_device(CLK_ID, new_devices.CLOCK, 1)

    return new_parser


@pytest.fixture
def new_parser_with_errors():
    """Return a new instance of the Parse class."""
    new_names = Names()
    new_scanner = Scanner(file_errors, new_names)
    new_devices = Devices(new_names)
    new_network = Network(new_names, new_devices)
    new_monitors = Monitors(new_names, new_devices, new_network)
    new_parser = Parser(new_names, new_devices, new_network,
                        new_monitors, new_scanner)

    return new_parser


@pytest.fixture
def parser_io():
    """Return a new instance of the Parse class."""
    names = Names()
    scanner = Scanner(file_io, names)
    devices = Devices(names)
    network = Network(names, devices)
    monitors = Monitors(names, devices, network)
    new_parser = Parser(names, devices, network,
                        monitors, scanner)

    # Initially populate new_devices with some devices
    [new_parser.DT] = new_parser.names.lookup(["d1"])

    new_parser.devices.make_device(new_parser.DT, devices.D_TYPE)

    return new_parser


@pytest.fixture
def parser_device():
    """Return a new instance of the Parse class."""
    names = Names()
    scanner = Scanner(file_device, names)
    devices = Devices(names)
    network = Network(names, devices)
    monitors = Monitors(names, devices, network)
    new_parser = Parser(names, devices, network,
                        monitors, scanner)

    return new_parser


@pytest.fixture
def parser_connect():
    """Return a new instance of the Parse class."""
    names = Names()
    scanner = Scanner(file_connect, names)
    devices = Devices(names)
    network = Network(names, devices)
    monitors = Monitors(names, devices, network)
    new_parser = Parser(names, devices, network,
                        monitors, scanner)

    [clk, dt] = new_parser.names.lookup(["CLK", "D1"])
    new_parser.devices.make_device(clk, devices.CLOCK, 10)
    new_parser.devices.make_device(dt, devices.D_TYPE)

    return new_parser


def test_check_valid_name(new_parser):
    """Test if check_valid_name correctly discerns whether name
    already exists or not.
    """
    [AND, NOR, CLK, SPAM] = new_parser.names.lookup(["foo", "bar",
                                                    "b", "spam"])
    assert not new_parser.check_valid_name(AND)
    assert not new_parser.check_valid_name(NOR)
    assert not new_parser.check_valid_name(CLK)
    assert new_parser.check_valid_name(SPAM)

@pytest.mark.parametrize("function_args, device_type, returns", [
    ("(scanner.PROPERTY, prop1, 0, 0)", "(devices.SWITCH)", "devices.LOW"),
    ("(scanner.NUMBER, prop2, 0, 0)", "(devices.AND)", "3"),
    ("(scanner.NAMES, prop3, 0, 0)", "(devices.AND)", "None"),
    ("(scanner.NUMBER, prop4, 0, 0)", "(devices.SIGGEN)", "'0110'"),
])
def test_get_property(new_parser, function_args, device_type, returns):
    """Test get_property"""
    names = new_parser.names
    scanner = new_parser.scanner
    devices = new_parser.devices
    [prop1, prop2, prop3, prop4] = names.lookup(["OFF", "3", "foo", "0110"])

    new_parser.symbol = eval("".join(["Symbol", function_args]))
    left_expression = eval("".join(["new_parser.get_property", device_type]))
    right_expression = eval(returns)
    assert left_expression == right_expression


def test_get_io(parser_io):
    """Test get_io"""
    names = parser_io.names
    scanner = parser_io.scanner
    devices = parser_io.devices
    parser_io.symbol = scanner.get_symbol()

    assert parser_io.get_io(parser_io.OUTPUT) == (parser_io.DT,
                                                  devices.Q_ID)

    [AND] = names.lookup(["and"])
    parser_io.symbol = Symbol(scanner.NAMES, AND, 0, 0)
    assert parser_io.get_io(parser_io.OUTPUT) == (None, None)


def test_device(parser_device):
    """Test device function"""
    scanner = parser_device.scanner
    parser_device.symbol = scanner.get_symbol()

    assert parser_device.device()
    assert parser_device.device()
    assert not parser_device.device()


def test_connect(parser_connect):
    """Test connect function"""
    scanner = parser_connect.scanner
    parser_connect.symbol = scanner.get_symbol()

    assert parser_connect.connect()
    assert not parser_connect.connect()


def test_check_keyword(new_parser):
    """Test check_keyword"""
    scanner = new_parser.scanner
    new_parser.symbol = scanner.get_symbol()

    assert new_parser.check_keyword(scanner.DEVICE_LIST)
    assert not new_parser.check_keyword(scanner.MONITOR_LIST)


def test_build_list(parser_device):
    """Test build_list"""
    scanner = parser_device.scanner
    parser_device.symbol = scanner.get_symbol()

    assert parser_device.build_list(scanner.DEVICETYPE,
                                    parser_device.device)

    parser_device.symbol = Symbol(scanner.NUMBER, 1, 0, 0)
    assert not parser_device.build_list(scanner.DEVICETYPE,
                                        parser_device.device)


def test_lists(parser):
    """Test the devicelist, connectionlist functions"""
    parser.symbol = parser.scanner.get_symbol()
    assert parser.devicelist()
    assert parser.connectionlist()


@pytest.mark.parametrize("function_args, error",[
    ("(parser.KEYWORD_ERROR,True, scanner.CONNECTION_LIST)", "scanner.END"),
    ("(parser.SYMBOL_TYPE_ERROR, True, parser.NAMES)", "scanner.SEMI_COLON"),
])
def test_error(new_parser_with_errors, function_args, error):
    """Test the error funciton"""
    parser = new_parser_with_errors
    scanner = parser.scanner
    parser.symbol = scanner.get_symbol()

    left_expression = eval("".join(["parser.error", function_args]))
    right_expression = eval(error)
    assert left_expression == right_expression


def test_parse_network(parser):
    """Test parse_network"""
    assert parser.parse_network()


def test_parse_network_with_errors(new_parser_with_errors):
    """Test parse_network"""
    assert not new_parser_with_errors.parse_network()
