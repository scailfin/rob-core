# This file is part of the Reproducible Open Benchmarks for Data Analysis
# Platform (ROB).
#
# Copyright (C) 2019 NYU.
#
# ROB is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""The benchmark repository maintains information about benchmarks. For each
benchmark basic information is stored in the underlying database, together with
the workflow template and the result files of individual workflow runs.
"""

import json

from robcore.model.template.benchmark import BenchmarkHandle
from robcore.model.template.schema import ResultSchema

import robcore.error as err
import robcore.model.constraint as constraint
import robcore.model.ranking as ranking
import robcore.model.template.parameter.declaration as pd


class BenchmarkRepository(object):
    """The repository maintains benchmarks as well as the results of benchmark
    runs.
    """
    def __init__(self, con, template_repo):
        """Initialize the database connection and the template store.

        Parameters
        ----------
        con: DB-API 2.0 database connection
            Connection to underlying database
        template_store: robcore.model.template.repo.base.TemplateRepository, optional
            Repository for workflow templates
        """
        self.con = con
        self.template_repo = template_repo

    def add_benchmark(
        self, name, description=None, instructions=None, src_dir=None,
        src_repo_url=None, spec_file=None
    ):
        """Add a benchmark to the repository. The associated workflow template
        is created in the template repository from either the given source
        directory or Git repository. The template repository will raise an
        error if neither or both arguments are given.

        Each benchmark has a name and an optional description and set of
        instructions.

        Raises an error if the given benchmark name is not unique.

        Parameters
        ----------
        name: string
            Unique benchmark headline name
        description: string, optional
            Optional short description for display in benchmark listings
        instructions: string, optional
            Text containing detailed instructions for benchmark participants
        src_dir: string, optional
            Directory containing the benchmark components, i.e., the fixed
            files and the template specification (optional).
        src_repo_url: string, optional
            Git repository that contains the the benchmark components
        spec_file: string, optional
            Path to the workflow template specification file (absolute or
            relative to the workflow directory)

        Returns
        -------
        robcore.model.template.benchmark.BenchmarkHandle

        Raises
        ------
        robcore.error.ConstraintViolationError
        robcore.error.InvalidTemplateError
        ValueError
        """
        # Ensure that the benchmark name is not empty, not longer than 512
        # character and unique.
        sql = 'SELECT name FROM benchmark WHERE name = ?'
        constraint.validate_name(name, con=self.con, sql=sql)
        # Create the workflow template in the associated template repository
        template = self.template_repo.add_template(
            src_dir=src_dir,
            src_repo_url=src_repo_url,
            spec_file=spec_file
        )
        t_id = template.identifier
        # Create the result table in the underlying database if the template
        # contains a schema definition
        if template.has_schema():
            schema = template.get_schema()
            ranking.create_result_table(
                con=self.con,
                benchmark_id=t_id,
                schema=schema,
                commit_changes=False
            )
            result_schema = json.dumps(schema.to_dict())
        else:
            result_schema = None
        # Insert benchmark into database and return descriptor
        sql = 'INSERT INTO benchmark'
        sql += '(benchmark_id, name, description, instructions, result_schema) '
        sql += 'VALUES(?, ?, ?, ?, ?)'
        values = (t_id, name, description, instructions, result_schema)
        self.con.execute(sql, values)
        # Commit all changes and return the benchmark descriptor
        self.con.commit()
        return BenchmarkHandle(
            identifier=t_id,
            name=name,
            description=description,
            instructions=instructions,
            template=template,
            repo=self
        )

    def delete_benchmark(self, benchmark_id):
        """Delete the benchmark with the given identifier.

        Parameters
        ----------
        benchmark_id: string
            Unique benchmark identifier
        """
        # Delete the workflow template.
        result = self.template_repo.delete_template(benchmark_id)
        # Delete the benchmark record. Use rowcount to determine if the record
        # existed.
        sql = 'DELETE FROM benchmark WHERE benchmark_id = ?'
        self.con.execute(sql, (benchmark_id,))
        self.con.commit()

    def get_benchmark(self, benchmark_id):
        """Get descriptor for the benchmark with the given identifier. Raises
        an error if no benchmark with the identifier exists.

        Parameters
        ----------
        benchmark_id: string
            Unique benchmark identifier

        Returns
        -------
        robcore.model.template.benchmark.BenchmarkHandle

        Raises
        ------
        robcore.error.UnknownBenchmarkError
        """
        # Get benchmark information from database. If the result is empty an
        # error is raised
        sql = 'SELECT benchmark_id, name, description, instructions '
        sql += 'FROM benchmark '
        sql += 'WHERE benchmark_id = ?'
        rs = self.con.execute(sql, (benchmark_id,)).fetchone()
        if rs is None:
            raise err.UnknownBenchmarkError(benchmark_id)
        # Return handle for benchmark descriptor. The workflow handle will be
        # loaded here and not on-demand.
        return BenchmarkHandle(
            identifier=benchmark_id,
            name=rs['name'],
            description=rs['description'],
            instructions=rs['instructions'],
            template=self.template_repo.get_template(benchmark_id),
            repo=self
        )

    def get_leaderboard(self, benchmark_id, order_by=None, include_all=False):
        """Get current leaderboard for a given benchmark. The result is a
        ranking of run results. Each entry contains the run and submission
        information, as well as a dictionary with the results of the respective
        workflow run.

        If the include_all flag is False at most one result per submission is
        included in the result.

        Parameters
        ----------
        benchmark_id: string
            Unique benchmark identifier
        order_by: list(robcore.model.template.schema.SortColumn), optional
            Use the given attribute to sort run results. If not given the schema
            default attribute is used
        include_all: bool, optional
            Include at most one entry per submission in the result if False

        Returns
        -------
        robcore.model.ranking.ResultRanking

        Raises
        ------
        robcore.error.UnknownBenchmarkError
        """
        # Get the result schema for the benchmark. Will raise an error if the
        # benchmark does not exist.
        sql = 'SELECT result_schema FROM benchmark WHERE benchmark_id = ?'
        row = self.con.execute(sql, (benchmark_id,)).fetchone()
        if row is None:
            raise err.UnknownBenchmarkError(benchmark_id)
        # Get the result schema as defined in the workflow template
        if not row['result_schema'] is None:
            schema = ResultSchema.from_dict(json.loads(row['result_schema']))
        else:
            schema = ResultSchema()
        return ranking.query(
            con=self.con,
            benchmark_id=benchmark_id,
            schema=schema,
            filter_stmt='s.benchmark_id = ?',
            args=(benchmark_id,),
            order_by=order_by,
            include_all=include_all
        )

    def list_benchmarks(self):
        """Get a list of descriptors for all benchmarks in the repository.

        Returns
        -------
        list(robcore.model.template.benchmark.BenchmarkHandle)
        """
        sql = 'SELECT benchmark_id, name, description, instructions '
        sql += 'FROM benchmark '
        result = list()
        for row in self.con.execute(sql).fetchall():
            # Return descriptors that will load associated workflow templates
            # on-demand
            result.append(
                BenchmarkHandle(
                    identifier=row['benchmark_id'],
                    name=row['name'],
                    description=row['description'],
                    instructions=row['instructions'],
                    repo=self
                )
            )
        return result
