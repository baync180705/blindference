INFERENCE_REQUESTS = "inference_requests"
QUORUM_ASSIGNMENTS = "quorum_assignments"
VERIFIER_VERDICTS = "verifier_verdicts"
QUORUM_CERTIFICATES = "quorum_certificates"
MODEL_CATALOG = "model_catalog"
DISPUTES = "disputes"
OPERATORS = "operators"


def get_collection_names() -> list[str]:
    return [
        INFERENCE_REQUESTS,
        QUORUM_ASSIGNMENTS,
        VERIFIER_VERDICTS,
        QUORUM_CERTIFICATES,
        MODEL_CATALOG,
        DISPUTES,
        OPERATORS,
    ]
