# This file is part of the Reproducible Open Benchmarks for Data Analysis
# Platform (ROB).
#
# Copyright (C) 2019 NYU.
#
# ROB is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""The run handle provides access to the run state, error messages, and any
resource files that have been generated by successful workflow runs.
"""

class RunHandle(object):
    """Basic information about workflow runs. Maintains the run identifier and
    the current run state.
    """
    def __init__(self, identifier, submission_id, state, arguments):
        """Initialize the object properties.

        Parameters
        ----------
        identifier: string
            Unique run identifier
        submission_id: string
            Unique identifier of the submission
        state: robcore.model.workflow.state.WorkflowState
            Current workflow run state
        arguments: dict()
            Dictionary of user-provided argument values for the run
        """
        self.identifier = identifier
        self.submission_id = submission_id
        self.state = state
        self.arguments = arguments

    def get_resource(self, identifier):
        """Get the file resource with the given identifier.

        Parameters
        ----------
        identifier: string
            Unique resource identifier

        Returns
        -------
        robcore.model.workflow.resource.FileResource
        """
        if not self.is_success():
            return None
        else:
            return self.state.get_resource(identifier)

    def is_active(self):
        """A run is in active state if it is either pending or running.

        Returns
        --------
        bool
        """
        return self.state.is_active()

    def is_canceled(self):
        """Returns True if the workflow state is of type CANCELED.

        Returns
        -------
        bool
        """
        return self.state.is_canceled()

    def is_error(self):
        """Returns True if the workflow state is of type ERROR.

        Returns
        -------
        bool
        """
        return self.state.is_error()

    def is_pending(self):
        """Returns True if the workflow state is of type PENDING.

        Returns
        -------
        bool
        """
        return self.state.is_pending()

    def is_running(self):
        """Returns True if the workflow state is of type RUNNING.

        Returns
        -------
        bool
        """
        return self.state.is_running()

    def is_success(self):
        """Returns True if the workflow state is of type SUCCESS.

        Returns
        -------
        bool
        """
        return self.state.is_success()

    def list_resources(self):
        """Shortcut to access all associated file resources.

        Returns
        -------
        list(robcore.model.workflow.resource.FileResource)
        """
        if not self.is_success():
            return list()
        else:
            return self.state.files.values()
