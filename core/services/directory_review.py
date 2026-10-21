"""Shared comparison of staff-reviewed public contact content."""

from hashlib import sha256
import json


def resource_digest(resource):
    return sha256(json.dumps(resource, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
