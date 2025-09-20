from __future__ import annotations

from ruamel.yaml import YAML

# strict YAML loader (reject duplicate keys everywhere)
yaml_loader = YAML(typ="safe")
yaml_loader.allow_duplicate_keys = False

# YAML dumper for output
yaml_dumper = YAML()
yaml_dumper.default_flow_style = False
yaml_dumper.width = 256


def _repr_str(dumper, data: str):
    # Use literal block style (|) for any multi-line strings in output
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml_dumper.representer.add_representer(str, _repr_str)
