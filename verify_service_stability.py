"""
验证服务层和 Blueprint 稳定性检查工具

使用方法:
    python verify_service_stability.py

或在生产环境中添加到健康检查:
    curl https://your-domain.com/api/health-check-detail
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_service_layer():
    """检查服务层是否可用"""
    results = {
        'available': False,
        'modules': {},
        'errors': []
    }
    
    # 检查各个服务模块
    service_modules = [
        ('backend.services.path_planning_service', [
            'calculate_direction',
            'is_direction_allowed',
            'get_node_by_id',
            'get_edge_length_m',
            'get_vehicle_speed_kmph',
            'get_edges_connected_to_node',
            'refresh_edge_geometry',
            'build_graph',
            'calculate_efficient_path',
            'estimate_efficiency_score',
        ]),
        ('backend.services.system_service', [
            'init_monitor_data',
            'initialize_system',
            'apply_node_congestion_to_edges',
            'current_vehicle_location_node',
            'reroute_vehicles',
            'update_monitor_data',
        ]),
        ('backend.services.vehicle_service', [
            'update_vehicle_positions',
        ]),
        ('backend.services.dqn_service', [
            'ensure_dqn_planner',
            'RoadEnvironment',
            'DeepQLearningPlanner',
        ]),
        ('backend.services.map_import_service', [
            'parse_dxf_file',
        ]),
        ('backend.services.travel_time_service', [
            'parse_travel_time_excel',
            'build_travel_time_excel',
            'normalize_travel_time_records',
            'calculate_average_speed_kmph',
        ]),
    ]
    
    all_available = True
    for module_name, functions in service_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            module_results = {}
            for func_name in functions:
                try:
                    func = getattr(module, func_name)
                    module_results[func_name] = {
                        'available': True,
                        'type': type(func).__name__
                    }
                except AttributeError as e:
                    module_results[func_name] = {
                        'available': False,
                        'error': f'未找到: {str(e)}'
                    }
                    all_available = False
            results['modules'][module_name] = module_results
        except ImportError as e:
            results['modules'][module_name] = {
                'available': False,
                'error': f'模块导入失败: {str(e)}'
            }
            results['errors'].append(f'{module_name}: {str(e)}')
            all_available = False
    
    results['available'] = all_available
    return results


def check_blueprints():
    """检查 Blueprint 是否可用"""
    results = {
        'available': False,
        'blueprints': {},
        'errors': []
    }
    
    blueprint_modules = [
        'backend.blueprints.health',
        'backend.blueprints.vehicles',
        'backend.blueprints.drivers',
        'backend.blueprints.nodes',
        'backend.blueprints.edges',
        'backend.blueprints.monitor',
        'backend.blueprints.dispatch',
        'backend.blueprints.dqn',
        'backend.blueprints.travel_time',
        'backend.blueprints.map_import',
        'backend.blueprints.system',
        'backend.blueprints.map_labels',
    ]
    
    all_available = True
    for blueprint_name in blueprint_modules:
        try:
            module = __import__(blueprint_name, fromlist=[''])
            # 检查是否有 bp 属性（Blueprint 对象）
            if hasattr(module, 'bp'):
                bp = module.bp
                results['blueprints'][blueprint_name] = {
                    'available': True,
                    'name': bp.name,
                    'url_prefix': getattr(bp, 'url_prefix', None),
                    'routes': [str(rule) for rule in bp.deferred_functions if hasattr(rule, 'url_rule')]
                }
            else:
                results['blueprints'][blueprint_name] = {
                    'available': False,
                    'error': '未找到 bp 属性'
                }
                all_available = False
        except ImportError as e:
            results['blueprints'][blueprint_name] = {
                'available': False,
                'error': f'导入失败: {str(e)}'
            }
            results['errors'].append(f'{blueprint_name}: {str(e)}')
            all_available = False
    
    results['available'] = all_available
    return results


def test_service_functions():
    """测试服务层函数是否能正常工作"""
    results = {
        'passed': [],
        'failed': [],
        'skipped': []
    }
    
    try:
        from backend.services.path_planning_service import get_node_by_id
        from backend.models.system_state import system_state
        
        # 测试 get_node_by_id
        with system_state.lock:
            nodes = system_state.get('nodes', [])
            if nodes:
                test_node = get_node_by_id(nodes[0]['id'])
                if test_node:
                    results['passed'].append('get_node_by_id: 能够获取节点')
                else:
                    results['failed'].append('get_node_by_id: 返回 None')
            else:
                results['skipped'].append('get_node_by_id: 没有节点数据，跳过测试')
    except Exception as e:
        results['failed'].append(f'get_node_by_id: {str(e)}')
    
    try:
        from backend.services.path_planning_service import calculate_direction
        # 测试 calculate_direction
        test_start = {'x': 0, 'y': 0}
        test_end = {'x': 100, 'y': 0}
        direction = calculate_direction(test_start, test_end)
        if direction:
            results['passed'].append(f'calculate_direction: 返回 {direction}')
        else:
            results['failed'].append('calculate_direction: 返回 None')
    except Exception as e:
        results['failed'].append(f'calculate_direction: {str(e)}')
    
    return results


def check_app_startup_flags():
    """检查 app.py 中的启动标志"""
    results = {
        'service_layer_available': False,
        'blueprints_available': False,
        'app_file_path': None
    }
    
    app_file = os.path.join(os.path.dirname(__file__), 'app.py')
    if os.path.exists(app_file):
        results['app_file_path'] = app_file
        try:
            # 读取 app.py 文件内容
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有服务层导入成功
            if '_SERVICE_LAYER_AVAILABLE = True' in content:
                results['service_layer_available'] = True
            elif '_SERVICE_LAYER_AVAILABLE = False' in content:
                results['service_layer_available'] = False
                results['warning'] = '代码中有 _SERVICE_LAYER_AVAILABLE = False，需要检查导入错误'
            
            # 检查是否有 Blueprint 导入成功
            if 'blueprints_available = True' in content:
                results['blueprints_available'] = True
            elif 'blueprints_available = False' in content:
                results['blueprints_available'] = False
                results['warning'] = '代码中有 blueprints_available = False，需要检查导入错误'
                
        except Exception as e:
            results['error'] = f'读取 app.py 失败: {str(e)}'
    
    return results


def generate_report():
    """生成完整的验证报告"""
    print("=" * 80)
    print("服务层和 Blueprint 稳定性验证报告")
    print("=" * 80)
    print()
    
    # 1. 检查启动标志
    print("1. 检查 app.py 启动标志")
    print("-" * 80)
    flags = check_app_startup_flags()
    if flags.get('app_file_path'):
        print(f"✓ 找到 app.py: {flags['app_file_path']}")
    print(f"服务层标志: {'✓ 可用' if flags['service_layer_available'] else '✗ 不可用'}")
    print(f"Blueprint 标志: {'✓ 可用' if flags['blueprints_available'] else '✗ 不可用'}")
    if flags.get('warning'):
        print(f"⚠ 警告: {flags['warning']}")
    print()
    
    # 2. 检查服务层模块
    print("2. 检查服务层模块")
    print("-" * 80)
    service_results = check_service_layer()
    if service_results['available']:
        print("✓ 所有服务层模块可用")
    else:
        print("✗ 部分服务层模块不可用:")
        for error in service_results['errors']:
            print(f"  - {error}")
    
    for module_name, module_data in service_results['modules'].items():
        if isinstance(module_data, dict) and 'error' in module_data:
            print(f"  ✗ {module_name}: {module_data['error']}")
        else:
            print(f"  ✓ {module_name}")
            if isinstance(module_data, dict):
                for func_name, func_data in module_data.items():
                    if isinstance(func_data, dict):
                        status = '✓' if func_data.get('available') else '✗'
                        print(f"    {status} {func_name}")
    print()
    
    # 3. 检查 Blueprint
    print("3. 检查 Blueprint 模块")
    print("-" * 80)
    blueprint_results = check_blueprints()
    if blueprint_results['available']:
        print("✓ 所有 Blueprint 模块可用")
    else:
        print("✗ 部分 Blueprint 模块不可用:")
        for error in blueprint_results['errors']:
            print(f"  - {error}")
    
    for bp_name, bp_data in blueprint_results['blueprints'].items():
        if bp_data.get('available'):
            print(f"  ✓ {bp_name} (name: {bp_data.get('name')})")
        else:
            print(f"  ✗ {bp_name}: {bp_data.get('error')}")
    print()
    
    # 4. 测试服务函数
    print("4. 测试服务函数")
    print("-" * 80)
    test_results = test_service_functions()
    if test_results['passed']:
        print("✓ 通过的测试:")
        for test in test_results['passed']:
            print(f"  - {test}")
    if test_results['failed']:
        print("✗ 失败的测试:")
        for test in test_results['failed']:
            print(f"  - {test}")
    if test_results['skipped']:
        print("⊘ 跳过的测试:")
        for test in test_results['skipped']:
            print(f"  - {test}")
    print()
    
    # 5. 总结和建议
    print("5. 总结和建议")
    print("-" * 80)
    all_ok = (
        flags.get('service_layer_available', False) and
        flags.get('blueprints_available', False) and
        service_results['available'] and
        blueprint_results['available'] and
        len(test_results['failed']) == 0
    )
    
    if all_ok:
        print("✓ 所有检查通过！服务层和 Blueprint 在生产环境中稳定运行。")
        print("建议: 可以安全地删除 app.py 中的后备实现代码。")
    else:
        print("✗ 发现问题，建议修复后再删除后备代码:")
        if not flags.get('service_layer_available'):
            print("  - 检查服务层模块导入错误")
        if not flags.get('blueprints_available'):
            print("  - 检查 Blueprint 模块导入错误")
        if not service_results['available']:
            print("  - 修复服务层模块问题")
        if not blueprint_results['available']:
            print("  - 修复 Blueprint 模块问题")
        if test_results['failed']:
            print("  - 修复服务函数测试失败")
    
    print()
    print("=" * 80)
    
    return all_ok


if __name__ == '__main__':
    try:
        success = generate_report()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"验证过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

