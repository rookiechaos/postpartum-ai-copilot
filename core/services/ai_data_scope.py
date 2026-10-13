"""Select only explicitly requested personal context before external AI calls."""

PROFILE_FIELDS = {"babyAge", "baby_age_days", "birthType", "birth_type", "feedingType", "feeding_type", "sleep_hours_avg"}
CARE_TYPES = {"feeding", "diaper", "sleep", "pumping"}
PARENT_TYPES = {"mood", "recovery"}
CARE_FIELDS = {"entry_type", "timestamp", "feeding_type", "duration_minutes", "amount_ml", "side", "diaper_type",
               "sleep_duration_minutes", "sleep_quality", "pumped_amount_ml"}
PARENT_FIELDS = {"mood_level", "weight_kg", "breast_condition"}


def previous_exchange_for_ai(value, include_previous=False):
    """Exactly one explicitly selected question/answer pair; never client-supplied roles."""
    if include_previous is not True:
        return None
    from exceptions import ValidationError
    if not isinstance(value, dict) or set(value) != {"previous_question", "previous_answer"}:
        raise ValidationError("Choose a previous question and answer before continuing")
    for key, limit in (("previous_question", 2000), ("previous_answer", 4000)):
        if not isinstance(value[key], str) or not 1 <= len(value[key]) <= limit:
            raise ValidationError("Previous exchange exceeds the allowed length")
    return {key: value[key] for key in ("previous_question", "previous_answer")}


def profile_for_ai(context, include_profile=False):
    if include_profile is not True:
        return {}
    return {key: value for key, value in context.items() if key in PROFILE_FIELDS and value is not None}


def records_for_ai(entries, include_parent=False, include_notes=False):
    allowed_types = CARE_TYPES | (PARENT_TYPES if include_parent is True else set())
    selected = []
    for entry in entries:
        kind = entry.get("entry_type")
        if kind not in allowed_types:
            continue
        allowed_fields = set(CARE_FIELDS) if kind in CARE_TYPES else PARENT_FIELDS | {"entry_type", "timestamp"}
        if include_notes is True:
            allowed_fields |= {"notes"}
            if kind == "mood":
                allowed_fields |= {"mood_notes"}
            elif kind == "recovery":
                allowed_fields |= {"recovery_notes"}
        selected.append({key: value for key, value in entry.items() if key in allowed_fields})
    return selected
