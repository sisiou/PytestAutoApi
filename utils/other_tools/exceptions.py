#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2022/8/06 15:44
# @Author : 余少琪
描述:
"""


class MyBaseFailure(Exception):
    pass


class JsonpathExtractionFailed(MyBaseFailure):
    pass


class NotFoundError(MyBaseFailure):
    pass


class FileNotFound(FileNotFoundError, NotFoundError):
    pass


class SqlNotFound(NotFoundError):
    pass


class AssertTypeError(MyBaseFailure):
    pass


class DataAcquisitionFailed(MyBaseFailure):
    pass


class ValueTypeError(MyBaseFailure):
    pass


class SendMessageError(MyBaseFailure):
    pass


class ValueNotFoundError(MyBaseFailure):
    pass


class APIParserError(MyBaseFailure):
    pass


class DependencyAnalysisError(MyBaseFailure):
    pass


class TestGenerationError(MyBaseFailure):
    pass


class AssertionGenerationError(MyBaseFailure):
    pass


class DataPreparationError(MyBaseFailure):
    pass


class ReportGenerationError(MyBaseFailure):
    pass


class CoverageScoringError(MyBaseFailure):
    pass
