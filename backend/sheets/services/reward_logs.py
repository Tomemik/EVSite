"""Match references shared by historical reward-log consumers."""

import re


def get_log_match_id(log):
    value = log.new_value.get('match_id')
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    match = re.search(r'^Match ID: (\d+)\s*$', log.description, re.MULTILINE)
    return int(match.group(1)) if match else None
