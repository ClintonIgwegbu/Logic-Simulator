"""Test the names module."""
import pytest

from names import Names


@pytest.fixture
def name_string_list():
    """creating a list"""
    return ["Alice", "Bob", "Eve"]


@pytest.fixture
def used_names(name_string_list):
    """putting the list into class"""
    my_name = Names()
    my_name.lookup(name_string_list)
    return my_name


@pytest.mark.parametrize("test_name_string, expected_idlist, new_name_string,"
                         "new_idlist", [(["Alice", "Bob", "Eve"], [0, 1, 2],
                                        ["Alice", "Bob", "Eve", "steve",
                                        "david"], [0, 1, 2, 3, 4])])
def test_lookup(used_names, test_name_string, expected_idlist, new_name_string,
                new_idlist):
    """testing the lookup function in names module"""
    assert used_names.lookup(test_name_string) == expected_idlist
    assert Names().lookup(new_name_string) == new_idlist


@pytest.mark.parametrize("name_id, expected_string", [("(0)", "Alice")])
def test_get_string(used_names, name_id, expected_string):
    """testing the get_name_string function in the names module"""
    left = eval("".join(["used_names.get_name_string", name_id]))
    right = expected_string
    assert left == right


@pytest.mark.parametrize("name_string, id", [("('Alice')", 0), ("('Bob')", 1)])
def test_query(used_names, name_string, id):
    """testing the query function in the names module"""
    left = eval("".join(["used_names.query", name_string]))
    right = id
    assert left == id
