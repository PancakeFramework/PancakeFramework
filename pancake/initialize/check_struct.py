import os
import logging

logger = logging.getLogger(__name__)


def check_struct():
    from pancake.settings import get, get_path

    # 从集中配置读取路径，确保目录存在
    dir_keys = ["src_dir", "yaml_dir", "json_dir", "mapper_dir", "template_dir"]
    for key in dir_keys:
        d = get_path(key)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            logger.info(f"{d} 目录已创建")
