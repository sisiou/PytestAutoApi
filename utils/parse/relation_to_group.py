import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Set


def read_api_relation_file(relation_file_path: str) -> Dict:
    """
    读取接口关联关系文件
    :param relation_file_path: 关联关系文件路径
    :return: 解析后的关联关系数据
    """
    if not os.path.exists(relation_file_path):
        raise FileNotFoundError(f"关联关系文件不存在：{relation_file_path}")

    with open(relation_file_path, 'r', encoding='utf-8') as f:
        try:
            relation_data = json.load(f)
            return relation_data
        except json.JSONDecodeError as e:
            raise Exception(f"解析关联关系文件失败：{str(e)}")


def get_related_file_groups(relation_data: Dict) -> List[Set[str]]:
    """
    从关联关系数据中提取关联文件组
    每个组包含一组相互关联的文件，无关联的文件单独成组
    :param relation_data: 关联关系数据
    :return: 分组后的文件集合列表
    """
    # 初始化分组列表
    file_groups = []
    # 记录已处理的文件
    processed_files = set()

    # 处理有关联的文件对
    if 'related_pairs' in relation_data and relation_data['related_pairs']:
        for pair in relation_data['related_pairs']:
            # 获取源文件和目标文件
            source_file = pair.get('source_openapi_file')
            target_file = pair.get('target_openapi_file')

            if not source_file or not target_file:
                continue

            # 检查是否已存在于某个分组中
            source_group_idx = None
            target_group_idx = None

            # 查找源文件所在分组
            for idx, group in enumerate(file_groups):
                if source_file in group:
                    source_group_idx = idx
                    break

            # 查找目标文件所在分组
            for idx, group in enumerate(file_groups):
                if target_file in group:
                    target_group_idx = idx
                    break

            # 处理分组逻辑
            if source_group_idx is not None and target_group_idx is not None:
                # 两个文件都有分组且分组不同，合并分组
                if source_group_idx != target_group_idx:
                    # 合并目标分组到源分组
                    file_groups[source_group_idx].update(file_groups[target_group_idx])
                    # 删除目标分组
                    del file_groups[target_group_idx]
            elif source_group_idx is not None:
                # 只有源文件有分组，将目标文件加入
                file_groups[source_group_idx].add(target_file)
            elif target_group_idx is not None:
                # 只有目标文件有分组，将源文件加入
                file_groups[target_group_idx].add(source_file)
            else:
                # 都没有分组，创建新分组
                new_group = {source_file, target_file}
                file_groups.append(new_group)

            # 标记为已处理
            processed_files.add(source_file)
            processed_files.add(target_file)

    # 处理无关联的文件
    if 'unrelated_files' in relation_data and relation_data['unrelated_files']:
        for unrelated_file in relation_data['unrelated_files']:
            if unrelated_file not in processed_files:
                # 每个无关联文件单独成组
                file_groups.append({unrelated_file})
                processed_files.add(unrelated_file)

    return file_groups


def copy_related_files_to_groups(
        relation_file_path: str,
        source_dir: str,
        base_target_dir: str,
        overwrite: bool = True
) -> List[str]:
    """
    根据关联关系将文件复制到对应的分组目录
    :param relation_file_path: 关联关系文件路径
    :param source_dir: 源YAML文件所在目录
    :param base_target_dir: 基础目标目录（如/openApi/openapi_bailian_da093a41）
    :param overwrite: 是否覆盖已存在的文件
    :return: 生成的分组目录列表
    """
    # 读取关联关系数据
    relation_data = read_api_relation_file(relation_file_path)

    # 获取文件分组
    file_groups = get_related_file_groups(relation_data)
    if not file_groups:
        print("未找到任何关联文件分组")
        return []

    # 创建基础目标目录
    Path(base_target_dir).mkdir(parents=True, exist_ok=True)

    # 存储生成的目录路径
    created_dirs = []

    # 处理每个文件分组
    for group_idx, file_group in enumerate(file_groups):
        # 生成分组目录名
        group_dir_name = f"related_group_{group_idx + 1}"
        group_dir_path = os.path.join(base_target_dir, group_dir_name)

        # 创建分组目录
        Path(group_dir_path).mkdir(parents=True, exist_ok=True)
        created_dirs.append(group_dir_path)

        # 复制该组的所有文件
        for filename in file_group:
            # 源文件路径
            source_file_path = os.path.join(source_dir, filename)

            # 检查源文件是否存在
            if not os.path.exists(source_file_path):
                print(f"警告：源文件不存在，跳过复制 - {source_file_path}")
                continue

            # 目标文件路径
            target_file_path = os.path.join(group_dir_path, filename)

            # 复制文件
            if overwrite or not os.path.exists(target_file_path):
                shutil.copy2(source_file_path, target_file_path)
                print(f"已复制：{filename} -> {group_dir_path}")
            else:
                print(f"文件已存在，跳过复制 - {target_file_path}")

    print(f"\n处理完成！共创建 {len(created_dirs)} 个分组目录")
    for dir_path in created_dirs:
        print(f"- {dir_path}")

    return created_dirs


# 主函数示例
def main():
    # 配置参数
    relation_file_path = "api_relation.json"  # 关联关系文件路径
    source_dir = "/openApi/openapi_bailian_da093a41"  # 源YAML文件所在目录
    base_target_dir = "/openApi/openapi_bailian_da093a41"  # 基础目标目录

    try:
        # 执行分组复制
        created_dirs = copy_related_files_to_groups(
            relation_file_path=relation_file_path,
            source_dir=source_dir,
            base_target_dir=base_target_dir,
            overwrite=True
        )

    except Exception as e:
        print(f"处理失败：{str(e)}")


# Flask接口集成示例
def integrate_with_group_api(relation_file_path, source_dir, base_target_dir):
    """
    集成到Flask接口的函数
    """
    try:
        created_dirs = copy_related_files_to_groups(
            relation_file_path=relation_file_path,
            source_dir=source_dir,
            base_target_dir=base_target_dir
        )
        return {
            "success": True,
            "created_dirs": created_dirs,
            "group_count": len(created_dirs),
            "message": f"成功创建 {len(created_dirs)} 个关联文件分组目录"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "关联文件分组失败"
        }


if __name__ == "__main__":
    main()