import pytest
from faker import Faker, providers
from munch import Munch as ObjDict
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import rkwargs
from application.tracker.models import Petition, Record
from application.tracker.models import (
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency,
)
from application.tracker.models import (
    PetitionSchema,
    RecordSchema,
    PetitionNestedSchema,
    RecordNestedSchema,
    SignaturesBySchema,
    SignaturesByCountrySchema,
    SignaturesByRegionSchema,
    SignaturesByConstituencySchema
)
from unittest import mock
from copy import deepcopy
from datetime import datetime as dt
import os, json, logging, requests



logger = logging.getLogger(__name__)
