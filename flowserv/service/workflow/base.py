# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) 2019-2021 NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Base class for the workflow API component that provides methods to create
and access workflows and workflow result rankings.
"""

from abc import ABCMeta, abstractmethod
from typing import Dict, IO, List, Optional

from flowserv.model.template.schema import SortColumn


class WorkflowService(metaclass=ABCMeta):  # pragma: no cover
    """API component that provides methods to access workflows and workflow
    evaluation rankings (benchmark leader boards).
    """
    @abstractmethod
    def get_ranking(
        self, workflow_id: str, order_by: Optional[List[SortColumn]] = None,
        include_all: Optional[bool] = False
    ) -> Dict:
        """Get serialization of the evaluation ranking for the given workflow.

        Parameters
        ----------
        workflow_id: string
            Unique workflow identifier
        order_by: list(flowserv.model.template.schema.SortColumn), default=None
            Use the given attribute to sort run results. If not given, the
            schema default sort order is used
        include_all: bool, default=False
            Include all entries (True) or at most one entry (False) per user
            group in the returned ranking

        Returns
        -------
        dict
        """
        raise NotImplementedError()

    @abstractmethod
    def get_result_archive(self, workflow_id: str) -> IO:
        """Get compressed tar-archive containing all result files that were
        generated by the most recent post-processing workflow. If the workflow
        does not have a post-processing step or if the post-processing workflow
        run is not in SUCCESS state, a unknown resource error is raised.

        Parameters
        ----------
        workflow_id: string
            Unique workflow identifier

        Returns
        -------
        io.BytesIO

        """
        raise NotImplementedError()

    @abstractmethod
    def get_result_file(self, workflow_id: str, file_id: str) -> IO:
        """Get file handle for a file that was generated as the result of a
        successful post-processing workflow run.

        Parameters
        ----------
        workflow_id: string
            Unique workflow identifier
        file_id: string
            Unique resource file identifier

        Returns
        -------
        flowserv.model.files.base.FileHandle

        Raises
        ------
        flowserv.error.UnknownWorkflowError
        flowserv.error.UnknownFileError
        """
        raise NotImplementedError()

    @abstractmethod
    def get_workflow(self, workflow_id: str) -> Dict:
        """Get serialization of the handle for the given workflow.

        Parameters
        ----------
        workflow_id: string
            Unique workflow identifier

        Returns
        -------
        dict
        """
        raise NotImplementedError()

    @abstractmethod
    def list_workflows(self) -> Dict:
        """Get serialized listing of descriptors for all workflows in the
        repository.

        Returns
        -------
        dict
        """
        raise NotImplementedError()
