"""
Result Reconciliation Engine
=============================
Pure-logic module that operates on student examination attempt records.
No OCR or database dependency — designed for independent testability.

Concepts:
  - Attempt Status: The actual PASS/FAIL recorded for a specific exam session.
  - Consolidated Clearance Status: Whether available records establish that
    an earlier failure was cleared in a subsequent examination.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
from collections import defaultdict


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

class AttemptStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ClearanceStatus(Enum):
    PASSED_ORIGINAL = "PASSED_ORIGINAL"          # Passed in the original attempt
    CLEARED_SUBSEQUENTLY = "CLEARED_SUBSEQUENTLY"  # Failed originally, cleared later
    UNCLEARED = "UNCLEARED"                      # Failure still not cleared
    PENDING = "PENDING"                          # No subsequent result available
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Cannot determine
    NEEDS_REVIEW = "NEEDS_REVIEW"                # Ambiguous — manual review


class ExceptionType(Enum):
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    UNMATCHED_KT = "UNMATCHED_KT"
    AMBIGUOUS_POINTER = "AMBIGUOUS_POINTER"
    MISSING_IDENTIFIER = "MISSING_IDENTIFIER"
    INVALID_STATUS = "INVALID_STATUS"


# Session ordering helper — FH (First Half) comes before SH (Second Half)
# within the same year; years are compared numerically.
SESSION_ORDER = {"FH": 0, "SH": 1}


def _session_sort_key(session: str) -> Tuple[int, int]:
    """Return (year, half) for sorting. E.g. 'FH 2026' -> (2026, 0)."""
    parts = session.strip().split()
    if len(parts) == 2:
        half = SESSION_ORDER.get(parts[0].upper(), 99)
        try:
            year = int(parts[1])
        except ValueError:
            year = 9999
        return (year, half)
    return (9999, 99)


@dataclass
class ExaminationAttempt:
    """A single examination attempt record."""
    attempt_id: Optional[int] = None
    student_identifier: str = ""       # ERN, seat number, or unique ID
    student_name: str = ""
    student_level: str = ""            # FE / SE / TE / BE
    exam_session: str = ""             # e.g. "FH 2026"
    semester: str = ""                 # e.g. "sem3"
    attempt_status: AttemptStatus = AttemptStatus.UNKNOWN
    gpa: float = 0.0
    clearance_pointer: str = ""        # OCR-extracted pointer reference
    source_pdf: str = ""
    file_id: Optional[int] = None
    exam_type: str = "REGULAR"         # REGULAR or KT


@dataclass
class ReconciliationResult:
    """Consolidated view for one student."""
    student_identifier: str = ""
    student_name: str = ""
    student_level: str = ""
    attempts: List[ExaminationAttempt] = field(default_factory=list)
    clearance_status: ClearanceStatus = ClearanceStatus.INSUFFICIENT_EVIDENCE
    clearance_session: str = ""        # Session in which failure was cleared
    clearance_pointer: str = ""
    final_status: str = ""             # Human-readable summary
    total_attempts: int = 0
    review_flags: List[str] = field(default_factory=list)


@dataclass
class ReconciliationException:
    """An exception/issue detected during reconciliation."""
    student_identifier: str = ""
    student_name: str = ""
    exception_type: ExceptionType = ExceptionType.CONFLICT
    description: str = ""
    action_required: str = ""
    related_attempts: List[ExaminationAttempt] = field(default_factory=list)


@dataclass
class BatchReconciliationSummary:
    """Summary for a batch reconciliation run."""
    total_students: int = 0
    pass_count: int = 0
    fail_count: int = 0
    cleared_count: int = 0
    uncleared_count: int = 0
    pending_count: int = 0
    duplicate_count: int = 0
    conflict_count: int = 0
    unmatched_kt_count: int = 0
    needs_review_count: int = 0
    results: List[ReconciliationResult] = field(default_factory=list)
    exceptions: List[ReconciliationException] = field(default_factory=list)
    # Pass/Fail by session
    session_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

def normalize_status(raw: str) -> AttemptStatus:
    """Normalize various status representations to AttemptStatus enum."""
    if not raw:
        return AttemptStatus.UNKNOWN
    s = str(raw).strip().upper()
    if s in ("PASS", "P", "SUCCESS", "SUCCESSFUL", "PASSED"):
        return AttemptStatus.PASS
    if s in ("FAIL", "F", "FAILED", "UNSUCCESSFUL"):
        return AttemptStatus.FAIL
    return AttemptStatus.UNKNOWN


def normalize_identifier(raw: str) -> str:
    """Normalize student identifier for matching."""
    return str(raw).strip().upper() if raw else ""


# ---------------------------------------------------------------------------
# Core Reconciliation Functions
# ---------------------------------------------------------------------------

def detect_duplicates(attempts: List[ExaminationAttempt]) -> Tuple[List[ExaminationAttempt], List[ReconciliationException]]:
    """
    Detect duplicate attempts (same student, session, semester, exam_type).
    Returns deduplicated list and list of exceptions.
    """
    seen = {}
    deduped = []
    exceptions = []

    for att in attempts:
        key = (
            normalize_identifier(att.student_identifier),
            att.exam_session.strip(),
            att.semester.strip(),
            att.exam_type.strip()
        )
        if key in seen:
            existing = seen[key]
            # Check for conflict (different status)
            if existing.attempt_status != att.attempt_status:
                exceptions.append(ReconciliationException(
                    student_identifier=att.student_identifier,
                    student_name=att.student_name,
                    exception_type=ExceptionType.CONFLICT,
                    description=(
                        f"Conflicting results for {att.exam_session} {att.semester}: "
                        f"existing={existing.attempt_status.value}, new={att.attempt_status.value}"
                    ),
                    action_required="Review and resolve the conflicting results manually.",
                    related_attempts=[existing, att]
                ))
            else:
                exceptions.append(ReconciliationException(
                    student_identifier=att.student_identifier,
                    student_name=att.student_name,
                    exception_type=ExceptionType.DUPLICATE,
                    description=(
                        f"Duplicate attempt for {att.exam_session} {att.semester} "
                        f"(status={att.attempt_status.value})"
                    ),
                    action_required="Duplicate record ignored. No action required.",
                    related_attempts=[existing, att]
                ))
        else:
            seen[key] = att
            deduped.append(att)

    return deduped, exceptions


def reconcile_student(attempts: List[ExaminationAttempt]) -> ReconciliationResult:
    """
    Reconcile all attempts for a single student.
    Implements Cases A through F from the specification.
    """
    if not attempts:
        return ReconciliationResult()

    first = attempts[0]
    result = ReconciliationResult(
        student_identifier=first.student_identifier,
        student_name=first.student_name,
        student_level=first.student_level,
        attempts=sorted(attempts, key=lambda a: _session_sort_key(a.exam_session)),
        total_attempts=len(attempts),
    )

    sorted_attempts = result.attempts

    # Separate regular and KT attempts
    regular = [a for a in sorted_attempts if a.exam_type == "REGULAR"]
    kt = [a for a in sorted_attempts if a.exam_type == "KT"]

    # Validate identifiers
    for att in sorted_attempts:
        if not att.student_identifier or att.student_identifier in ("N/A", "NOT_FOUND", ""):
            result.review_flags.append(f"Missing/invalid identifier in {att.exam_session}")

    # Find the earliest attempt and its status
    if not regular and not kt:
        result.clearance_status = ClearanceStatus.INSUFFICIENT_EVIDENCE
        result.final_status = "No examination records available"
        return result

    all_sorted = sorted(regular + kt, key=lambda a: _session_sort_key(a.exam_session))

    # --- Determine clearance status ---

    # Case A: First/earliest attempt is PASS
    first_attempt = all_sorted[0]

    if first_attempt.attempt_status == AttemptStatus.PASS:
        # Case A: Passed originally
        result.clearance_status = ClearanceStatus.PASSED_ORIGINAL
        result.final_status = "Passed in original attempt"
        return result

    if first_attempt.attempt_status == AttemptStatus.UNKNOWN:
        result.clearance_status = ClearanceStatus.INSUFFICIENT_EVIDENCE
        result.review_flags.append(f"First attempt status is UNKNOWN in {first_attempt.exam_session}")
        result.final_status = "Insufficient evidence to determine clearance"
        return result

    # First attempt is FAIL — check subsequent attempts
    subsequent = all_sorted[1:]

    if not subsequent:
        # Case D: Failed, no subsequent result
        # Check for clearance pointer
        if first_attempt.clearance_pointer and first_attempt.clearance_pointer.strip():
            result.clearance_status = ClearanceStatus.NEEDS_REVIEW
            result.clearance_pointer = first_attempt.clearance_pointer
            result.review_flags.append(
                f"Clearance pointer found ({first_attempt.clearance_pointer}) but no matching subsequent result"
            )
            result.final_status = "Failed; clearance pointer exists but no subsequent result — needs review"
        else:
            result.clearance_status = ClearanceStatus.PENDING
            result.final_status = "Failed; no subsequent result available"
        return result

    # Check subsequent attempts for a PASS
    clearing_attempt = None
    for att in subsequent:
        if att.attempt_status == AttemptStatus.PASS:
            clearing_attempt = att
            break

    if clearing_attempt:
        # Case B: Failed originally, passed subsequently
        result.clearance_status = ClearanceStatus.CLEARED_SUBSEQUENTLY
        result.clearance_session = clearing_attempt.exam_session
        if clearing_attempt.clearance_pointer:
            result.clearance_pointer = clearing_attempt.clearance_pointer
        elif first_attempt.clearance_pointer:
            result.clearance_pointer = first_attempt.clearance_pointer
        elif clearing_attempt.gpa > 0:
            result.clearance_pointer = f"{clearing_attempt.gpa:.2f}"
        result.final_status = (
            f"Failed in {first_attempt.exam_session}; "
            f"cleared in {clearing_attempt.exam_session}"
        )
        # Validate clearance pointer if present
        if result.clearance_pointer:
            result.review_flags.append(
                f"Clearance pointer present: {result.clearance_pointer}"
            )
        return result

    # Case C: Failed in all subsequent attempts too
    all_fail = all(a.attempt_status == AttemptStatus.FAIL for a in subsequent)
    has_unknown = any(a.attempt_status == AttemptStatus.UNKNOWN for a in subsequent)

    if all_fail:
        result.clearance_status = ClearanceStatus.UNCLEARED
        result.final_status = f"Failed in all {len(all_sorted)} attempts; failure uncleared"
        return result

    if has_unknown:
        result.clearance_status = ClearanceStatus.INSUFFICIENT_EVIDENCE
        result.review_flags.append("One or more subsequent attempts have UNKNOWN status")
        result.final_status = "Insufficient evidence — some attempts have unknown status"
        return result

    result.clearance_status = ClearanceStatus.INSUFFICIENT_EVIDENCE
    result.final_status = "Unable to determine clearance from available data"
    return result


def reconcile_batch(
    all_attempts: List[ExaminationAttempt],
    kt_attempts: Optional[List[ExaminationAttempt]] = None,
    regular_identifiers: Optional[set] = None,
) -> BatchReconciliationSummary:
    """
    Reconcile a batch of examination attempts.

    Parameters:
        all_attempts: Combined list of regular + KT attempts
        kt_attempts: Optional separate KT list for unmatched detection
        regular_identifiers: Set of known regular student identifiers
    """
    summary = BatchReconciliationSummary()
    all_exceptions = []

    # Step 1: Validate identifiers
    for att in all_attempts:
        if not att.student_identifier or att.student_identifier in ("N/A", "NOT_FOUND", ""):
            all_exceptions.append(ReconciliationException(
                student_identifier=att.student_identifier,
                student_name=att.student_name,
                exception_type=ExceptionType.MISSING_IDENTIFIER,
                description=f"Missing/invalid student identifier in {att.exam_session}",
                action_required="Assign a valid student identifier before reconciliation.",
                related_attempts=[att]
            ))
        if att.attempt_status == AttemptStatus.UNKNOWN:
            all_exceptions.append(ReconciliationException(
                student_identifier=att.student_identifier,
                student_name=att.student_name,
                exception_type=ExceptionType.INVALID_STATUS,
                description=f"Unknown/unrecognized status in {att.exam_session}: not PASS or FAIL",
                action_required="Review and set the correct PASS/FAIL status.",
                related_attempts=[att]
            ))

    # Step 2: Detect duplicates/conflicts
    deduped, dup_exceptions = detect_duplicates(all_attempts)
    all_exceptions.extend(dup_exceptions)
    summary.duplicate_count = sum(1 for e in dup_exceptions if e.exception_type == ExceptionType.DUPLICATE)
    summary.conflict_count = sum(1 for e in dup_exceptions if e.exception_type == ExceptionType.CONFLICT)

    # Step 3: Group by student
    student_groups: Dict[str, List[ExaminationAttempt]] = defaultdict(list)
    for att in deduped:
        key = normalize_identifier(att.student_identifier)
        if key and key not in ("N/A", "NOT_FOUND"):
            student_groups[key].append(att)

    # Step 4: Detect unmatched KT students (Case E)
    if kt_attempts and regular_identifiers:
        for kt_att in kt_attempts:
            kt_id = normalize_identifier(kt_att.student_identifier)
            if kt_id and kt_id not in regular_identifiers:
                all_exceptions.append(ReconciliationException(
                    student_identifier=kt_att.student_identifier,
                    student_name=kt_att.student_name,
                    exception_type=ExceptionType.UNMATCHED_KT,
                    description=(
                        f"KT student {kt_att.student_identifier} ({kt_att.student_name}) "
                        f"has no matching regular examination record"
                    ),
                    action_required="Verify student identity and associate with the correct record.",
                    related_attempts=[kt_att]
                ))
                summary.unmatched_kt_count += 1

    # Step 5: Check for ambiguous clearance pointers
    for key, group in student_groups.items():
        for att in group:
            if att.clearance_pointer and att.clearance_pointer.strip():
                # Validate: does the pointer reference a known student/session?
                pointer = att.clearance_pointer.strip()
                # Simple heuristic: if pointer doesn't match any known session
                # in this student's records, flag it
                known_sessions = {a.exam_session for a in group}
                pointer_valid = any(
                    sess.lower() in pointer.lower() for sess in known_sessions
                ) or len(group) > 1  # If multiple attempts exist, pointer is plausible
                if not pointer_valid:
                    all_exceptions.append(ReconciliationException(
                        student_identifier=att.student_identifier,
                        student_name=att.student_name,
                        exception_type=ExceptionType.AMBIGUOUS_POINTER,
                        description=(
                            f"Clearance pointer '{pointer}' in {att.exam_session} "
                            f"could not be validated against known records"
                        ),
                        action_required="Manually verify the clearance reference.",
                        related_attempts=[att]
                    ))

    # Step 6: Reconcile each student
    session_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"PASS": 0, "FAIL": 0})

    for key, group in student_groups.items():
        rec_result = reconcile_student(group)
        summary.results.append(rec_result)

        # Accumulate session counts
        for att in group:
            if att.attempt_status == AttemptStatus.PASS:
                session_counts[att.exam_session]["PASS"] += 1
            elif att.attempt_status == AttemptStatus.FAIL:
                session_counts[att.exam_session]["FAIL"] += 1

        # Accumulate summary counts
        cs = rec_result.clearance_status
        if cs == ClearanceStatus.PASSED_ORIGINAL:
            summary.pass_count += 1
        elif cs == ClearanceStatus.CLEARED_SUBSEQUENTLY:
            summary.cleared_count += 1
        elif cs == ClearanceStatus.UNCLEARED:
            summary.uncleared_count += 1
        elif cs == ClearanceStatus.PENDING:
            summary.pending_count += 1
        elif cs in (ClearanceStatus.NEEDS_REVIEW, ClearanceStatus.INSUFFICIENT_EVIDENCE):
            summary.needs_review_count += 1

    summary.total_students = len(student_groups)
    summary.fail_count = summary.uncleared_count + summary.pending_count
    summary.session_counts = dict(session_counts)
    summary.exceptions = all_exceptions

    return summary
