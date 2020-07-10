# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) 2019-2020 NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Unit tests for post-processing workflows."""

import os
import time

from flowserv.config.api import FLOWSERV_API_BASEDIR
from flowserv.config.database import FLOWSERV_DB
from flowserv.controller.serial.engine import SerialWorkflowEngine
from flowserv.service.api import service
from flowserv.service.run import ARG_ID, ARG_VALUE
from flowserv.tests.files import FakeStream
from flowserv.tests.service import (
    create_group, create_user, create_workflow, start_run, upload_file
)

import flowserv.util as util
import flowserv.model.workflow.state as st
import flowserv.tests.serialize as serialize


# Template directory
DIR = os.path.dirname(os.path.realpath(__file__))
SPEC_FILE = os.path.join(DIR, '../.files/benchmark/postproc/benchmark.yaml')
SPEC_FILE_ERR_1 = os.path.join(DIR, '../.files/benchmark/postproc/error1.yaml')
SPEC_FILE_ERR_2 = os.path.join(DIR, '../.files/benchmark/postproc/error2.yaml')
TEMPLATE_DIR = os.path.join(DIR, '../.files/benchmark/helloworld')


# List of names for input files
NAMES = ['Alice', 'Bob', 'Gabriel', 'William']


def test_postproc_workflow(tmpdir):
    """Execute the modified helloworld example."""
    # -- Setup ----------------------------------------------------------------
    #
    # Start a new run for the workflow template.
    os.environ[FLOWSERV_DB] = 'sqlite:///{}/flowserv.db'.format(str(tmpdir))
    os.environ[FLOWSERV_API_BASEDIR] = str(tmpdir)
    from flowserv.service.database import database
    database.init()
    engine = SerialWorkflowEngine(is_async=True)
    with service(engine=engine) as api:
        workflow_id = create_workflow(
            api,
            sourcedir=TEMPLATE_DIR,
            specfile=SPEC_FILE
        )
        user_id = create_user(api)
    # Create four groups and run the workflow with a slightly different input
    # file
    for i in range(4):
        with service(engine=engine) as api:
            group_id = create_group(api, workflow_id, [user_id])
            names = FakeStream(data=NAMES[:(i+1)], format='plain/text')
            file_id = upload_file(api, group_id, user_id, names)
            # Set the template argument values
            arguments = [
                {ARG_ID: 'names', ARG_VALUE: file_id},
                {ARG_ID: 'greeting', ARG_VALUE: 'Hi'}
            ]
            run_id = start_run(api, group_id, user_id, arguments=arguments)
        # Poll workflow state every second.
        run = poll_run(service, engine, run_id, user_id)
        assert run['state'] == st.STATE_SUCCESS
        with service(engine=engine) as api:
            wh = api.workflows().get_workflow(workflow_id=workflow_id)
        while 'postproc' not in wh:
            time.sleep(1)
            with service(engine=engine) as api:
                wh = api.workflows().get_workflow(workflow_id=workflow_id)
        serialize.validate_workflow_handle(wh)
        while wh['postproc']['state'] in st.ACTIVE_STATES:
            time.sleep(1)
            with service(engine=engine) as api:
                wh = api.workflows().get_workflow(workflow_id=workflow_id)
        serialize.validate_workflow_handle(wh)
        for fobj in wh['postproc']['files']:
            if fobj['name'] == 'results/compare.json':
                file_id = fobj['id']
        with service(engine=engine) as api:
            fh = api.runs().get_result_file(
                run_id=wh['postproc']['id'],
                file_id=file_id,
                user_id=None
            )
        compare = util.read_object(fh.filename)
        assert len(compare) == (i + 1)
    # Clean-up environment variables
    del os.environ[FLOWSERV_DB]
    del os.environ[FLOWSERV_API_BASEDIR]


def test_postproc_workflow_errors(tmpdir):
    """Execute the modified helloworld example."""
    # -- Setup ----------------------------------------------------------------
    #
    # Start a new run for the workflow template.
    os.environ[FLOWSERV_DB] = 'sqlite:///{}/flowserv.db'.format(str(tmpdir))
    os.environ[FLOWSERV_API_BASEDIR] = str(tmpdir)
    from flowserv.service.database import database
    database.init()
    engine = SerialWorkflowEngine(is_async=True)
    # Error during data preparation
    run_erroneous_workflow(service, engine, SPEC_FILE_ERR_1)
    # Erroneous specification
    run_erroneous_workflow(service, engine, SPEC_FILE_ERR_2)
    # Clean-up environment variables
    del os.environ[FLOWSERV_DB]
    del os.environ[FLOWSERV_API_BASEDIR]


# -- Helper functions ---------------------------------------------------------

def poll_run(service, engine, run_id, user_id):
    """Poll workflow run while in active state."""
    with service(engine=engine) as api:
        run = api.runs().get_run(run_id=run_id, user_id=user_id)
    while run['state'] in st.ACTIVE_STATES:
        time.sleep(1)
        with service(engine=engine) as api:
            run = api.runs().get_run(run_id=run_id, user_id=user_id)
    return run


def run_erroneous_workflow(service, engine, specfile):
    """Execute the modified helloworld example."""
    with service(engine=engine) as api:
        # Create workflow template, user, and the workflow group.
        workflow_id = create_workflow(
            api,
            sourcedir=TEMPLATE_DIR,
            specfile=specfile
        )
        user_id = create_user(api)
        group_id = create_group(api, workflow_id, [user_id])
        # Upload the names file.
        names = FakeStream(data=NAMES, format='txt/plain')
        file_id = upload_file(api, group_id, user_id, names)
        # Run the workflow.
        arguments = [
            {'id': 'names', 'value': file_id},
            {'id': 'greeting', 'value': 'Hi'}
        ]
        run_id = start_run(api, group_id, user_id, arguments=arguments)
    # Poll workflow state every second.
    run = poll_run(service, engine, run_id, user_id)
    assert run['state'] == st.STATE_SUCCESS
    with service(engine=engine) as api:
        wh = api.workflows().get_workflow(workflow_id=workflow_id)
    while 'postproc' not in wh:
        time.sleep(1)
        with service(engine=engine) as api:
            wh = api.workflows().get_workflow(workflow_id=workflow_id)
    serialize.validate_workflow_handle(wh)
    while wh['postproc']['state'] in st.ACTIVE_STATES:
        time.sleep(1)
        with service(engine=engine) as api:
            wh = api.workflows().get_workflow(workflow_id=workflow_id)
    serialize.validate_workflow_handle(wh)
    assert wh['postproc']['state'] == st.STATE_ERROR
