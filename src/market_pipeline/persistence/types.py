from enum import StrEnum


class PipelineRunOutcome(StrEnum):
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"


class ProcessingStage(StrEnum):
    ACQUISITION = "acquisition"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
