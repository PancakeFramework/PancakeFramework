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


def cmd_config_show(args):
    """显示当前配置"""
    yaml_dir = os.path.join("src", "resource", "yaml")
    if not os.path.isdir(yaml_dir):
        print(f"警告: {yaml_dir} 目录不存在")
        yaml_dir = None

    configs = {}

    if yaml_dir:
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
            print(f"警告: 读取配置失败: {e}")

    xml_path = "pancake.xml"
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            global_elem = tree.getroot().find("config") or tree.getroot().find("global")
            if global_elem is not None:
                for child in global_elem:
                    if child.tag != "property" and child.text and child.text.strip():
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
