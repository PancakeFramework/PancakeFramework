#!/bin/bash
# 本地测试 publish workflow 逻辑

set -e

echo "=== 测试 Publish Workflow 逻辑 ==="
echo ""

# 1. 测试版本读取
echo "1. 测试版本读取"
MAIN_VERSION=$(poetry version --short 2>/dev/null || echo "0.2.0")
echo "   主框架版本: $MAIN_VERSION"
echo ""

# 2. 测试版本 tag 检查
echo "2. 测试版本 tag 检查"
TAG_NAME="v${MAIN_VERSION}"
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "   ⚠️ 版本 $TAG_NAME 已存在，跳过发布"
    PUBLISH_MAIN=false
else
    echo "   ✅ 版本 $TAG_NAME 可以发布"
    PUBLISH_MAIN=true
fi
echo ""

# 3. 测试插件检测
echo "3. 测试插件版本检测"
PLUGINS=""
for plugin_dir in pancake-*/; do
    plugin_name=$(basename "$plugin_dir")
    if [ -f "$plugin_dir/pyproject.toml" ]; then
        # 读取插件版本
        VERSION=$(cd "$plugin_dir" && grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
        if [ -n "$VERSION" ]; then
            # 检查版本 tag 是否存在
            PLUGIN_TAG="${plugin_name}-v${VERSION}"
            if ! git rev-parse "$PLUGIN_TAG" >/dev/null 2>&1; then
                echo "   ✅ $plugin_name 版本 $VERSION 需要发布"
                PLUGINS="${PLUGINS}${plugin_name}:${VERSION},"
            else
                echo "   ⏭️ $plugin_name 版本 $VERSION 已存在，跳过"
            fi
        fi
    else
        echo "   ⚠️ $plugin_name 缺少 pyproject.toml，跳过"
    fi
done
# 移除末尾逗号
PLUGINS=${PLUGINS%,}
echo ""

# 4. 汇总结果
echo "=== 汇总 ==="
echo "主框架发布: $PUBLISH_MAIN"
echo "待发布插件: ${PLUGINS:-无}"
echo ""

# 5. 模拟构建（不实际发布）
if [ "$PUBLISH_MAIN" = "true" ]; then
    echo "5. 模拟构建主框架"
    echo "   poetry build"
    echo "   poetry publish"
    echo "   git tag -a $TAG_NAME -m 'Release $TAG_NAME'"
    echo "   git push origin $TAG_NAME"
fi

if [ -n "$PLUGINS" ]; then
    echo ""
    echo "6. 模拟发布插件"
    IFS=',' read -ra PLUGIN_LIST <<< "$PLUGINS"
    for plugin_info in "${PLUGIN_LIST[@]}"; do
        IFS=':' read -r plugin_name version <<< "$plugin_info"
        echo "   📦 $plugin_name v$version"
        echo "      cd $plugin_name && poetry build && poetry publish"
        echo "      git tag -a ${plugin_name}-v${version} -m 'Release ${plugin_name} v${version}'"
    done
fi

echo ""
echo "=== 测试完成 ==="
