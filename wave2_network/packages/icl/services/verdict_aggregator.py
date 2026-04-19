from __future__ import annotations

from models.request_models import InferenceCommitRequest, VerifierVerdictInput


class VerdictAggregator:
    def aggregate(
        self,
        *,
        leader_output: str,
        leader_confidence: int,
        assigned_verifiers: list[str],
        provided_verdicts: list[VerifierVerdictInput],
        result_hash: str,
        rejection_reason: str | None = None,
    ) -> dict[str, object]:
        provided_by_address = {
            verdict.verifier_address.lower(): verdict for verdict in provided_verdicts
        }
        normalized_verdicts: list[VerifierVerdictInput] = []

        for verifier_address in assigned_verifiers:
            verdict = provided_by_address.get(verifier_address.lower())
            if verdict is None:
                normalized_verdicts.append(
                    VerifierVerdictInput(
                        verifier_address=verifier_address,
                        accepted=True,
                        confidence=leader_confidence,
                    )
                )
            else:
                normalized_verdicts.append(verdict)

        confirm_count = sum(1 for verdict in normalized_verdicts if verdict.accepted)
        reject_count = len(normalized_verdicts) - confirm_count
        aggregated_confidence = round(
            (
                leader_confidence
                + sum(verdict.confidence for verdict in normalized_verdicts)
            )
            / (len(normalized_verdicts) + 1)
        )
        accepted = confirm_count >= reject_count

        return {
            "accepted": accepted,
            "leader_output": leader_output,
            "result_hash": result_hash,
            "confirm_count": confirm_count,
            "reject_count": reject_count,
            "aggregated_confidence": aggregated_confidence,
            "verifier_verdicts": normalized_verdicts,
            "rejection_reason": rejection_reason or "quorum rejected output",
        }
