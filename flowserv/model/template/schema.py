# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) 2019-2021 NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Definition of schema components for benchmark results. The schema definition
is part of the extended workflow template specification that is used to define
benchmarks.
"""

from flowserv.model.parameter.numeric import PARA_FLOAT, PARA_INT
from flowserv.model.parameter.string import PARA_STRING

import flowserv.error as err
import flowserv.util as util


"""Supported data types for result values."""
DATA_TYPES = [PARA_FLOAT, PARA_INT, PARA_STRING]


class ResultColumn(object):
    """Column in the result schema of a benchmark. Each column has a unique
    identifier and unique name. The identifier is used as column name in the
    database schema. The name is for display purposes in a user interface.
    The optional path element is used to extract the column value from nested
    result files.
    """
    def __init__(self, column_id, name, dtype, path=None, required=None):
        """Initialize the unique column identifier, name, and the data type. If
        the value of dtype is not in the list of supported data types an
        error is raised.

        The optional path element references the column value in nested result
        files. If no path is given the column identifier is used instead.

        Parameters
        ----------
        column_id: string
            Unique column identifier
        name: string
            Unique column name
        dtype: string
            Data type identifier
        path: string, optional
            Path to column value in nested result files.
        required: bool, optional
            Indicates whether a value is expected for this column in every
            benchmark run result

        Raises
        ------
        flowserv.error.InvalidTemplateError
        """
        # Raise error if the data type value is not in the list of supported
        # data types
        if dtype not in DATA_TYPES:
            msg = "unknown data type '{}'"
            raise err.InvalidTemplateError(msg.format(dtype))
        self.column_id = column_id
        self.name = name
        self.dtype = dtype
        self.path = path
        self.required = required if required is not None else True

    def cast(self, value):
        """Cast the given value to the data type of the column. Will raise
        ValueError if type cast is not successful.

        Parameters
        ----------
        value: scalar
            Expects a scalar value that can be converted to the respective
            column type.

        Returns
        -------
        int, float, or string
        """
        if self.dtype == PARA_INT:
            return int(value)
        elif self.dtype == PARA_FLOAT:
            return float(value)
        return str(value)

    @classmethod
    def from_dict(cls, doc, validate=True):
        """Get an instance of the column from the dictionary serialization.
        Raises an error if the given dictionary does not contain the expected
        elements as generated by the to_dict() method of the class.

        Parameters
        ----------
        doc: dict
            Dictionary serialization of a column object
        validate: bool, default=True
            Validate the serialization if True.

        Returns
        -------
        flowserv.model.template.schema.ResultColumn

        Raises
        ------
        flowserv.error.InvalidTemplateError
        """
        # Validate the serialization dictionary.
        if validate:
            try:
                util.validate_doc(
                    doc,
                    mandatory=['name', 'label', 'dtype'],
                    optional=['path', 'required']
                )
            except ValueError as ex:
                raise err.InvalidTemplateError(str(ex))
        # Return instance of the column object
        return cls(
            column_id=doc['name'],
            name=doc['label'],
            dtype=doc['dtype'],
            path=doc.get('path'),
            required=doc.get('required')
        )

    def jpath(self):
        """The Json path for a result column is a list of element keys that
        reference the column value in a nested document. If the internal path
        variable is not set the column identifier is returned as the only
        element in the path.

        Returns
        -------
        list(string)
        """
        if self.path is not None:
            return self.path.split('/')
        else:
            return list([self.column_id])

    def to_dict(self):
        """Get dictionary serialization for the column object.

        Returns
        -------
        dict
        """
        doc = {
            'name': self.column_id,
            'label': self.name,
            'dtype': self.dtype,
            'required': self.required
        }
        # Add the path expression if it is given
        if self.path is not None:
            doc['path'] = self.path
        return doc


class ResultSchema(object):
    """The result schema of a benchmark run is a collection of columns. The
    result schema is used to generate leader boards for benchmarks.

    The schema also contains the identifier of the output file that contains
    the result object. The result object that is generated by each benchmark
    run is expected to contain a value for each required columns in the schema.
    """
    def __init__(self, result_file, columns, order_by=None):
        """Initialize the result file identifier, schema columns, and the
        default sort order.

        Parameters
        ----------
        result_file: string
            Identifier of the benchmark run result file that contains the
            analytics results.
        columns: list(flowserv.model.template.schema.ResultColumn)
            List of columns in the result object
        order_by: list(flowserv.model.template.schema.SortColumn), optional
            List of columns that define the default sort order for entries in
            the leader board.
        """
        self.result_file = result_file
        self.columns = columns
        self.order_by = order_by if order_by is not None else list()

    @classmethod
    def from_dict(cls, doc, validate=True):
        """Get an instance of the schema from a dictionary serialization.
        Raises an error if the given dictionary does not contain the expected
        elements as generated by the to_dict() method of the class or if the
        names or identifier of columns are not unique.

        Returns None if the given document is None.

        Parameters
        ----------
        doc: dict
            Dictionary serialization of a benchmark result schema object
        validate: bool, default=True
            Validate the serialization if True.

        Returns
        -------
        flowserv.model.template.schema.ResultSchema

        Raises
        ------
        flowserv.error.InvalidTemplateError
        """
        # Return None if no document is given
        if doc is None:
            return None
        # Validate the serialization dictionary
        if validate:
            try:
                util.validate_doc(
                    doc,
                    mandatory=['file', 'schema'],
                    optional=['orderBy']
                )
            except ValueError as ex:
                raise err.InvalidTemplateError(str(ex))
        # Identifier of the output file that contains the result object
        file_id = doc['file']
        # Get column list. Ensure that all column names and identifier are
        # unique
        columns = list()
        for c in doc['schema']:
            columns.append(ResultColumn.from_dict(c, validate=validate))
        ids = set()
        names = set()
        for col in columns:
            if col.column_id in ids:
                msg = "duplicate column identifier '{}'"
                raise err.InvalidTemplateError(msg.format(col.column_id))
            ids.add(col.column_id)
            if col.name in names:
                msg = "not unique column name '{}'"
                raise err.InvalidTemplateError(msg.format(col.name))
            names.add(col.name)
        # Get optional default sort statement for the ranking
        order_by = list()
        for c in doc.get('orderBy', []):
            col = SortColumn.from_dict(c, validate=validate)
            if col.column_id not in ids:
                msg = "unknown column '{}'"
                raise err.InvalidTemplateError(msg.format(col.column_id))
            order_by.append(col)
        # Return benchmark schema object
        return cls(
            result_file=file_id,
            columns=columns,
            order_by=order_by
        )

    def get_default_order(self):
        """By default the first column in the schema is used as the sort
        column. Values in the column are sorted in descending order.

        Returns
        -------
        list(flowserv.model.template.schema.SortColumn)
        """
        if len(self.order_by) > 0:
            return self.order_by
        col = self.columns[0]
        return [SortColumn(column_id=col.column_id, sort_desc=True)]

    def to_dict(self):
        """Get dictionary serialization for the result schema object.

        Returns
        -------
        dict
        """
        return {
            'file': self.result_file,
            'schema': [col.to_dict() for col in self.columns],
            'orderBy': [col.to_dict() for col in self.order_by]
        }


class SortColumn(object):
    """The sort column defines part of an ORDER BY statement that is used to
    sort benchmark results when creating the benchmark leader board. Each
    object contains a reference to a result column and a flag indicating the
    sort order for values in the column.
    """
    def __init__(self, column_id, sort_desc=None):
        """Initialize the object properties.

        Parameters
        ----------
        column_id: string
            Unique column identifier
        sort_desc: bool, optional
            Sort values in descending order if True or in ascending order
            otherwise
        """
        self.column_id = column_id
        self.sort_desc = sort_desc if sort_desc is not None else True

    @classmethod
    def from_dict(cls, doc, validate=True):
        """Get an instance of the sort column from the dictionary serialization.
        Raises an error if the given dictionary does not contain the expected
        elements as generated by the to_dict() method of the class.

        Parameters
        ----------
        doc: dict
            Dictionary serialization of a column object
        validate: bool, default=True
            Validate the serialization if True.

        Returns
        -------
        flowserv.model.template.schema.SortColumn

        Raises
        ------
        flowserv.error.InvalidTemplateError
        """
        # Validate the serialization dictionary
        if validate:
            try:
                util.validate_doc(
                    doc,
                    mandatory=['name'],
                    optional=['sortDesc']
                )
            except ValueError as ex:
                raise err.InvalidTemplateError(str(ex))
        sort_desc = None
        if 'sortDesc' in doc:
            sort_desc = doc['sortDesc']
        # Return instance of the column object
        return cls(column_id=doc['name'], sort_desc=sort_desc)

    def to_dict(self):
        """Get dictionary serialization for the sort column object.

        Returns
        -------
        dict
        """
        return {'name': self.column_id, 'sortDesc': self.sort_desc}
