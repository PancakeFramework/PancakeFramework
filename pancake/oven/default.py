from pancake.tool import ProgressBar

def pancake_default_before():
    from pancake import oven
    oven.pancake_dough.update({
        "Service": {},
        "Mapper": {}
    })
    oven.pancake_pie.update({
        "Service": {},
        "Method": {},
        "Mapper": {}
    })
    oven.pancake_other.update({
        "path": {},
        "System": {}
    })

    # 配置加载已移至 ConfigFactory（run.py load_config）
    # 保留向后兼容：如果 ConfigFactory 未初始化，回退到旧方式
    if not oven.pancake_yaml:
        from pancake.resource import json, yml
        oven.pancake_json.update(json.json_init())
        oven.pancake_yaml.update(yml.yaml_init())
        oven.pancake_yaml.setdefault("framework.disable_dlc", [])

        xml_config = oven.pancake_xml.get("config", {})
        if xml_config:
            oven.pancake_yaml.update(xml_config)

        for plugin in oven.pancake_xml.get("plugins", []):
            plugin_config = plugin.get("config", {})
            if plugin_config:
                oven.pancake_yaml.update(plugin_config)

def muffin_default_before():
    from pancake import oven
    oven.muffin_egg.update({
        "Builder": {},
        "LoopMethod": {},
        "VerifyMethod": {},
        "InitOrder": [],
        "BuildOrder": []
    })

default_before_methods = [
    pancake_default_before,
    muffin_default_before,
]

default_after_methods = [

]

def default_before():
    """默认初始化"""
    progress_bar = ProgressBar(len(default_before_methods), "Pancake Default Before")
    for method in default_before_methods:
        method()
        progress_bar.update(1, f"{method.__name__} 完成")

def default_after():
    """默认后处理"""
    progress_bar = ProgressBar(len(default_after_methods), "Pancake Default After")
    for method in default_after_methods:
        method()
        progress_bar.update(1, f"{method.__name__} 完成")
