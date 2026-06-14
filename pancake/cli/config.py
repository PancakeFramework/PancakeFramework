"""配置管理命令：config show"""

import os
import xml.etree.ElementTree as ET

_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "apikey", "credential"}


def _mask_value(key: str, value) -> str:
    """对敏感配置值脱敏"""
    key_lower = key.lower()
    if any(s in key_lower for s in _SENSITIVE_KEYS):
        if isinstance(value, str) and len(value) > 4:
            return value[:2] + "***" + value[-2:]
        return "***"
    return str(value)


def _flatten_dict(d: dict, prefix: str, result: dict):
    """扁平化字典"""
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            _flatten_dict(v, f"{key}.", result)
        else:
            result[key] = v


def _get_paths_from_xml():
    """从 pancake.xml 读取路径配置"""
    from pancake.settings import _DEFAULTS
    defaults = {
        "yaml_dir": _DEFAULTS.get("paths.yaml_dir", "src/resource/yaml"),
        "json_dir": _DEFAULTS.get("paths.json_dir", "src/resource/json"),
    }
    xml_path = "pancake.xml"
    if not os.path.exists(xml_path):
        return defaults
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        config = root.find("config") or root.find("global")
        if config is not None:
            for prop in config.findall("property"):
                name = prop.get("name", "")
                value = prop.get("value", "")
                if name.startswith("paths.") and value:
                    defaults[name[6:]] = value
            for child in config:
                if child.tag.startswith("paths.") and child.text:
                    defaults[child.tag[6:]] = child.text.strip()
    except Exception:
        pass
    return defaults


def cmd_config_show(args):
    """显示当前配置"""
    paths = _get_paths_from_xml()
    yaml_dir = paths.get("yaml_dir")
    json_dir = paths.get("json_dir")

    configs = {}

    # 读取 YAML 配置
    if yaml_dir and os.path.isdir(yaml_dir):
        try:
            import yaml
            for fname in sorted(os.listdir(yaml_dir)):
                if not fname.endswith(('.yaml', '.yml')):
                    continue
                fpath = os.path.join(yaml_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    _flatten_dict(data, f"{fname}:", configs)
        except ImportError:
            print("警告: pyyaml 未安装，无法读取 YAML 配置")
        except Exception as e:
            print(f"警告: 读取 YAML 配置失败: {e}")

    # 读取 JSON 配置
    if json_dir and os.path.isdir(json_dir):
        try:
            import json
            for fname in sorted(os.listdir(json_dir)):
                if not fname.endswith('.json'):
                    continue
                fpath = os.path.join(json_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.loads(f.read())
                if data and isinstance(data, dict):
                    _flatten_dict(data, f"{fname}:", configs)
        except Exception as e:
            print(f"警告: 读取 JSON 配置失败: {e}")

    # 读取 XML 配置
    xml_path = "pancake.xml"
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            global_elem = tree.getroot().find("config") or tree.getroot().find("global")
            if global_elem is not None:
                for child in global_elem:
                    if child.tag == "property":
                        name = child.get("name", "")
                        value = child.get("value", "")
                        if name:
                            configs[f"xml:{name}"] = value
                    elif child.text and child.text.strip():
                        configs[f"xml:{child.tag}"] = child.text.strip()
        except Exception:
            pass

    if not configs:
        print("未找到配置")
        return

    print(f"{'配置项':<40} {'值'}")
    print("-" * 70)
    for key, value in sorted(configs.items()):
        masked = _mask_value(key, value)
        print(f"{key:<40} {masked}")
