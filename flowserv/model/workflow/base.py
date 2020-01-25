# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) [2019-2020] NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Descriptor and handle for workflow definitions that are maintained by the
API in a workflow repository.
"""

from flowserv.model.template.base import WorkflowTemplate
from flowserv.model.workflow.resource import ResourceSet


class WorkflowDescriptor(object):
    """the workflow descriptor maintains basic information about a workflows in
    a repository. The descriptors are primarily intended for workflow listings
    that only display the basic workflow information. All additional objects
    that are associated with a workflow are contained in the workflow handle
    that extends the workflow descriptor.
    """
    def __init__(
        self, identifier, name=None, description=None, instructions=None
    ):
        """Initialize the descriptor properties. If no name is given the
        identifier is used as a name.

        Parameters
        ----------
        identifier: string
            Unique workflow identifier
        template: flowserv.model.template.base.WorkflowTemplate
            Template for the associated workflow
        name: string, optional
            Descriptive workflow name
        description: string, optional
            Optional short description for display in workflow listings
        instructions: string, optional
            Text containing detailed instructions for running the workflow
        """
        self.identifier = identifier
        self.name = name if name is not None else identifier
        self.description = description
        self.instructions = instructions

    def get_description(self):
        """Get value of description property. If the value of the property is
        None an empty string is returned instead.

        Returns
        -------
        string
        """
        return self.description if self.description is not None else ''

    def get_instructions(self):
        """Get value of instructions property. If the value of the property is
        None an empty string is returned instead.

        Returns
        -------
        string
        """
        return self.instructions if self.instructions is not None else ''

    def has_description(self):
        """Shortcut to test of the description attribute is set.

        Returns
        -------
        bool
        """
        return self.description is not None

    def has_instructions(self):
        """Test if the instructions for the workflow are set.

        Returns
        -------
        bool
        """
        return self.instructions is not None


class WorkflowHandle(WorkflowDescriptor):
    """The workflow handle extends the workflow descriptor with references to
    the workflow template and the current workflow metric resources that are
    generated by an (optional) post-processing step.
    """
    def __init__(
        self, identifier, template, name=None, description=None,
        instructions=None, resources=None
    ):
        """Initialize the handle properties. If no name is given the
        identifier is used as a name.

        Parameters
        ----------
        identifier: string
            Unique workflow identifier
        template: flowserv.model.template.base.WorkflowTemplate
            Template for the associated workflow
        name: string, optional
            Descriptive workflow name
        description: string, optional
            Optional short description for display in workflow listings
        instructions: string, optional
            Text containing detailed instructions for running the workflow
        resources: list(flowserv.model.workflow.resource.WorkflowResource), optional
            Optional list of resources that are generated by the optional
            post-processing task for the workflow.
        """
        super(WorkflowHandle, self).__init__(
            identifier=identifier,
            name=name,
            description=description,
            instructions=instructions
        )
        self.template = template
        self.resources = ResourceSet(resources)

    def get_template(self, workflow_spec=None, parameters=None):
        """Get associated workflow template. The template is loaded on-demand
        if necessary. If either of the optional parameters are given, a modified
        copy of the template is returned.

        Returns
        -------
        flowserv.model.template.base.WorkflowTemplate
        """
        # If any of the optional parameters are given return a modified copy of
        # the workflow template.
        if workflow_spec and parameters:
            return WorkflowTemplate(
                workflow_spec=workflow_spec,
                parameters=parameters,
                sourcedir=self.template.sourcedir,
                result_schema=self.template.result_schema,
                modules=self.template.modules,
                postproc_spec=self.template.postproc_spec
            )
        elif workflow_spec:
            return WorkflowTemplate(
                workflow_spec=workflow_spec,
                parameters=self.template.parameters,
                sourcedir=self.template.sourcedir,
                result_schema=self.template.result_schema,
                modules=self.template.modules,
                postproc_spec=self.template.postproc_spec
            )
        elif parameters:
            return WorkflowTemplate(
                workflow_spec=self.template.workflow_spec,
                parameters=parameters,
                sourcedir=self.template.sourcedir,
                result_schema=self.template.result_schema,
                modules=self.template.modules,
                postproc_spec=self.template.postproc_spec
            )
        return self.template
