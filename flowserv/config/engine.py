# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) [2019-2020] NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""This module defines environment variables that are used to configure the
workflow engine. In addition, the module provides a function to get an instance
of the workflow controller that is specified by the defined environment
variables.

Workflow controllers are specified using the name of the module and the name
of the class that implements the controller. The specified class is imported
dynamically.

Different workflow controllers may define additional environment variables to
control their configuration.
"""

import os
import tempfile

import flowserv.config.api as api
import flowserv.config.base as config
import flowserv.core.error as err


"""Environment variables that are used to create an instance of the workflow
controller that is used by the workflow engine to execute workflows.
"""
# Name of the class that implements the workflow controller interface
FLOWSERV_ENGINE_CLASS = 'FLOWSERV_ENGINE_CLASS'
# Name of the module that contains the workflow controller implementation
FLOWSERV_ENGINE_MODULE = 'FLOWSERV_ENGINE_MODULE'


def ENGIN_BASEDIR():
    """Get base directory for workflow engine from the environment. At this
    point we store run files in a sub-folder of the API base directory. If the
    API base directory is not set the local director for temporary files is
    used.

    Returns
    -------
    string
    """
    basedir = api.API_BASEDIR(default_value=str(tempfile.gettempdir()))
    return os.path.join(basedir, 'runs')


def FLOWSERV_ENGINE():
    """Get an instance of the workflow controller that is specified by the two
    environment variables 'FLOWSERV_ENGINE_MODULE' and 'FLOWSERV_ENGINE_CLASS'. It is
    expected that either both variables contain a non-emoty value or none of
    then is set. In the latter case, the synchronous workflow controller is
    returned as the default.

    Returns
    -------
    flowserv.controller.base.WorkflowController

    Raises
    ------
    flowserv.core.error.MissingConfigurationError
    """
    module_name = config.get_variable(name=FLOWSERV_ENGINE_MODULE)
    class_name = config.get_variable(name=FLOWSERV_ENGINE_CLASS)
    # If both environment variables are None return the default controller.
    # Otherwise, import the specified module and return an instance of the
    # controller class. An error is raised if only one of the two environment
    # variables is set.
    if module_name is None and class_name is None:
        from flowserv.controller.sync import SyncWorkflowEngine
        return SyncWorkflowEngine(basedir=ENGIN_BASEDIR())
    elif module_name is not None and class_name is not None:
        from importlib import import_module
        module = import_module(module_name)
        return getattr(module, class_name)()
    elif module_name is None:
        raise err.MissingConfigurationError(FLOWSERV_ENGINE_MODULE)
    else:
        raise err.MissingConfigurationError(FLOWSERV_ENGINE_CLASS)
