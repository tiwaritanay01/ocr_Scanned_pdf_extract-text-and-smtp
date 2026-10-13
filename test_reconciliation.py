"""
Automated Tests for the Reconciliation Engine
==============================================
Covers all 14 required scenarios from the specification.
Run with: python -m pytest test_reconciliation.py -v
"""

import pytest
from reconciliation import (
    ExaminationAttempt,
    AttemptStatus,
    ClearanceStatus,
    ExceptionType,
    ReconciliationResult,
    ReconciliationException,
    BatchReconciliationSummary,
    normalize_status,
    normalize_identifier,
    detect_duplicates,
    reconcile_student,
    reconcile_batch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_attempt(
    sid="MU2024001",
    name="TEST STUDENT",
    level="SE",
    session="FH 2026",
    semester="sem3",
    status="PASS",
    gpa=8.0,
    pointer="",
    pdf="test.pdf",
    file_id=1,
    exam_type="REGULAR",
):
    return ExaminationAttempt(
        student_identifier=sid,
        student_name=name,
        student_level=level,
        exam_session=session,
        semester=semester,
        attempt_status=normalize_status(status),
        gpa=gpa,
        clearance_pointer=pointer,
        source_pdf=pdf,
        file_id=file_id,
        exam_type=exam_type,
    )


# ---------------------------------------------------------------------------
# Test 1: Student passes in FH 2026 and has no SH result
# ---------------------------------------------------------------------------
class TestCase1PassFHNoSH:
    def test_pass_original_no_subsequent(self):
        attempts = [make_attempt(session="FH 2026", status="PASS")]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.PASSED_ORIGINAL
        assert result.total_attempts == 1
        assert "Passed in original attempt" in result.final_status


# ---------------------------------------------------------------------------
# Test 2: Student passes in both FH 2026 and SH 2026
# ---------------------------------------------------------------------------
class TestCase2PassBoth:
    def test_pass_both_sessions(self):
        attempts = [
            make_attempt(session="FH 2026", status="PASS"),
            make_attempt(session="SH 2026", status="PASS"),
        ]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.PASSED_ORIGINAL
        assert result.total_attempts == 2


# ---------------------------------------------------------------------------
# Test 3: Student fails in FH 2026 and passes in SH 2026
# ---------------------------------------------------------------------------
class TestCase3FailFHPassSH:
    def test_fail_then_clear(self):
        attempts = [
            make_attempt(session="FH 2026", status="FAIL", gpa=0),
            make_attempt(session="SH 2026", status="PASS", gpa=7.5),
        ]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.CLEARED_SUBSEQUENTLY
        assert "FH 2026" in result.final_status
        assert "SH 2026" in result.final_status
        assert result.clearance_session == "SH 2026"

    def test_original_attempt_preserved_as_fail(self):
        """Verify that we do NOT rewrite the original to PASS."""
        attempts = [
            make_attempt(session="FH 2026", status="FAIL", gpa=0),
            make_attempt(session="SH 2026", status="PASS", gpa=7.5),
        ]
        result = reconcile_student(attempts)
        assert result.attempts[0].attempt_status == AttemptStatus.FAIL
        assert result.attempts[1].attempt_status == AttemptStatus.PASS


# ---------------------------------------------------------------------------
# Test 4: Student fails in FH 2026 and fails again in SH 2026
# ---------------------------------------------------------------------------
class TestCase4FailBoth:
    def test_fail_both_uncleared(self):
        attempts = [
            make_attempt(session="FH 2026", status="FAIL"),
            make_attempt(session="SH 2026", status="FAIL"),
        ]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.UNCLEARED
        assert result.total_attempts == 2
        assert "uncleared" in result.final_status.lower()


# ---------------------------------------------------------------------------
# Test 5: Student fails in FH 2026 and has no subsequent result
# ---------------------------------------------------------------------------
class TestCase5FailNoSubsequent:
    def test_fail_pending(self):
        attempts = [make_attempt(session="FH 2026", status="FAIL")]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.PENDING
        assert result.total_attempts == 1

    def test_fail_with_pointer_but_no_result(self):
        """Pointer exists but no subsequent result — needs review."""
        attempts = [
            make_attempt(session="FH 2026", status="FAIL", pointer="CLR-REF-SH2026")
        ]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.NEEDS_REVIEW
        assert "pointer" in result.final_status.lower()


# ---------------------------------------------------------------------------
# Test 6: KT student matches an existing student record
# ---------------------------------------------------------------------------
class TestCase6KTMatch:
    def test_kt_matches_regular(self):
        regular = [make_attempt(session="FH 2026", status="FAIL", exam_type="REGULAR")]
        kt = [make_attempt(session="SH 2026", status="PASS", exam_type="KT")]
        combined = regular + kt
        regular_ids = {normalize_identifier(a.student_identifier) for a in regular}
        summary = reconcile_batch(combined, kt_attempts=kt, regular_identifiers=regular_ids)
        assert summary.total_students == 1
        assert summary.unmatched_kt_count == 0
        assert summary.results[0].clearance_status == ClearanceStatus.CLEARED_SUBSEQUENTLY


# ---------------------------------------------------------------------------
# Test 7: Unmatched KT student
# ---------------------------------------------------------------------------
class TestCase7UnmatchedKT:
    def test_unmatched_kt(self):
        regular = [make_attempt(sid="MU2024001", session="FH 2026", status="FAIL")]
        kt = [make_attempt(sid="MU2024099", name="UNKNOWN KT STUDENT", session="SH 2026", status="PASS", exam_type="KT")]
        combined = regular + kt
        regular_ids = {normalize_identifier(a.student_identifier) for a in regular}
        summary = reconcile_batch(combined, kt_attempts=kt, regular_identifiers=regular_ids)
        assert summary.unmatched_kt_count == 1
        unmatched = [e for e in summary.exceptions if e.exception_type == ExceptionType.UNMATCHED_KT]
        assert len(unmatched) == 1
        assert "MU2024099" in unmatched[0].student_identifier


# ---------------------------------------------------------------------------
# Test 8: Ambiguous clearance pointer
# ---------------------------------------------------------------------------
class TestCase8AmbiguousPointer:
    def test_ambiguous_pointer_flagged(self):
        attempts = [
            make_attempt(session="FH 2026", status="FAIL", pointer="REF-UNKNOWN-2025"),
        ]
        combined = attempts
        regular_ids = {normalize_identifier(a.student_identifier) for a in attempts}
        summary = reconcile_batch(combined, regular_identifiers=regular_ids)
        # The pointer references 2025 but only FH 2026 exists — should flag
        ambiguous = [e for e in summary.exceptions if e.exception_type == ExceptionType.AMBIGUOUS_POINTER]
        assert len(ambiguous) >= 1


# ---------------------------------------------------------------------------
# Test 9: Duplicate PDF upload
# ---------------------------------------------------------------------------
class TestCase9DuplicateUpload:
    def test_duplicate_detected(self):
        att1 = make_attempt(session="FH 2026", status="PASS", pdf="result1.pdf")
        att2 = make_attempt(session="FH 2026", status="PASS", pdf="result2.pdf")
        deduped, exceptions = detect_duplicates([att1, att2])
        assert len(deduped) == 1
        assert len(exceptions) == 1
        assert exceptions[0].exception_type == ExceptionType.DUPLICATE

    def test_idempotent_batch(self):
        """Processing same PDF twice should not create duplicates in summary."""
        att = make_attempt(session="FH 2026", status="PASS")
        summary = reconcile_batch([att, att])
        assert summary.total_students == 1
        assert summary.duplicate_count == 1


# ---------------------------------------------------------------------------
# Test 10: Conflicting results for same student and session
# ---------------------------------------------------------------------------
class TestCase10Conflict:
    def test_conflict_detected(self):
        att1 = make_attempt(session="FH 2026", status="PASS", pdf="v1.pdf")
        att2 = make_attempt(session="FH 2026", status="FAIL", pdf="v2.pdf")
        deduped, exceptions = detect_duplicates([att1, att2])
        assert len(deduped) == 1
        conflicts = [e for e in exceptions if e.exception_type == ExceptionType.CONFLICT]
        assert len(conflicts) == 1
        assert "Conflicting" in conflicts[0].description


# ---------------------------------------------------------------------------
# Test 11: Multiple later attempts with eventual pass
# ---------------------------------------------------------------------------
class TestCase11MultipleLaterAttempts:
    def test_eventual_pass(self):
        attempts = [
            make_attempt(session="FH 2025", status="FAIL"),
            make_attempt(session="SH 2025", status="FAIL"),
            make_attempt(session="FH 2026", status="FAIL"),
            make_attempt(session="SH 2026", status="PASS", gpa=6.5),
        ]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.CLEARED_SUBSEQUENTLY
        assert result.clearance_session == "SH 2026"
        assert result.total_attempts == 4


# ---------------------------------------------------------------------------
# Test 12: Excel export separates original vs consolidated status
# ---------------------------------------------------------------------------
class TestCase12ExportSeparation:
    def test_attempt_status_distinct_from_clearance(self):
        """
        Verify that reconciliation result preserves individual attempt statuses
        separately from the consolidated clearance status.
        """
        attempts = [
            make_attempt(session="FH 2026", status="FAIL"),
            make_attempt(session="SH 2026", status="PASS"),
        ]
        result = reconcile_student(attempts)
        # Individual attempt statuses are preserved
        assert result.attempts[0].attempt_status == AttemptStatus.FAIL
        assert result.attempts[1].attempt_status == AttemptStatus.PASS
        # Consolidated clearance is separate
        assert result.clearance_status == ClearanceStatus.CLEARED_SUBSEQUENTLY
        # The original is NOT changed to PASS
        assert result.attempts[0].attempt_status != AttemptStatus.PASS


# ---------------------------------------------------------------------------
# Test 13: Batch filtering includes all history for reconciliation
# ---------------------------------------------------------------------------
class TestCase13BatchFiltering:
    def test_cross_session_history_included(self):
        """
        Selecting SH 2026 for export must still include FH 2026 data
        to correctly compute clearance.
        """
        attempts = [
            make_attempt(session="FH 2026", status="FAIL"),
            make_attempt(session="SH 2026", status="PASS"),
        ]
        summary = reconcile_batch(attempts)
        assert summary.total_students == 1
        assert summary.cleared_count == 1
        # Both sessions present in session_counts
        assert "FH 2026" in summary.session_counts
        assert "SH 2026" in summary.session_counts


# ---------------------------------------------------------------------------
# Test 14: Existing FE/SE/TE/BE processing is not affected (non-regression)
# ---------------------------------------------------------------------------
class TestCase14NonRegression:
    def test_regular_pass_still_works(self):
        """Regular PASS result reconciliation is unchanged."""
        attempts = [make_attempt(session="FH 2026", status="PASS", exam_type="REGULAR")]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.PASSED_ORIGINAL

    def test_regular_fail_still_works(self):
        """Regular FAIL result reconciliation is unchanged."""
        attempts = [make_attempt(session="FH 2026", status="FAIL", exam_type="REGULAR")]
        result = reconcile_student(attempts)
        assert result.clearance_status == ClearanceStatus.PENDING

    def test_mixed_regular_and_kt(self):
        """KT additions don't break regular reconciliation."""
        regular = [
            make_attempt(sid="MU001", session="FH 2026", status="PASS", exam_type="REGULAR"),
            make_attempt(sid="MU002", session="FH 2026", status="FAIL", exam_type="REGULAR"),
        ]
        kt = [
            make_attempt(sid="MU002", session="SH 2026", status="PASS", exam_type="KT"),
        ]
        combined = regular + kt
        regular_ids = {normalize_identifier(a.student_identifier) for a in regular}
        summary = reconcile_batch(combined, kt_attempts=kt, regular_identifiers=regular_ids)
        assert summary.total_students == 2
        assert summary.pass_count == 1  # MU001 passed original
        assert summary.cleared_count == 1  # MU002 cleared via KT


# ---------------------------------------------------------------------------
# Additional Edge Cases
# ---------------------------------------------------------------------------

class TestNormalizeStatus:
    @pytest.mark.parametrize("raw,expected", [
        ("PASS", AttemptStatus.PASS),
        ("P", AttemptStatus.PASS),
        ("pass", AttemptStatus.PASS),
        ("FAIL", AttemptStatus.FAIL),
        ("F", AttemptStatus.FAIL),
        ("FAILED", AttemptStatus.FAIL),
        ("UNKNOWN", AttemptStatus.UNKNOWN),
        ("", AttemptStatus.UNKNOWN),
        (None, AttemptStatus.UNKNOWN),
        ("GARBAGE", AttemptStatus.UNKNOWN),
    ])
    def test_normalize(self, raw, expected):
        assert normalize_status(raw) == expected


class TestSessionOrdering:
    def test_fh_before_sh(self):
        attempts = [
            make_attempt(session="SH 2026", status="PASS"),
            make_attempt(session="FH 2026", status="FAIL"),
        ]
        result = reconcile_student(attempts)
        # After sorting, FH should come first
        assert result.attempts[0].exam_session == "FH 2026"
        assert result.attempts[1].exam_session == "SH 2026"
        assert result.clearance_status == ClearanceStatus.CLEARED_SUBSEQUENTLY


class TestEmptyInput:
    def test_no_attempts(self):
        result = reconcile_student([])
        assert result.clearance_status == ClearanceStatus.INSUFFICIENT_EVIDENCE

    def test_empty_batch(self):
        summary = reconcile_batch([])
        assert summary.total_students == 0


class TestBatchSummarySessionCounts:
    def test_session_counts_accurate(self):
        attempts = [
            make_attempt(sid="S1", session="FH 2026", status="PASS"),
            make_attempt(sid="S2", session="FH 2026", status="FAIL"),
            make_attempt(sid="S3", session="SH 2026", status="PASS"),
            make_attempt(sid="S2", session="SH 2026", status="PASS"),
        ]
        summary = reconcile_batch(attempts)
        assert summary.session_counts["FH 2026"]["PASS"] == 1
        assert summary.session_counts["FH 2026"]["FAIL"] == 1
        assert summary.session_counts["SH 2026"]["PASS"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
