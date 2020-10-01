# This file is part of the Reproducible and Reusable Data Analysis Workflow
# Server (flowServ).
#
# Copyright (C) 2019-2020 NYU.
#
# flowServ is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.

"""Helper method to create instances of the flowServ application object."""

from flowserv.app.base import install_app as install  # noqa: F401
from flowserv.app.base import open_app as open  # noqa: F401
from flowserv.app.base import uninstall_app as uninstall  # noqa: F401