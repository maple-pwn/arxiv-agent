#!/usr/bin/env python3
"""
配置文件迁移和合并工具

功能：
1. 智能合并 config.yaml.template 和现有 config.yaml
2. 保留用户自定义的配置值
3. 添加模板中新增的配置项
4. 自动备份现有配置
5. 生成详细的变更报告
"""

import os
import sys
import yaml
import shutil
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import OrderedDict


class ConfigMigration:
    """配置迁移工具"""

    def __init__(self, template_path: str = "config.yaml.template",
                 config_path: str = "config.yaml"):
        """
        初始化配置迁移工具

        Args:
            template_path: 模板文件路径
            config_path: 配置文件路径
        """
        self.template_path = template_path
        self.config_path = config_path
        self.backup_path = None
        self.changes = []

    def backup_config(self) -> str:
        """
        备份现有配置文件

        Returns:
            备份文件路径
        """
        if not os.path.exists(self.config_path):
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.config_path}.backup_{timestamp}"

        shutil.copy2(self.config_path, backup_path)
        self.backup_path = backup_path
        print(f"✅ 已备份现有配置: {backup_path}")

        return backup_path

    def load_yaml(self, filepath: str) -> Dict[str, Any]:
        """
        加载 YAML 文件

        Args:
            filepath: 文件路径

        Returns:
            配置字典
        """
        if not os.path.exists(filepath):
            return {}

        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                print(f"❌ YAML 解析错误 ({filepath}): {e}")
                return {}

    def merge_configs(self, template: Dict[str, Any],
                     existing: Dict[str, Any],
                     path: str = "") -> Dict[str, Any]:
        """
        递归合并配置

        保留用户自定义的值，添加模板中新增的配置项

        Args:
            template: 模板配置
            existing: 现有配置
            path: 当前配置路径（用于日志）

        Returns:
            合并后的配置
        """
        merged = {}

        # 1. 遍历模板中的所有键
        for key, template_value in template.items():
            current_path = f"{path}.{key}" if path else key

            if key in existing:
                existing_value = existing[key]

                # 如果两者都是字典，递归合并
                if isinstance(template_value, dict) and isinstance(existing_value, dict):
                    merged[key] = self.merge_configs(template_value, existing_value, current_path)

                # 如果类型不同，或者是基本类型，保留用户配置
                else:
                    # 检查用户是否修改了默认值
                    if self._is_user_modified(template_value, existing_value):
                        merged[key] = existing_value
                        self.changes.append(f"  ✓ 保留用户配置: {current_path} = {existing_value}")
                    else:
                        # 用户未修改，使用模板值（可能是更新后的默认值）
                        merged[key] = template_value
            else:
                # 模板中的新配置项
                merged[key] = template_value
                self.changes.append(f"  + 新增配置项: {current_path} = {template_value}")

        # 2. 保留用户在现有配置中添加的自定义配置项（模板中不存在的）
        for key, existing_value in existing.items():
            if key not in template:
                current_path = f"{path}.{key}" if path else key
                merged[key] = existing_value
                self.changes.append(f"  ★ 保留自定义配置: {current_path}")

        return merged

    def _is_user_modified(self, template_value: Any, existing_value: Any) -> bool:
        """
        判断用户是否修改了配置值

        Args:
            template_value: 模板值
            existing_value: 现有值

        Returns:
            是否修改
        """
        # 如果值不同，认为是用户修改的
        if template_value != existing_value:
            # 排除一些特殊情况（如模板占位符）
            if isinstance(template_value, str) and isinstance(existing_value, str):
                # 如果模板是占位符，且用户填写了真实值，认为是修改
                placeholders = ['your-api-key', 'your-email', 'your-app-password',
                               'your-api-key-here', 'recipient@example.com']
                if any(ph in template_value for ph in placeholders):
                    return True

            return True

        return False

    def write_config(self, config: Dict[str, Any], output_path: str):
        """
        写入配置文件

        Args:
            config: 配置字典
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f,
                     default_flow_style=False,
                     allow_unicode=True,
                     sort_keys=False,
                     indent=2)

    def migrate(self, dry_run: bool = False) -> Tuple[bool, str]:
        """
        执行配置迁移

        Args:
            dry_run: 是否为演练模式（不实际写入文件）

        Returns:
            (是否成功, 消息)
        """
        print("=" * 60)
        print("配置文件迁移工具")
        print("=" * 60)

        # 1. 检查模板文件
        if not os.path.exists(self.template_path):
            return False, f"❌ 模板文件不存在: {self.template_path}"

        print(f"📄 模板文件: {self.template_path}")

        # 2. 检查现有配置
        if not os.path.exists(self.config_path):
            print(f"ℹ️  配置文件不存在，将从模板创建: {self.config_path}")

            if not dry_run:
                shutil.copy2(self.template_path, self.config_path)
                print(f"✅ 已创建配置文件: {self.config_path}")

            return True, "配置文件已创建"

        print(f"📄 现有配置: {self.config_path}")

        # 3. 备份现有配置
        if not dry_run:
            self.backup_config()

        # 4. 加载配置
        print("\n⏳ 正在加载配置文件...")
        template_config = self.load_yaml(self.template_path)
        existing_config = self.load_yaml(self.config_path)

        if not template_config:
            return False, "❌ 无法加载模板配置"

        if not existing_config:
            return False, "❌ 无法加载现有配置"

        # 5. 合并配置
        print("⏳ 正在合并配置...")
        self.changes = []
        merged_config = self.merge_configs(template_config, existing_config)

        # 6. 显示变更摘要
        print("\n" + "=" * 60)
        print("变更摘要")
        print("=" * 60)

        if not self.changes:
            print("✅ 无需更新，配置文件已是最新")
            return True, "配置文件无需更新"

        # 统计变更类型
        new_items = [c for c in self.changes if '+ 新增配置项' in c]
        kept_items = [c for c in self.changes if '✓ 保留用户配置' in c]
        custom_items = [c for c in self.changes if '★ 保留自定义配置' in c]

        print(f"📊 变更统计:")
        print(f"  - 新增配置项: {len(new_items)}")
        print(f"  - 保留用户配置: {len(kept_items)}")
        print(f"  - 保留自定义配置: {len(custom_items)}")
        print(f"  - 总计: {len(self.changes)}")

        print("\n📋 详细变更:")
        for change in self.changes[:20]:  # 只显示前20条
            print(change)

        if len(self.changes) > 20:
            print(f"  ... 还有 {len(self.changes) - 20} 条变更")

        # 7. 写入合并后的配置
        if dry_run:
            print("\n⚠️  演练模式：未实际写入文件")
            return True, "演练完成（未写入文件）"

        try:
            self.write_config(merged_config, self.config_path)
            print(f"\n✅ 配置文件已更新: {self.config_path}")

            if self.backup_path:
                print(f"📦 备份文件: {self.backup_path}")

            return True, "配置迁移成功"

        except Exception as e:
            return False, f"❌ 写入配置失败: {str(e)}"

    def validate_config(self, config_path: str = None) -> Tuple[bool, List[str]]:
        """
        验证配置文件完整性

        检查是否缺少必要的配置项

        Args:
            config_path: 配置文件路径（默认使用 self.config_path）

        Returns:
            (是否有效, 错误/警告列表)
        """
        if config_path is None:
            config_path = self.config_path

        issues = []

        # 加载配置
        config = self.load_yaml(config_path)
        template = self.load_yaml(self.template_path)

        if not config:
            return False, ["配置文件为空或无法解析"]

        # 检查必要配置项
        required_keys = [
            ('arxiv', 'keywords'),
            ('ai', 'enabled'),
            ('ai', 'provider'),
        ]

        for keys in required_keys:
            current = config
            path = ""
            missing = False

            for key in keys:
                path = f"{path}.{key}" if path else key
                if key not in current:
                    issues.append(f"❌ 缺少必要配置: {path}")
                    missing = True
                    break
                current = current[key]
                if current is None:
                    issues.append(f"⚠️  配置项为空: {path}")
                    break

        # 检查 API key 是否为占位符
        if config.get('ai', {}).get('enabled', False):
            provider = config.get('ai', {}).get('provider', 'openai')
            api_key = config.get('ai', {}).get(provider, {}).get('api_key', '')

            if 'your-api-key' in api_key or not api_key:
                issues.append(f"⚠️  请配置 AI API Key: ai.{provider}.api_key")

        # 检查邮件配置
        if config.get('notification', {}).get('enabled', False):
            if config.get('notification', {}).get('method') == 'email':
                email_config = config.get('notification', {}).get('email', {})

                if 'your-email' in email_config.get('sender', ''):
                    issues.append("⚠️  请配置发件人邮箱: notification.email.sender")

                if 'your-app-password' in email_config.get('password', ''):
                    issues.append("⚠️  请配置邮箱密码: notification.email.password")

        if not issues:
            return True, ["✅ 配置文件验证通过"]

        return False, issues


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='配置文件迁移和合并工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看会进行哪些变更（不实际修改文件）
  python config_migration.py --dry-run

  # 执行配置迁移
  python config_migration.py

  # 验证配置文件
  python config_migration.py --validate

  # 指定自定义路径
  python config_migration.py --template custom.yaml --config my_config.yaml
        """
    )

    parser.add_argument(
        '--template',
        default='config.yaml.template',
        help='模板文件路径（默认: config.yaml.template）'
    )

    parser.add_argument(
        '--config',
        default='config.yaml',
        help='配置文件路径（默认: config.yaml）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='演练模式（不实际写入文件）'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='验证配置文件完整性'
    )

    args = parser.parse_args()

    # 创建迁移工具实例
    migration = ConfigMigration(args.template, args.config)

    # 验证模式
    if args.validate:
        print("=" * 60)
        print("配置文件验证")
        print("=" * 60)

        valid, issues = migration.validate_config()

        for issue in issues:
            print(issue)

        if valid:
            print("\n✅ 配置验证通过")
            sys.exit(0)
        else:
            print("\n⚠️  配置存在问题，请检查")
            sys.exit(1)

    # 迁移模式
    success, message = migration.migrate(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    if success:
        print(f"✅ {message}")
        sys.exit(0)
    else:
        print(f"❌ {message}")
        sys.exit(1)


if __name__ == '__main__':
    main()