# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) 2019-2021 NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Unit tests to ensure correctness of the workflow state classes."""

import datetime as dt
import os

from flowserv.model.workflow.state import (
    StateCanceled, StateError, StatePending, StateRunning, StateSuccess
)

import flowserv.util as util


def test_cancel_state():
    """Test creating instances of the cancel state class."""
    created_at = dt.datetime.now()
    started_at = created_at + dt.timedelta(seconds=10)
    stopped_at = started_at + dt.timedelta(seconds=10)
    state = StateCanceled(
        created_at=created_at,
        started_at=started_at,
        stopped_at=stopped_at
    )
    assert state.is_canceled()
    assert not state.is_error()
    assert not state.is_pending()
    assert not state.is_running()
    assert not state.is_success()
    assert not state.is_active()
    assert state.created_at == created_at
    assert state.started_at == started_at
    assert state.stopped_at == stopped_at
    assert len(state.messages) == 1
    state = StateCanceled(
        created_at=created_at,
        started_at=started_at,
        stopped_at=stopped_at,
        messages=['A', 'B', 'C']
    )
    assert state.created_at == created_at
    assert state.started_at == started_at
    assert state.stopped_at == stopped_at
    assert len(state.messages) == 3


def test_error_state():
    """Test creating instances of the error state class."""
    created_at = dt.datetime.now()
    started_at = created_at + dt.timedelta(seconds=10)
    stopped_at = started_at + dt.timedelta(seconds=10)
    state = StateError(
        created_at=created_at,
        started_at=started_at,
        stopped_at=stopped_at
    )
    assert state.is_error()
    assert not state.is_canceled()
    assert not state.is_pending()
    assert not state.is_running()
    assert not state.is_success()
    assert not state.is_active()
    assert state.created_at == created_at
    assert state.started_at == started_at
    assert state.stopped_at == stopped_at
    assert len(state.messages) == 0
    state = StateError(
        created_at=created_at,
        started_at=started_at,
        stopped_at=stopped_at,
        messages=['A', 'B', 'C']
    )
    assert state.created_at == created_at
    assert state.started_at == started_at
    assert state.stopped_at == stopped_at
    assert len(state.messages) == 3


def test_pending_state():
    """Test creating instances of the pending state class."""
    created_at = dt.datetime.now()
    state = StatePending(created_at)
    assert state.is_pending()
    assert state.is_active()
    assert not state.is_canceled()
    assert not state.is_error()
    assert not state.is_running()
    assert not state.is_success()
    assert state.created_at == created_at
    running = state.start()
    assert state.created_at == running.created_at
    assert running.started_at is not None
    # Cancel pending run
    canceled = state.cancel()
    assert canceled.is_canceled()
    assert len(canceled.messages) == 1
    canceled = state.cancel(messages=['by', 'user'])
    assert canceled.is_canceled()
    assert len(canceled.messages) == 2
    # Set pending run into error state
    state = StatePending(created_at)
    error = state.error(messages=['there', 'was', 'a', 'error'])
    assert error.is_error()
    assert len(error.messages) == 4


def test_running_state(tmpdir):
    """Test creating instances of the running state class."""
    created_at = dt.datetime.now()
    started_at = created_at + dt.timedelta(seconds=10)
    state = StateRunning(created_at=created_at, started_at=started_at)
    assert state.is_active()
    assert state.is_running()
    assert not state.is_pending()
    assert not state.is_canceled()
    assert not state.is_error()
    assert not state.is_success()
    assert state.created_at == created_at
    assert state.started_at == started_at
    # Cancel pending run
    canceled = state.cancel()
    assert canceled.is_canceled()
    assert len(canceled.messages) == 1
    canceled = state.cancel(messages=['by', 'user'])
    assert canceled.is_canceled()
    assert len(canceled.messages) == 2
    # Set active run into error state
    error = state.error(messages=['Error', 'State'])
    assert error.created_at == state.created_at
    assert error.started_at == state.started_at
    assert len(error.messages) == 2
    assert error.messages[0] == 'Error'
    assert error.messages[1] == 'State'
    # Set active run to success state
    filename = os.path.join(str(tmpdir), 'myfile.json')
    util.write_object(filename=filename, obj={'A': 1})
    success = state.success(files=['results/myfile.json'])
    assert success.is_success()
    assert not success.is_error()
    assert not success.is_pending()
    assert not success.is_running()
    assert not success.is_active()
    assert success.created_at == state.created_at
    assert success.started_at == state.started_at
    assert len(success.files) == 1
    assert 'results/myfile.json' in success.files


def test_success_state(tmpdir):
    """Test creating instances of the success state class."""
    # Create new file resource for test purposes
    filename = os.path.join(str(tmpdir), 'res.json')
    util.write_object(filename=filename, obj={'A': 1})
    # Create instance of successfule workflow state without a file resource
    created_at = dt.datetime.now()
    started_at = created_at + dt.timedelta(seconds=10)
    finished_at = started_at + dt.timedelta(seconds=10)
    state = StateSuccess(
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at
    )
    assert state.is_success()
    assert not state.is_error()
    assert not state.is_pending()
    assert not state.is_running()
    assert not state.is_active()
    assert state.created_at == created_at
    assert state.started_at == started_at
    assert state.finished_at == finished_at
    assert len(state.files) == 0
    # Create state instance with file resource
    state = StateSuccess(
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        files=['myfile.json']
    )
    assert state.created_at == created_at
    assert state.started_at == started_at
    assert state.finished_at == finished_at
    assert len(state.files) == 1
    assert 'myfile.json' in state.files
