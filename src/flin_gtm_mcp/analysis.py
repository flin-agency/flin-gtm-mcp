"""Deterministic structural findings; no claim of runtime or legal correctness."""

import re

from .client import GTMError
from .snapshots import ENTITY_IDS


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def dependencies(data):
    tags, triggers, variables = (data.get(k, []) for k in ("tag", "trigger", "variable"))
    trigger_ids = {str(t["triggerId"]) for t in triggers}
    tag_names = {t.get("name") for t in tags}
    # GTM's system triggers are not necessarily present in the snapshot's trigger array.
    system_triggers = {"2147479553", "2147479572", "2147479573"}
    used_triggers, sequenced, missing = set(), set(), []
    for tag in tags:
        for field in ("firingTriggerId", "blockingTriggerId"):
            for tid in tag.get(field, []):
                used_triggers.add(str(tid))
                if str(tid) not in trigger_ids | system_triggers:
                    missing.append({"tagId": tag.get("tagId"), "field": field, "triggerId": tid})
        for field in ("setupTag", "teardownTag"):
            for ref in tag.get(field, []):
                name = ref.get("tagName")
                sequenced.add(name)
                if name not in tag_names:
                    missing.append({"tagId": tag.get("tagId"), "field": field, "tagName": name})
    # Trigger groups reference member IDs inside parameters.
    for trigger in triggers:
        if trigger.get("type") == "triggerGroup":
            used_triggers.update(s for s in strings(trigger.get("parameter", []))
                                 if s in trigger_ids)
    refs = set()
    for kind in ENTITY_IDS:
        for entity in data.get(kind, []):
            # Display metadata is not an executable variable reference.
            payload = {k: v for k, v in entity.items()
                       if k not in ("name", "notes", "fingerprint", "path", "tagManagerUrl")}
            refs.update(name for s in strings(payload) for name in re.findall(r"\{\{([^{}]+)\}\}", s))
    return {
        "tags_without_firing_or_sequence_reference": [t.get("tagId") for t in tags
            if not t.get("firingTriggerId") and t.get("name") not in sequenced],
        "unreferenced_trigger_candidates": sorted(trigger_ids - used_triggers),
        "unreferenced_variable_candidates": [v.get("variableId") for v in variables
                                              if v.get("name") not in refs],
        "missing_references": missing,
        "limitations": "Static candidates only, not deletion advice. Dynamic code references, "
        "template behaviour, cycles and runtime firing/consent require manual or browser checks.",
    }


def changed_fields(left, right, prefix=""):
    result = []
    for key in sorted(left.keys() | right.keys()):
        if key in ("fingerprint", "path", "tagManagerUrl", "containerVersionId", "workspaceId"):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if key not in left or key not in right:
            result.append(path)
        elif isinstance(left[key], dict) and isinstance(right[key], dict):
            result.extend(changed_fields(left[key], right[key], path))
        elif left[key] != right[key]:
            result.append(path)
    return result


def diff_versions(left, right):
    for key in ("accountId", "containerId"):
        if not left.get(key) or left.get(key) != right.get(key):
            raise GTMError("Compare snapshots from the same account and container.")
    changes = []
    for kind, id_key in ENTITY_IDS.items():
        before = {str(e[id_key]): e for e in left.get(kind, [])}
        after = {str(e[id_key]): e for e in right.get(kind, [])}
        for entity_id in sorted(before.keys() | after.keys()):
            if entity_id not in before:
                changes.append({"kind": kind, "id": entity_id, "change": "added"})
            elif entity_id not in after:
                changes.append({"kind": kind, "id": entity_id, "change": "removed"})
            else:
                fields = changed_fields(before[entity_id], after[entity_id])
                if fields:
                    changes.append({"kind": kind, "id": entity_id, "change": "modified",
                                    "fields": fields})
    return changes
