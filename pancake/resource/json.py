from json import loads, dumps
import os
import logging

logger = logging.getLogger(__name__)


def json_init():
    from pancake.settings import get_path
    json_dir = get_path("json_dir")
    if not json_dir or not os.path.exists(json_dir):
        return {}
    data = {}
    for filename in os.listdir(json_dir):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(json_dir, filename)
        try:
            with open(filepath, 'r', encoding="utf-8") as f:
                data[filename.split('.')[0]] = loads(f.read())
        except Exception as e:
            logger.warning(f"加载 JSON 配置失败 {filename}: {e}")
    return data
