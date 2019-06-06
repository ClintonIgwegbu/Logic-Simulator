"""Testing the scanner module"""
import pytest

from names import Names
from scanner import Symbol
from scanner import Scanner

path = 'testFiles/testfile_scanner.txt'
scan = Scanner(path, Names())


def test_keyword():
    """testing keywords scanning in scanner module"""
    symbol = scan.get_symbol()
    assert symbol.type == 0
    assert symbol.id == 7
    assert symbol.linenum == 1


def test_colon():
    """testing colon scanning in scanner module"""
    symbol = scan.get_symbol()
    assert symbol.type == 5
    assert symbol.id == 1
    assert symbol.linenum == 1


def test_devicetype_():
    """testing devicetype scanning in scanner module"""
    symbol = scan.get_symbol()
    assert symbol.type == 1
    assert symbol.id == 12
    assert symbol.linenum == 1


def test_names():
    """testing name scanning in scanner module"""
    symbol = scan.get_symbol()
    assert symbol.type == 2
    assert symbol.id == 20
    assert symbol.linenum == 1


def test_number():
    """testing number scanning in scanner module"""
    symbol = scan.get_symbol()
    assert symbol.type == 4
    assert symbol.id == 21
    assert symbol.linenum == 1


def test_semi_colon():
    """testing semi-colon scanning in scanner module"""
    symbol = scan.get_symbol()
    assert symbol.type == 6
    assert symbol.id == 2
    assert symbol.linenum == 1


def test_initial_states():
    """testing initial states scanning in scanner module"""
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    symbol = scan.get_symbol()
    assert symbol.type == 3
    assert symbol.id == 5
    assert symbol.linenum == 1


def test_arrow():
    """testing arrow scanning in scanner module"""
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    scan.get_symbol()
    symbol = scan.get_symbol()
    assert symbol.type == 7
    assert symbol.id == 3
    assert symbol.linenum == 4


def test_period():
    """testing period scanning in scanner module"""
    scan.get_symbol()
    symbol = scan.get_symbol()
    assert symbol.type == 8
    assert symbol.id == 4
    assert symbol.linenum == 4
