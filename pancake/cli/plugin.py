"""插件管理命令：plugin list/add/remove/clear

插件格式与 pancake.xml 的 <dependencies> 一致：
  <dependency>
    <groupId>io.pancake</groupId>
    <artifactId>mybatis</artifactId>
  </dependency>
"""

import os
import sys
import xml.etree.ElementTree as ET


def _get_xml_path():
    """获取 pancake.xml 路径"""
    return os.path.join(os.getcwd(), "pancake.xml")


def _parse_xml(xml_path):
    """解析 XML，返回 (tree, root)"""
    try:
        tree = ET.parse(xml_path)
        return tree, tree.getroot()
    except ET.ParseError as e:
        print(f"错误: XML 解析失败: {e}")
        sys.exit(1)


def _get_dependencies(root):
    """从 XML 根节点获取所有 dependency 元素"""
    deps_elem = root.find("dependencies")
    if deps_elem is None:
        return []
    return deps_elem.findall("dependency")


def _get_disabled_plugins(root):
    """获取禁用的插件列表"""
    disabled = set()
    for dep in _get_dependencies(root):
        enabled = dep.findtext("enabled", "true").lower()
        artifact = dep.findtext("artifactId", "")
        if artifact and enabled == "false":
            disabled.add(artifact)
    return disabled


def _find_or_create_deps_elem(root):
    """找到或创建 <dependencies> 节点"""
    deps_elem = root.find("dependencies")
    if deps_elem is None:
        deps_elem = ET.SubElement(root, "dependencies")
    return deps_elem


def _save_xml(tree, xml_path):
    """格式化并写回 XML"""
    ET.indent(tree, space="    ")
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)


def cmd_plugin_list(args):
    """列出 pancake.xml 中配置的插件"""
    xml_path = _get_xml_path()
    if not os.path.exists(xml_path):
        print("错误: 当前目录没有 pancake.xml")
        sys.exit(1)

    tree, root = _parse_xml(xml_path)
    disabled = _get_disabled_plugins(root)
    deps = _get_dependencies(root)

    if not deps:
        print("pancake.xml 中没有配置插件")
        return

    print(f"{'插件名':<25} {'groupId':<20} {'状态':<10}")
    print("-" * 58)
    for dep in deps:
        group_id = dep.findtext("groupId", "io.pancake")
        artifact_id = dep.findtext("artifactId", "")
        if not artifact_id:
            continue
        status = "disabled" if artifact_id in disabled else "enabled"
        print(f"{artifact_id:<25} {group_id:<20} {status:<10}")


def cmd_plugin_add(args):
    """添加插件到 pancake.xml 的 <dependencies>"""
    name = args.name
    xml_path = _get_xml_path()

    if not os.path.exists(xml_path):
        print("错误: 当前目录没有 pancake.xml")
        sys.exit(1)

    tree, root = _parse_xml(xml_path)

    # 检查是否已存在
    for dep in _get_dependencies(root):
        if dep.findtext("artifactId") == name:
            print(f"插件 '{name}' 已存在于 pancake.xml")
            return

    # 添加到 <dependencies>
    deps_elem = _find_or_create_deps_elem(root)
    dep_elem = ET.SubElement(deps_elem, "dependency")
    ET.SubElement(dep_elem, "groupId").text = "io.pancake"
    ET.SubElement(dep_elem, "artifactId").text = name

    _save_xml(tree, xml_path)
    print(f"已添加插件 '{name}' 到 pancake.xml")


def cmd_plugin_remove(args):
    """从 pancake.xml 移除指定插件"""
    name = args.name
    xml_path = _get_xml_path()

    if not os.path.exists(xml_path):
        print("错误: 当前目录没有 pancake.xml")
        sys.exit(1)

    tree, root = _parse_xml(xml_path)
    found = False

    deps_elem = root.find("dependencies")
    if deps_elem is not None:
        for dep in deps_elem.findall("dependency"):
            if dep.findtext("artifactId") == name:
                deps_elem.remove(dep)
                found = True
                break
        if len(deps_elem) == 0:
            root.remove(deps_elem)

    if not found:
        print(f"插件 '{name}' 不存在于 pancake.xml")
        return

    _save_xml(tree, xml_path)
    print(f"已从 pancake.xml 移除插件 '{name}'")


def cmd_plugin_clear(args):
    """清空 pancake.xml 中的所有插件"""
    xml_path = _get_xml_path()

    if not os.path.exists(xml_path):
        print("错误: 当前目录没有 pancake.xml")
        sys.exit(1)

    tree, root = _parse_xml(xml_path)

    deps_elem = root.find("dependencies")
    if deps_elem is None:
        print("pancake.xml 中没有插件")
        return

    count = len(deps_elem.findall("dependency"))
    if count == 0:
        print("pancake.xml 中没有插件")
        return

    root.remove(deps_elem)
    _save_xml(tree, xml_path)
    print(f"已清空所有插件 ({count} 个)")
