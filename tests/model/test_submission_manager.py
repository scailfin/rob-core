# This file is part of the Reproducible Open Benchmarks for Data Analysis
# Platform (ROB).
#
# Copyright (C) 2019 NYU.
#
# ROB is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Test functionality of the submission manager."""

import json
import os
import pytest

from passlib.hash import pbkdf2_sha256

from robcore.model.submission import SubmissionManager
from robcore.model.template.base import WorkflowTemplate
from robcore.model.template.schema import SortColumn
from robcore.controller.engine import BenchmarkEngine
from robcore.tests.benchmark import StateEngine
from robcore.tests.repo import DictRepo

import robcore.error as err
import robcore.model.ranking as ranking
import robcore.tests.benchmark as bm
import robcore.tests.db as db
import robcore.util as util


BENCHMARK_1 = util.get_unique_identifier()
BENCHMARK_2 = util.get_unique_identifier()
USER_1 = util.get_unique_identifier()
USER_2 = util.get_unique_identifier()
USER_3 = util.get_unique_identifier()

TEMPLATE = WorkflowTemplate(
    workflow_spec=dict(),
    source_dir='/dev/null',
    result_schema=bm.BENCHMARK_SCHEMA
)


class TestSubmissionManager(object):
    """Unit tests for managing submissions and team members through the
    submission manager.
    """
    @staticmethod
    def init(base_dir):
        """Create a fresh database with three users and two benchmarks. The
        first benchmark has a resutl schema and the second benchmark does not
        have a schema.

        Creates an instance of the test benchmark engine and the submission
        manager.

        Returns the pair of sumbission manager and state engine (the workflow
        controller that is used for unit tests).
        """
        con = db.init_db(base_dir).connect()
        sql = 'INSERT INTO api_user(user_id, name, secret, active) VALUES(?, ?, ?, ?)'
        con.execute(sql, (USER_1, USER_1, pbkdf2_sha256.hash(USER_1), 1))
        con.execute(sql, (USER_2, USER_2, pbkdf2_sha256.hash(USER_2), 1))
        con.execute(sql, (USER_3, USER_3, pbkdf2_sha256.hash(USER_3), 1))
        sql = 'INSERT INTO benchmark(benchmark_id, name, result_schema) '
        sql += 'VALUES(?, ?, ?)'
        schema = json.dumps(bm.BENCHMARK_SCHEMA.to_dict())
        con.execute(sql, (BENCHMARK_1, BENCHMARK_1, schema))
        sql = 'INSERT INTO benchmark(benchmark_id, name) '
        sql += 'VALUES(?, ?)'
        con.execute(sql, (BENCHMARK_2, BENCHMARK_2))
        ranking.create_result_table(
            con=con,
            benchmark_id=BENCHMARK_1,
            schema=bm.BENCHMARK_SCHEMA,
            commit_changes=False
        )
        con.commit()
        engine = StateEngine(base_dir=os.path.join(base_dir, 'runs'))
        manager = SubmissionManager(
            con=con,
            directory=base_dir,
            engine=BenchmarkEngine(
                con=con,
                backend=engine
            )
        )
        return manager, engine

    def test_create_submission(self, tmpdir):
        """Test creating a submission."""
        # Create database and submission manager
        manager, _ = TestSubmissionManager.init(str(tmpdir))
        # Create a new submission with a single user
        s = manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='A',
            user_id=USER_1
        )
        assert s.name == 'A'
        assert s.owner_id == USER_1
        assert len(s.members) == 1
        assert s.has_member(USER_1)
        # Update submission name and add another member
        manager.update_submission(s.identifier, name='ABC')
        s = manager.get_submission(s.identifier)
        assert s.name == 'ABC'
        assert s.owner_id == USER_1
        assert len(s.members) == 1
        assert s.has_member(USER_1)
        manager.update_submission(s.identifier, members=[USER_1, USER_2])
        s = manager.get_submission(s.identifier)
        assert s.name == 'ABC'
        assert s.owner_id == USER_1
        assert len(s.members) == 2
        assert s.has_member(USER_1)
        assert s.has_member(USER_2)
        assert not s.has_member(USER_3)
        # Create second submission where all users are members
        s = manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='B',
            user_id=USER_2,
            members=[USER_1, USER_3]
        )
        assert s.owner_id == USER_2
        assert len(s.members) == 3
        for user_id in [USER_1, USER_2, USER_3]:
            assert s.has_member(user_id)
        # Duplicate users in member list
        s = manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='C',
            user_id=USER_3,
            members=[USER_1, USER_3, USER_1, USER_3]
        )
        for user_id in [USER_1, USER_3]:
            assert s.has_member(user_id)
        assert not s.has_member(USER_2)
        # Error conditions
        # - Unknown benchmark
        with pytest.raises(err.UnknownBenchmarkError):
            manager.create_submission(
                benchmark_id='UNK',
                name='C',
                user_id=USER_1
            )
        # - Invalid name
        with pytest.raises(err.ConstraintViolationError):
            manager.create_submission(
                benchmark_id=BENCHMARK_1,
                name='A' * 513,
                user_id=USER_1
            )
        # - Unknown user
        with pytest.raises(err.UnknownUserError):
            manager.create_submission(
                benchmark_id=BENCHMARK_1,
                name='D',
                user_id=USER_1,
                members=[USER_2, 'not a user']
            )

    def test_delete_submission(self, tmpdir):
        """Test creating and deleting submissions."""
        # Create database and submission manager
        manager, engine = TestSubmissionManager.init(str(tmpdir))
        # Create a new submission
        submission = manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='A',
            user_id=USER_1
        )
        assert os.path.isdir(os.path.join(str(tmpdir), submission.identifier))
        # Create two successful runs for the submission
        values = {'col1': 1, 'col2': 1.1, 'col3': 'R0'}
        engine.success(values=values)
        manager.start_run(
            submission_id=submission.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        values = {'col1': 2, 'col2': 2.1}
        engine.success(values=values)
        manager.start_run(
            submission_id=submission.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        # Retrieve the submission to check that the result files were created
        submission = manager.get_submission(submission.identifier)
        assert len(submission.get_runs()) == 2
        filenames = list()
        for run in submission.get_runs():
            for res in run.list_resources():
                assert os.path.isfile(res.filename)
                assert not res.filename in filenames
                filenames.append(res.filename)
        manager.delete_submission(submission.identifier)
        assert not os.path.isdir(os.path.join(str(tmpdir), submission.identifier))
        for f in filenames:
            assert not os.path.isfile(f)
        with pytest.raises(err.UnknownSubmissionError):
            manager.get_submission(submission.identifier)
        with pytest.raises(err.UnknownSubmissionError):
            manager.delete_submission(submission.identifier)

    def test_get_results(self, tmpdir):
        """Test get result ranking for different submissions."""
        # Create database and submission manager
        manager, engine = TestSubmissionManager.init(str(tmpdir))
        # Create three submissions, two for the first benchmark and one for the
        # second benchmark
        s1 = manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='A',
            user_id=USER_1
        )
        s2 = manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='B',
            user_id=USER_1
        )
        s3 = manager.create_submission(
            benchmark_id=BENCHMARK_2,
            name='A',
            user_id=USER_1
        )
        # Insert three run results for the first submission, two for the second
        # submission and one for the third submission
        # Submission 1
        values = {'col1': 10, 'col2': 11.1, 'col3': 'L3'}
        engine.success(values=values)
        manager.start_run(
            submission_id=s1.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        values = {'col1': 5, 'col2': 21.1, 'col3': 'L1'}
        engine.success(values=values)
        manager.start_run(
            submission_id=s1.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        values = {'col1': 8, 'col2': 28.3, 'col3': 'L1'}
        engine.success(values=values)
        manager.start_run(
            submission_id=s1.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        # Submission 2
        values = {'col1': 25, 'col2': 25.1, 'col3': 'L4'}
        engine.success(values=values)
        manager.start_run(
            submission_id=s2.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        values = {'col1': 7, 'col2': 27.1, 'col3': 'L5'}
        engine.success(values=values)
        manager.start_run(
            submission_id=s2.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        # Submission 3
        values = {'col1': 7, 'col2': 27.1, 'col3': 'L5'}
        engine.success(values=values)
        manager.start_run(
            submission_id=s3.identifier,
            arguments=dict(),
            template=TEMPLATE
        )
        assert s1.get_results().size() == 3
        assert s2.get_results().size() == 2
        assert s3.get_results().size() == 1
        # Use list_submissions() to retrieve submission handles from database
        submissions = dict()
        for s in manager.list_submissions():
            submissions[s.identifier] = s
        assert len(submissions) == 3
        # Get sorted results for submission 1
        s1 = submissions[s1.identifier]
        results = s1.get_results(order_by=[SortColumn('col1')])
        assert results.size() == 3
        assert results.get(0).get('col1') == 10
        assert results.get(1).get('col1') == 8
        assert results.get(2).get('col1') == 5
        results = s1.get_results(
            order_by=[SortColumn('col1', sort_desc=False)]
        )
        assert results.size() == 3
        assert results.get(0).get('col1') == 5
        assert results.get(1).get('col1') == 8
        assert results.get(2).get('col1') == 10
        # Get sorted results for submission 2
        s2 = submissions[s2.identifier]
        results = s2.get_results(order_by=[SortColumn('col1')])
        assert results.size() == 2
        assert results.get(0).get('col1') == 25
        assert results.get(1).get('col1') == 7
        # Get sorted results for submission 3
        s3 = submissions[s3.identifier]
        results = s3.get_results(order_by=[SortColumn('col1')])
        assert results.size() == 1
        assert len(results.get(0).values) == 0


    def test_list_submissions(self, tmpdir):
        """Test listing a submissions."""
        # Create database and submission manager
        manager, _ = TestSubmissionManager.init(str(tmpdir))
        # Create a new submission with a single user
        manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='A',
            user_id=USER_1
        )
        manager.create_submission(
            benchmark_id=BENCHMARK_1,
            name='B',
            user_id=USER_2,
            members=[USER_3]
        )
        manager.create_submission(
            benchmark_id=BENCHMARK_2,
            name='C',
            user_id=USER_1
        )
        # Get listing of all submissions
        names = [s.name for s in manager.list_submissions()]
        assert len(names) == 3
        for n in ['A', 'B', 'C']:
            assert n in names
        # Get listing of all submissions for benchmark 1 and 2
        names = [s.name for s in manager.list_submissions(benchmark_id=BENCHMARK_1)]
        assert len(names) == 2
        for n in ['A', 'B']:
            assert n in names
        names = [s.name for s in manager.list_submissions(benchmark_id=BENCHMARK_2)]
        assert len(names) == 1
        assert 'C' in names
        # Get listings for users 1, 2, and 3
        names = [s.name for s in manager.list_submissions(user_id=USER_1)]
        assert len(names) == 2
        for n in ['A', 'C']:
            assert n in names
        names = [s.name for s in manager.list_submissions(user_id=USER_2)]
        assert len(names) == 1
        assert 'B' in names
        names = [s.name for s in manager.list_submissions(user_id=USER_3)]
        assert len(names) == 1
        assert 'B' in names
        # List submissions with both optional parameters given
        names = [s.name for s in manager.list_submissions(benchmark_id=BENCHMARK_2, user_id=USER_1)]
        assert len(names) == 1
        assert 'C' in names
        names = [s.name for s in manager.list_submissions(benchmark_id=BENCHMARK_2, user_id=USER_3)]
        assert len(names) == 0
