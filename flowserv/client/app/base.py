# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) 2019-2020 NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Helper methods for test runs of workflow templates."""

from typing import Dict, List, Optional, Tuple

import shutil
import tempfile


from flowserv.client.api import ClientAPI
from flowserv.client.app.workflow import Workflow
from flowserv.model.workflow.repository import WorkflowRepository

import flowserv.config as config
import flowserv.util as util
import flowserv.view.workflow as labels


class Flowserv(object):
    """Environment for installing an running workflow templates. This class
    provides additional functionality for installing flowserv components. It
    is primarily intended for testing and/or running flowserv in a notebook
    environment.

    The test environment will keep all workflow files in a folder on the file
    system. The environment uses SQLite as the database backend.

    The enviroment uses a serial workflow engine only at this point. The use
    can choose between running all workflows as separate processes in the local
    Python environment or using the Docker engine.
    """
    def __init__(
        self, env: Optional[Dict] = None, basedir: Optional[str] = None,
        database: Optional[str] = None, open_access: Optional[bool] = None,
        run_async: Optional[bool] = None, docker: Optional[bool] = None,
        s3bucket: Optional[str] = None, clear: Optional[bool] = False,
        user_id: Optional[str] = None
    ):
        """Initialize the components of the test environment. Provides the option
        to alter the default settings of environment variables.

        Parameters
        ----------
        env: dict, default=None
            Dictionary with configuration parameter values.
        basedir: string, default=None
            Base directory for all workflow files. If no directory is given or
            specified in the environment a temporary directory will be created.
        open_access: bool, default=None
            Use an open access policy if set to True.
        run_async: bool, default=False
            Run workflows in asynchronous mode.
        docker: bool, default=False
            Use Docker workflow engine.
        s3bucket: string, default=None
            Use the S3 bucket with the given identifier to store all workflow
            files.
        clear: bool, default=False
            Remove all existing files and folders in the base directory if the
            clear flag is True.
        user_id: string, default=None
            Identifier for an authenticated default user.
        """
        # Get the base configuration settings from the environment if not given.
        self.env = env if env is not None else config.env()
        # Set the base directory and ensure that it exists. Create a temporary
        # directory if no base directory is specified. If a base directory was
        # specified by the user it will override the settings from the global
        # environment.
        basedir = basedir if basedir is not None else self.env.get(config.FLOWSERV_API_BASEDIR)
        self.basedir = basedir if basedir is not None else tempfile.mkdtemp()
        self.env[config.FLOWSERV_API_BASEDIR] = self.basedir
        # Remove all existing files and folders in the base directory if the
        # clear flag is True.
        if clear:
            util.cleardir(self.basedir)
        self.user_id = user_id
        if user_id is None and open_access:
            self.user_id = config.DEFAULT_USER
        self.service = ClientAPI(
            env=self.env,
            basedir=self.basedir,
            database=database,
            open_access=open_access,
            run_async=run_async,
            docker=docker,
            s3bucket=s3bucket
        )

    def erase(self):
        """Delete the base folder for the test environment that contains all
        workflow files.
        """
        shutil.rmtree(self.basedir)

    def install(
        self,
        source: str, identifier: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        specfile: Optional[str] = None,
        manifestfile: Optional[str] = None,
        ignore_postproc: Optional[bool] = False,
        as_app: Optional[bool] = True

    ) -> str:
        """Create a new workflow in the environment that is defined by the
        template referenced by the source parameter. Returns the identifier
        of the created workflow.

        Parameters
        ----------
        source: string
            Path to local template, name or URL of the template in the
            repository.
        identifier: string, default=None
            Unique user-provided workflow identifier. If no identifier is given
            a unique identifier will be generated for the application.
        name: string, default=None
            Unique workflow name
        description: string, default=None
            Optional short description for display in workflow listings
        instructions: string, default=None
            File containing instructions for workflow users.
        specfile: string, default=None
            Path to the workflow template specification file (absolute or
            relative to the workflow directory)
        manifestfile: string, default=None
            Path to manifest file. If not given an attempt is made to read one
            of the default manifest file names in the base directory.
        ignore_postproc: bool, default=False
            Ignore post-processing workflow specification if True.
        as_app: bool, default=True
            Install the workflow as an application. Applications have a single
            group associated with the installed workflow (with same identifier
            as the workflow) and the default user as the only user associated
            with that group.

        Returns
        -------
        string
        """
        with self.service(user_id=self.user_id) as api:
            doc = api.workflows().create_workflow(
                source=source,
                identifier=identifier,
                name=name,
                description=description,
                instructions=instructions,
                specfile=specfile,
                manifestfile=manifestfile,
                ignore_postproc=ignore_postproc
            )
            workflow_id = doc[labels.WORKFLOW_ID]
            if as_app:
                api.groups().create_group(
                    workflow_id=workflow_id,
                    name=workflow_id,
                    identifier=workflow_id
                )
        return workflow_id

    def load(self, workflow_id: str, group_id: str) -> Workflow:
        """Get the handle for a workflow with a given identifier.

        Parameters
        ----------

        Returns
        -------
        flowserv.client.app.workflow.Workflow
        """
        return Workflow(
            workflow_id=workflow_id,
            group_id=group_id,
            service=self.service,
            user_id=self.user_id
        )

    def open(self, identifier: str) -> Workflow:
        """Get an instance of the floserv app for the workflow with the given
        identifier.

        Parameters
        ----------
        identifier: string
            Unique workflow identifier.

        Returns
        -------
        flowserv.client.app.workflow.Workflow
        """
        return self.load(workflow_id=identifier, group_id=identifier)

    def repository(self) -> List[Tuple[str, str]]:
        """Get list of tuples containing the identifier and description for
        each registered workflow template in the global repository.

        Returns
        -------
        list
        """
        return [(tid, desc) for tid, desc, _ in WorkflowRepository().list()]

    def uninstall(self, identifier: str):
        """Remove the workflow with the given identifier. This will also remove
        all run files for that workflow.

        Parameters
        ----------
        identifier: string
            Unique workflow identifier.
        """
        with self.service() as api:
            api.workflows().delete_workflow(workflow_id=identifier)
