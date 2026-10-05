import json_repair

s = '{"a": "b", "c": [{"d": "e"}'
print(json_repair.loads(s))
