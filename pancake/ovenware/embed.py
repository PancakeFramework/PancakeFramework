"""
    # 嵌入 插件
    提供嵌入功能，将所有依赖项和装饰器加载到全局命名空间中
"""
logger = logging.getLogger(__name__)

class Main(InitAction):

    init_order = 999

    def __init__(self):
        self.build()

    def build(self):
        __builtins__["oven"] = oven
        plugin_count = 0

        for classes in oven.pancake_pie.keys():
            for module in oven.pancake_pie[classes].keys():
                __builtins__[classes+"_"+module] = oven.pancake_pie[classes][module]
                plugin_count += 1

        for flour in oven.muffin_flour.keys():
            __builtins__[flour] = oven.muffin_flour[flour]
            plugin_count += 1

        for water in oven.muffin_water.keys():
            __builtins__[water] = oven.muffin_water[water]
            plugin_count += 1

        for egg in oven.muffin_egg.keys():
            __builtins__[egg] = oven.muffin_egg[egg]
            plugin_count += 1

        for yml in oven.pancake_yaml.keys():
            __builtins__[yml.replace(".", "_")] = oven.pancake_yaml[yml]
            plugin_count += 1

        for json in oven.pancake_json.keys():
            __builtins__[json] = oven.pancake_json[json]
            plugin_count += 1

        for sugar in oven.muffin_sugar.keys():
            __builtins__[sugar] = oven.muffin_sugar[sugar]
            plugin_count += 1

        # XML 配置
        __builtins__["pancake_xml"] = oven.pancake_xml
        plugin_count += 1

        logger.info(f"嵌入 {plugin_count} 个插件")