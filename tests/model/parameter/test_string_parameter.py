# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) 2019-2021 NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Unit tests for string parameter declarations."""

import pytest

from flowserv.model.parameter.string import String, PARA_STRING

import flowserv.error as err


def test_invalid_serialization():
    """Test errors for invalid serializations."""
    with pytest.raises(err.InvalidParameterError):
        String.from_dict({
            'name': '0000',
            'dtype': PARA_STRING,
        })
    String.from_dict({
        'name': '0000',
        'dtype': 'unknown',
        'index': 0,
        'label': 'Name',
        'isRequired': True
    }, validate=False)
    with pytest.raises(ValueError):
        String.from_dict({
            'name': '0000',
            'dtype': 'unknown',
            'index': 0,
            'label': 'Name',
            'isRequired': True
        })
    with pytest.raises(err.InvalidParameterError):
        String.from_dict({
            'dtype': PARA_STRING,
            'label': 'Firstname',
            'index': 1,
            'help': 'Your first name',
            'defaultValue': 'Alice',
            'isRequired': True,
            'group': 'person'
        })


def test_string_parameter_from_dict():
    """Test generating a string parameter declaration from a dictionary
    serialization.
    """
    para = String.from_dict(
        String.to_dict(
            String.from_dict({
                'name': '0000',
                'dtype': PARA_STRING,
                'label': 'Firstname',
                'index': 1,
                'help': 'Your first name',
                'defaultValue': 'Alice',
                'isRequired': True,
                'group': 'person'
            })
        )
    )
    assert para.is_string()
    assert para.name == '0000'
    assert para.dtype == PARA_STRING
    assert para.label == 'Firstname'
    assert para.index == 1
    assert para.help == 'Your first name'
    assert para.default == 'Alice'
    assert para.required
    assert para.group == 'person'


def test_string_parameter_value():
    """Test getting argument value for a string parameter."""
    para = String('0000', 0)
    assert para.cast(2) == '2'
    assert para.cast('ABC') == 'ABC'
    assert para.cast(None) == 'None'
    para = String('0000', 0, required=True)
    assert para.cast(2) == '2'
    assert para.cast('ABC') == 'ABC'
