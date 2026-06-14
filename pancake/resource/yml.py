import yaml, os, re
import logging


logger = logging.getLogger(__name__)

def yaml_init():
    from pancake.settings import get_path
    yaml_file_dir = get_path("yaml_dir")
    data = {}
    if not yaml_file_dir or not os.path.exists(yaml_file_dir):
        return data
    for yaml_file in os.listdir(yaml_file_dir):
        if yaml_file.endswith('.yml') or yaml_file.endswith('.yaml'):
            with open(f'{yaml_file_dir}/{yaml_file}', 'r',encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded is not None:
                    data.update(loaded)

    pattern = re.compile(r'\$\{([a-zA-Z0-9_.]+)}')

    # 递归解析占位符
    def resolve(obj, resolving=None):
        if resolving is None:
            resolving = set()
        if isinstance(obj, dict):
            return {k: resolve(v, resolving) for k, v in obj.items()}
        if isinstance(obj, list):
            return [resolve(i, resolving) for i in obj]
        if isinstance(obj, str):
            for _ in range(10):  # max iterations to prevent infinite loop
                match = pattern.search(obj)
                if not match:
                    break
                key_path = match.group(1)
                if key_path in resolving:
                    logger.warning(f"Circular reference detected: {key_path}")
                    break
                resolving.add(key_path)
                keys = key_path.split('.')
                value = data
                try:
                    for k in keys:
                        value = value[k]
                except (KeyError, TypeError):
                    value = match.group(0)
                obj = obj.replace(match.group(0), str(value))
                resolving.discard(key_path)
            return obj
        return obj
    data = resolve(data)

    # 将嵌套字典转换为扁平字典
    def flatten(obj, parent_key='', sep='.'):
        items = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f'{parent_key}{sep}{k}' if parent_key else k
                items.extend(flatten(v, new_key, sep).items())
        else:
            items.append((parent_key, obj))

        return dict(items)
    data = flatten(data)
    return data