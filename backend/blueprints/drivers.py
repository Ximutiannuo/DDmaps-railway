"""
司机相关 Blueprint
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.utils.api_handler import api_handler
from backend.models.system_state import system_state
from backend.config import Config

bp = Blueprint('drivers', __name__, url_prefix='/api')

# 从服务层导入
from backend.services.path_planning_service import (
    get_node_by_id,
    calculate_efficient_path,
    get_vehicle_speed_kmph,
    estimate_efficiency_score,
    estimate_travel_minutes,
    serialize_path_edges,
    build_node_sequence_from_path
)

@bp.route('/drivers', methods=['GET'])
@api_handler
def get_drivers():
    """获取司机列表"""
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        # 确保返回的是数组格式，而不是对象
        drivers_list = list(drivers.values()) if isinstance(drivers, dict) else (drivers if isinstance(drivers, list) else [])
        return jsonify({
            'success': True,
            'drivers': drivers_list,
            'driver_routes': system_state.get('driver_routes', {})
        })

@bp.route('/drivers', methods=['POST'])
@api_handler
def register_driver():
    """注册或更新司机信息"""
    data = request.json or {}
    driver_id = data.get('driver_id') or data.get('id')
    
    if not driver_id:
        return jsonify({'success': False, 'message': '请提供司机ID (driver_id)'}), 400
    
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        
        # 获取现有司机信息（如果存在），保留已注册时间
        existing_driver = drivers.get(driver_id, {})
        
        driver = {
            'id': driver_id,
            'name': data.get('name', existing_driver.get('name', driver_id)),
            'phone': data.get('phone', existing_driver.get('phone', '')),
            'license_plate': data.get('license_plate', existing_driver.get('license_plate', '')),  # 车牌号
            'contact': data.get('contact', existing_driver.get('contact', '')),  # 联系电话（兼容旧字段）
            'vehicle_type': data.get('vehicle_type', existing_driver.get('vehicle_type', '渣土车')),
            'weight': data.get('weight', existing_driver.get('weight', 20)),
            'width': data.get('width', existing_driver.get('width', 3)),
            'custom_speed_kmph': data.get('custom_speed_kmph', existing_driver.get('custom_speed_kmph')),
            'default_start_node': data.get('default_start_node', existing_driver.get('default_start_node')),
            'default_target_node': data.get('default_target_node', existing_driver.get('default_target_node')),
            'registered_at': existing_driver.get('registered_at') or datetime.now().isoformat(),
            'last_active': datetime.now().isoformat()
        }
        
        # 兼容处理：如果提供了 contact 但没有 phone，使用 contact 作为 phone
        if not driver['phone'] and driver['contact']:
            driver['phone'] = driver['contact']
        
        drivers[driver_id] = driver
        system_state.set('drivers', drivers)
        
        return jsonify({
            'success': True,
            'driver': driver,
            'message': f'司机 {driver_id} 注册成功'
        })

@bp.route('/drivers/<driver_id>', methods=['GET'])
@api_handler
def get_driver(driver_id):
    """获取司机信息"""
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': f'司机 {driver_id} 未注册'}), 404
        
        return jsonify({
            'success': True,
            'driver': driver
        })

@bp.route('/drivers/<driver_id>/route-preview', methods=['POST'])
@api_handler
def driver_route_preview(driver_id):
    """司机路线预览"""
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': f'司机 {driver_id} 未注册'}), 404
        
        data = request.json or {}
        
        # 获取起点和目标点
        start_node_id = data.get('start_node') or driver.get('default_start_node')
        target_node_id = data.get('target_node') or driver.get('default_target_node')
        
        if not start_node_id or not target_node_id:
            return jsonify({'success': False, 'message': '请提供起点和目标点'}), 400
        
        # 验证节点
        start_node = get_node_by_id(start_node_id)
        target_node = get_node_by_id(target_node_id)
        
        if not start_node:
            return jsonify({'success': False, 'message': f'起点节点 {start_node_id} 不存在'}), 400
        if not target_node:
            return jsonify({'success': False, 'message': f'目标节点 {target_node_id} 不存在'}), 400
        
        # 车辆参数
        vehicle_type = data.get('vehicle_type') or driver.get('vehicle_type', '渣土车')
        weight = float(data.get('weight', 20))
        width = float(data.get('width', 3))
        custom_speed = data.get('custom_speed_kmph', driver.get('custom_speed_kmph'))
        try:
            custom_speed = float(custom_speed) if custom_speed is not None else None
        except (TypeError, ValueError):
            custom_speed = None
        if custom_speed is not None and custom_speed <= 0:
            custom_speed = None
        
        # 检查是否提供了预计算的路径信息（如DQN路线）
        provided_path_edges = data.get('path_edges')
        provided_path_nodes = data.get('path_nodes')
        provided_estimated_minutes = data.get('estimated_minutes')
        provided_efficiency_score = data.get('efficiency_score')
        planner = data.get('planner', 'classic')
        
        # 如果提供了路径信息（如DQN路线），直接使用
        if provided_path_edges and isinstance(provided_path_edges, list) and len(provided_path_edges) > 0:
            # 使用提供的路径信息
            serialized_edges = provided_path_edges
            node_sequence = provided_path_nodes if provided_path_nodes and len(provided_path_nodes) >= 2 else []
            efficiency = provided_efficiency_score
            estimated_minutes = provided_estimated_minutes
            
            # 如果节点序列为空或只有一个，尝试从边重建
            if not node_sequence or len(node_sequence) < 2:
                node_sequence = build_node_sequence_from_path(start_node_id, serialized_edges)
                # 如果重建失败，至少确保有起点和终点
                if not node_sequence or len(node_sequence) < 2:
                    node_sequence = []
                    if start_node:
                        node_sequence.append({
                            'id': start_node.get('id'),
                            'name': start_node.get('name'),
                            'type': start_node.get('type')
                        })
                    if target_node and target_node_id != start_node_id:
                        node_sequence.append({
                            'id': target_node.get('id'),
                            'name': target_node.get('name'),
                            'type': target_node.get('type')
                        })
            
            # 如果没有提供效率评分或预计时间，尝试计算
            if efficiency is None:
                # 尝试从边重建路径对象来计算效率评分
                edges = system_state.get('edges', [])
                path_objects = []
                for edge_data in serialized_edges:
                    edge_id = edge_data.get('id') or edge_data.get('edge_id')
                    if edge_id:
                        edge = next((e for e in edges if e.get('id') == edge_id), None)
                        if edge:
                            path_objects.append(edge)
                if path_objects:
                    efficiency = estimate_efficiency_score(path_objects)
            
            if estimated_minutes is None and custom_speed is not None and custom_speed > 0:
                # 计算总距离
                total_distance = sum(
                    float(edge.get('length_m') or edge.get('length') or 0.0)
                    for edge in serialized_edges
                )
                if total_distance > 0:
                    estimated_minutes = (total_distance / 1000.0) / (custom_speed / 60.0)
        else:
            # 没有提供路径信息，需要计算路径
            vehicle_template = {
                'id': f'driver-{driver_id}',
                'type': vehicle_type,
                'weight': weight,
                'width': width,
                'target_node': target_node_id,
                'start_node': start_node_id,
                'custom_speed_kmph': custom_speed
            }
            
            path = calculate_efficient_path(start_node_id, target_node_id, vehicle_template)
            
            if not path:
                return jsonify({'success': False, 'message': '无法找到有效路径，请尝试其他节点或检查道路状态'}), 400
            
            # 计算路线评估指标
            efficiency = estimate_efficiency_score(path)
            estimated_minutes = estimate_travel_minutes(
                path,
                vehicle_type,
                custom_speed_kmph=custom_speed,
                start_node=start_node_id,
                target_node=target_node_id
            )
            node_sequence = build_node_sequence_from_path(start_node_id, path)
            serialized_edges = serialize_path_edges(path)
        
        # 保存路线记录（包含完整信息）
        driver_routes = system_state.get('driver_routes', {})
        if driver_id not in driver_routes:
            driver_routes[driver_id] = []
        
        route_record = {
            'driver_id': driver_id,
            'start_node': start_node_id,
            'target_node': target_node_id,
            'vehicle_type': vehicle_type,
            'weight': weight,
            'width': width,
            'requested_at': datetime.now().isoformat(),
            'efficiency_score': efficiency,
            'estimated_minutes': estimated_minutes,
            'path_edges': serialized_edges,
            'path_nodes': node_sequence,
            'custom_speed_kmph': custom_speed,
            'planner': planner  # 记录使用的规划算法
        }
        
        driver_routes[driver_id].append(route_record)
        
        # 限制历史记录数量
        if len(driver_routes[driver_id]) > Config.MAX_DRIVER_ROUTES:
            driver_routes[driver_id] = driver_routes[driver_id][-Config.MAX_DRIVER_ROUTES:]
        
        system_state.set('driver_routes', driver_routes)
        
        # 更新司机信息
        if custom_speed is not None:
            driver['custom_speed_kmph'] = custom_speed
        driver['last_active'] = route_record['requested_at']
        driver['default_start_node'] = start_node_id
        driver['default_target_node'] = target_node_id
        drivers[driver_id] = driver
        system_state.set('drivers', drivers)
        
        return jsonify({
            'success': True,
            'route': route_record,
            'message': '路线规划成功'
        })

@bp.route('/driver-routes', methods=['GET'])
@api_handler
def list_driver_routes():
    """获取所有司机的路线请求历史"""
    with system_state.lock:
        driver_routes = system_state.get('driver_routes', {})
        return jsonify({
            'success': True,
            'driver_routes': driver_routes
        })

@bp.route('/drivers/<driver_id>/submit-vehicle', methods=['POST'])
@api_handler
def driver_submit_vehicle(driver_id):
    """司机提交路线规划为实际车辆"""
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': f'司机 {driver_id} 未注册'}), 404
        
        data = request.json or {}
        
        # 获取最近的路线规划，或者使用传入的参数
        driver_routes = system_state.get('driver_routes', {})
        routes = driver_routes.get(driver_id, [])
        
        if not routes:
            return jsonify({'success': False, 'message': '请先进行路线规划'}), 400
        
        # 使用最近的路线规划
        latest_route = routes[-1] if not data.get('route_index') else routes[data.get('route_index')]
        
        start_node_id = latest_route['start_node']
        target_node_id = latest_route['target_node']
        vehicle_type = latest_route['vehicle_type']
        weight = latest_route['weight']
        width = latest_route['width']
        custom_speed = latest_route.get('custom_speed_kmph')
        if custom_speed is None:
            custom_speed = driver.get('custom_speed_kmph')
        
        try:
            custom_speed = float(custom_speed) if custom_speed is not None else None
        except (TypeError, ValueError):
            custom_speed = None
        if custom_speed is not None and custom_speed <= 0:
            custom_speed = None
        
        # 生成车辆ID
        vehicle_counter = system_state.get('vehicle_counter', 1)
        vehicle_id = data.get('vehicle_id') or f"V{vehicle_counter}"
        system_state.set('vehicle_counter', vehicle_counter + 1)
        
        # 验证节点
        start_node = get_node_by_id(start_node_id)
        if not start_node:
            return jsonify({'success': False, 'message': f'起点 {start_node_id} 不存在'}), 404
        target_node = get_node_by_id(target_node_id)
        if not target_node:
            return jsonify({'success': False, 'message': f'目标节点 {target_node_id} 不存在'}), 404
        
        # 使用路线规划中的路径，或重新计算
        path = []
        if latest_route.get('path_edges') and len(latest_route['path_edges']) > 0:
            # 从序列化的边重建路径
            edges = system_state.get('edges', [])
            from backend.utils.logger import logger
            logger.info(f'🔍 [提交车辆] 开始重建路径，planned_path_edges数量: {len(latest_route["path_edges"])}')
            
            for idx, edge_data in enumerate(latest_route['path_edges']):
                edge_id = edge_data.get('id') or edge_data.get('edge_id')
                if edge_id:
                    edge = next((e for e in edges if e.get('id') == edge_id), None)
                    if edge:
                        # 检查边的方向和长度
                        start_node_check = get_node_by_id(edge.get('start_node'))
                        end_node_check = get_node_by_id(edge.get('end_node'))
                        if not start_node_check or not end_node_check:
                            logger.warning(f'⚠️ [提交车辆] 边 {idx+1}: {edge_id} 的节点不存在！'
                                         f'start_node={edge.get("start_node")}, end_node={edge.get("end_node")}')
                            # 即使节点不存在，也尝试添加边（可能是数据问题）
                        
                        dx = end_node_check['x'] - start_node_check['x'] if end_node_check and start_node_check else 0
                        dy = end_node_check['y'] - start_node_check['y'] if end_node_check and start_node_check else 0
                        is_vertical = abs(dx) < abs(dy)  # 竖向道路判断
                        length_m = edge.get('length_m') or edge.get('length') or 0
                        
                        # 调试信息已移除
                        path.append(edge)
                    else:
                        # 边在系统中未找到，尝试从序列化数据重建边信息
                        logger.warning(f'⚠️ [提交车辆] 边 {idx+1}: {edge_id} 在系统中未找到！尝试从序列化数据重建...')
                        
                        # 检查序列化数据是否完整
                        if edge_data.get('start_node') and edge_data.get('end_node'):
                            # 尝试从序列化数据重建边
                            reconstructed_edge = {
                                'id': edge_id,
                                'start_node': edge_data.get('start_node'),
                                'end_node': edge_data.get('end_node'),
                                'length': edge_data.get('length') or edge_data.get('length_m') or 1.0,
                                'length_m': edge_data.get('length_m') or edge_data.get('length') or 1.0,
                                'congestion_coeff': edge_data.get('congestion_coeff', 1.0),
                                'direction': edge_data.get('direction', 'two-way'),
                                'max_weight': edge_data.get('max_weight', 50),
                                'max_width': edge_data.get('max_width', 5),
                                'is_available': True
                            }
                            
                            # 检查节点是否存在
                            start_node_check = get_node_by_id(reconstructed_edge['start_node'])
                            end_node_check = get_node_by_id(reconstructed_edge['end_node'])
                            
                            if start_node_check and end_node_check:
                                dx = end_node_check['x'] - start_node_check['x']
                                dy = end_node_check['y'] - start_node_check['y']
                                is_vertical = abs(dx) < abs(dy)
                                # 调试信息已移除
                                path.append(reconstructed_edge)
                            else:
                                logger.error(f'❌ [提交车辆] 边 {idx+1}: {edge_id} 重建失败，节点不存在！'
                                           f'start_node={reconstructed_edge["start_node"]}, end_node={reconstructed_edge["end_node"]}')
                        else:
                            logger.error(f'❌ [提交车辆] 边 {idx+1}: {edge_id} 无法重建，序列化数据不完整: {edge_data}')
                else:
                    logger.warning(f'⚠️ [提交车辆] 边 {idx+1}: 缺少ID，数据: {edge_data}')
            
            logger.info(f'✅ [提交车辆] 路径重建完成，最终路径数量: {len(path)}')
        
        # 如果路径重建失败或为空，重新计算路径
        if not path:
            vehicle_template = {
                'id': vehicle_id,
                'type': vehicle_type,
                'weight': weight,
                'width': width,
                'target_node': target_node_id,
                'start_node': start_node_id,
                'custom_speed_kmph': custom_speed
            }
            path = calculate_efficient_path(start_node_id, target_node_id, vehicle_template)
        
        if not path:
            return jsonify({'success': False, 'message': '无法找到有效路径'}), 400
        
        # 验证路径的第一条边是否从起点开始
        if path and len(path) > 0:
            first_edge = path[0]
            first_edge_start = first_edge.get('start_node')
            if first_edge_start != start_node_id:
                # 路径的第一条边不是从起点开始，这可能是因为路径序列化的问题
                # 尝试找到从起点开始的正确路径
                from backend.utils.logger import logger
                logger.warning(f'路径第一条边的起点 {first_edge_start} 与车辆起点 {start_node_id} 不匹配，尝试修正')
                
                # 检查路径中是否有从起点开始的边
                found_correct_start = False
                for i, edge in enumerate(path):
                    if edge.get('start_node') == start_node_id:
                        # 找到从起点开始的边，移除之前的边
                        path = path[i:]
                        found_correct_start = True
                        break
                
                if not found_correct_start:
                    # 如果路径中没有从起点开始的边，重新计算路径
                    logger.warning(f'路径中没有从起点 {start_node_id} 开始的边，重新计算路径')
                    vehicle_template = {
                        'id': vehicle_id,
                        'type': vehicle_type,
                        'weight': weight,
                        'width': width,
                        'target_node': target_node_id,
                        'start_node': start_node_id,
                        'custom_speed_kmph': custom_speed
                    }
                    path = calculate_efficient_path(start_node_id, target_node_id, vehicle_template)
                    if not path:
                        return jsonify({'success': False, 'message': '无法找到有效路径'}), 400
        
        # 创建实际车辆
        speed_for_vehicle = custom_speed if custom_speed is not None else get_vehicle_speed_kmph(vehicle_type)
        start_time_iso = datetime.now().isoformat()
        
        # 从路线规划中获取路径信息
        planned_path_edges = latest_route.get('path_edges', [])
        planned_path_nodes = latest_route.get('path_nodes', [])
        
        # 如果路线规划中没有路径信息，从当前路径生成
        if not planned_path_edges and path:
            from backend.services.path_planning_service import serialize_path_edges, build_node_sequence_from_path
            planned_path_edges = serialize_path_edges(path)
            planned_path_nodes = build_node_sequence_from_path(start_node_id, path)
        
        # 计算总距离
        from backend.services.path_planning_service import get_edge_length_m
        total_distance_m = 0.0
        if path:
            total_distance_m = sum(get_edge_length_m(edge) for edge in path)
        elif planned_path_edges:
            total_distance_m = sum(
                float(edge.get('length_m') or edge.get('length') or 0.0)
                for edge in planned_path_edges
            )
        total_distance_m = float(round(total_distance_m, 3))
        
        # 计算预计时间（从路线规划中获取，如果没有则估算）
        estimated_minutes = latest_route.get('estimated_minutes')
        if estimated_minutes is None and total_distance_m > 0 and speed_for_vehicle > 0:
            estimated_minutes = (total_distance_m / 1000.0) / (speed_for_vehicle / 60.0)
        
        # 确保路径的第一条边从起点开始，并设置正确的初始位置
        initial_position = {'x': start_node['x'], 'y': start_node['y']}
        if path and len(path) > 0:
            first_edge_start = path[0].get('start_node')
            if first_edge_start != start_node_id:
                # 路径的第一条边起点不匹配，使用第一条边的实际起点
                first_edge_start_node = get_node_by_id(first_edge_start)
                if first_edge_start_node:
                    initial_position = {'x': first_edge_start_node['x'], 'y': first_edge_start_node['y']}
        
        # 记录最终的路径信息用于调试
        from backend.utils.logger import logger
        logger.info(f'📋 [提交车辆] 最终路径信息: 路径数量={len(path)}, planned_path_edges数量={len(planned_path_edges)}')
        for idx, edge in enumerate(path):
            start_node_check = get_node_by_id(edge.get('start_node'))
            end_node_check = get_node_by_id(edge.get('end_node'))
            if start_node_check and end_node_check:
                dx = end_node_check['x'] - start_node_check['x']
                dy = end_node_check['y'] - start_node_check['y']
                is_vertical = abs(dx) < abs(dy)
                length_m = get_edge_length_m(edge)
                logger.info(f'  📍 路径边 {idx+1}: {edge.get("id")}, '
                          f'{edge.get("start_node")} -> {edge.get("end_node")}, '
                          f'{"竖向" if is_vertical else "横向"}, 长度={length_m}m')
            else:
                logger.warning(f'  ⚠️ 路径边 {idx+1}: {edge.get("id")}, 无法找到节点')
        
        new_vehicle = {
            'id': vehicle_id,
            'type': vehicle_type,
            'speed_kmph': speed_for_vehicle,
            'weight': weight,
            'width': width,
            'target_node': target_node_id,
            'start_node': start_node_id,
            'current_position': initial_position,
            'assigned_entrance': start_node_id if start_node.get('type') == 'entrance' else None,
            'current_path': path,
            'status': 'moving',
            'progress': 0.0,  # 初始进度为0，确保从起点开始
            'created_at': start_time_iso,
            'start_time': start_time_iso,  # 记录出发时间（从提交为实际车辆时开始）
            'last_update_time': start_time_iso,
            'driver_id': driver_id,  # 关联司机ID
            'driver_name': driver.get('name', driver_id),
            # 保存完整的路径信息，用于到达时计算距离和速度
            'planned_path_edges': planned_path_edges,
            'planned_path_nodes': planned_path_nodes,
            'planned_total_distance_m': total_distance_m,
            'route_estimated_minutes': estimated_minutes,
            'route_efficiency_score': latest_route.get('efficiency_score'),
            'route_request_time': latest_route.get('requested_at'),
            'custom_speed_kmph': custom_speed
        }
        
        logger.info(f'✅ [提交车辆] 车辆 {vehicle_id} 创建成功，current_path数量={len(path)}')
        
        # 添加到车辆列表
        vehicles = system_state.get('vehicles', [])
        
        # 确保司机ID的唯一性：如果该司机已有其他车辆（包括已到达的），先清理它们
        # 避免同一司机ID在地图上显示多个车辆
        # 当司机重新注册或重新提交车辆时，应该只显示最新的车辆，旧的车辆（包括已到达的）都应该被清理
        existing_vehicles_for_driver = [v for v in vehicles if v.get('driver_id') == driver_id]
        if existing_vehicles_for_driver:
            # 移除该司机的所有旧车辆（包括已到达的），确保唯一性
            vehicles = [v for v in vehicles if v.get('driver_id') != driver_id]
            from backend.utils.logger import logger
            logger.info(f'司机 {driver_id} 重新提交车辆，已清理 {len(existing_vehicles_for_driver)} 个旧车辆记录（包括已到达车辆）')
        
        vehicles.append(new_vehicle)
        system_state.set('vehicles', vehicles)
        
        # 如果调度未运行，自动启动调度
        dispatch_was_started = False
        if not system_state.get('dispatch_running', False):
            system_state.set('dispatch_running', True)
            dispatch_was_started = True
        
        # 更新司机信息
        driver['active_vehicle_id'] = vehicle_id
        drivers[driver_id] = driver
        system_state.set('drivers', drivers)
        
        return jsonify({
            'success': True,
            'vehicle': new_vehicle,
            'message': f'车辆 {vehicle_id} 已创建并关联到司机 {driver_id}',
            'dispatch_started': dispatch_was_started
        })

@bp.route('/drivers/<driver_id>/location', methods=['POST'])
@api_handler
def update_driver_location(driver_id):
    """更新司机GPS位置"""
    from backend.services.location_service import update_driver_location as _update_driver_location
    
    data = request.json or {}
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    accuracy = data.get('accuracy')
    
    if latitude is None or longitude is None:
        return jsonify({
            'success': False,
            'message': '请提供纬度和经度'
        }), 400
    
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        accuracy = float(accuracy) if accuracy is not None else None
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': '坐标格式不正确'
        }), 400
    
    result = _update_driver_location(driver_id, latitude, longitude, accuracy)
    
    if not result.get('success', False):
        return jsonify(result), 404
    
    return jsonify(result)

@bp.route('/drivers/<driver_id>/location', methods=['GET'])
@api_handler
def get_driver_location(driver_id):
    """获取司机当前位置"""
    from backend.services.location_service import get_driver_location as _get_driver_location
    
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': f'司机 {driver_id} 未注册'}), 404
        
        location = _get_driver_location(driver_id)
        nearest_nodes = []
        
        if location:
            # 如果有位置信息，查找附近的节点
            from backend.services.location_service import find_nearest_nodes_by_gps
            nearest_nodes = find_nearest_nodes_by_gps(
                location['latitude'],
                location['longitude'],
                max_results=5
            )
        
        return jsonify({
            'success': True,
            'location': location,
            'nearest_nodes': nearest_nodes
        })

@bp.route('/drivers/<driver_id>/find-nodes-by-gps', methods=['POST'])
@api_handler
def find_nodes_by_gps(driver_id):
    """根据GPS坐标查找附近的节点"""
    from backend.services.location_service import find_nearest_nodes_by_gps
    
    data = request.json or {}
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    max_results = data.get('max_results', 5)
    max_distance_m = data.get('max_distance_m')
    
    if latitude is None or longitude is None:
        return jsonify({
            'success': False,
            'message': '请提供纬度和经度'
        }), 400
    
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        max_results = int(max_results) if max_results else 5
        max_distance_m = float(max_distance_m) if max_distance_m else None
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': '参数格式不正确'
        }), 400
    
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': f'司机 {driver_id} 未注册'}), 404
    
    nearest_nodes = find_nearest_nodes_by_gps(
        latitude,
        longitude,
        max_results=max_results,
        max_distance_m=max_distance_m
    )
    
    return jsonify({
        'success': True,
        'nearest_nodes': nearest_nodes,
        'message': f'找到 {len(nearest_nodes)} 个附近节点'
    })

@bp.route('/drivers/<driver_id>/confirm-start-node', methods=['POST'])
@api_handler
def confirm_start_node(driver_id):
    """司机确认起点节点"""
    data = request.json or {}
    node_id = data.get('node_id')
    latitude = data.get('latitude')  # 可选的GPS坐标
    longitude = data.get('longitude')
    
    if not node_id:
        return jsonify({
            'success': False,
            'message': '请提供节点ID'
        }), 400
    
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': f'司机 {driver_id} 未注册'}), 404
        
        # 验证节点是否存在
        start_node = get_node_by_id(node_id)
        if not start_node:
            return jsonify({'success': False, 'message': f'节点 {node_id} 不存在'}), 404
        
        # 更新司机的默认起点节点
        driver['default_start_node'] = node_id
        driver['last_active'] = datetime.now().isoformat()
        
        # 如果提供了GPS坐标，同时更新位置信息
        if latitude is not None and longitude is not None:
            from backend.services.location_service import update_driver_location as _update_driver_location
            try:
                _update_driver_location(driver_id, float(latitude), float(longitude))
            except:
                pass  # 位置更新失败不影响节点确认
        
        drivers[driver_id] = driver
        system_state.set('drivers', drivers)
    
    return jsonify({
        'success': True,
        'message': f'已确认起点节点: {start_node.get("name", node_id)}',
        'node': {
            'id': start_node.get('id'),
            'name': start_node.get('name'),
            'type': start_node.get('type')
        }
    })

@bp.route('/drivers/<driver_id>/arrival', methods=['POST'])
@api_handler
def driver_arrival(driver_id):
    """司机到达目的地（完整实现，包含历史数据记录）"""
    from uuid import uuid4
    from backend.services.travel_time_service import calculate_average_speed_kmph
    from backend.services.path_planning_service import get_node_by_id, build_node_sequence_from_path, serialize_path_edges
    from backend.utils.persistence import append_travel_time_record, save_travel_time_database
    
    with system_state.lock:
        drivers = system_state.get('drivers', {})
        driver = drivers.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': f'司机 {driver_id} 未注册'}), 404
        
        data = request.json or {}
        vehicle_id = data.get('vehicle_id') or driver.get('active_vehicle_id')
        
        if not vehicle_id:
            return jsonify({'success': False, 'message': '未找到需要确认到达的车辆'}), 400
        
        # 查找车辆
        vehicles = system_state.get('vehicles', [])
        vehicle = next((v for v in vehicles if v.get('id') == vehicle_id), None)
        
        if not vehicle:
            return jsonify({'success': False, 'message': f'车辆 {vehicle_id} 不存在'}), 404
        
        arrival_time = datetime.now()
        
        # 允许司机随时确认到达，不检查车辆是否已经到达目的地
        # 这样可以处理提前到达、延迟确认等实际情况
        # 行驶时间从"提交为实际车辆"到"确认到达"的时间，由司机自己决定何时确认
        
        # 如果车辆状态不是 'arrived'，更新为 'arrived'（允许司机提前或延迟确认）
        if vehicle.get('status') != 'arrived':
            vehicle['status'] = 'arrived'
        
        # 检查是否已经确认过到达（防止重复确认）
        if vehicle.get('arrival_time'):
            return jsonify({
                'success': False,
                'message': '该车辆已经确认过到达，无法重复确认'
            }), 400
        
        # 获取目标节点，更新车辆位置到终点
        target_node_id = vehicle.get('target_node')
        target_node = None
        if target_node_id:
            target_node = get_node_by_id(target_node_id)
        
        # 先保存路径数据的副本（用于到达记录），然后再清除
        planned_path_edges_backup = vehicle.get('planned_path_edges', [])[:]  # 深拷贝
        planned_path_nodes_backup = vehicle.get('planned_path_nodes', [])[:]  # 深拷贝
        
        # 现在设置 arrival_time（只有司机点击确认到达时才设置）
        vehicle['arrival_time'] = arrival_time.isoformat()
        vehicle['last_update_time'] = arrival_time.isoformat()
        
        # 清除路径数据，防止刷新后路径重新显示（在确认到达后清除）
        vehicle['current_path'] = []
        vehicle['planned_path_edges'] = []
        vehicle['planned_path_nodes'] = []
        
        # 更新车辆位置到终点节点位置
        if target_node:
            vehicle['current_position'] = {'x': target_node['x'], 'y': target_node['y']}
            vehicle['progress'] = 1.0  # 进度设为100%
        else:
            # 如果找不到目标节点，尝试从备份的路径节点中获取最后一个节点
            if planned_path_nodes_backup and len(planned_path_nodes_backup) > 0:
                last_node = planned_path_nodes_backup[-1]
                if last_node and isinstance(last_node, dict) and 'x' in last_node and 'y' in last_node:
                    vehicle['current_position'] = {'x': last_node['x'], 'y': last_node['y']}
                    vehicle['progress'] = 1.0
        
        driver['active_vehicle_id'] = None
        
        # 计算行驶时间（从提交为实际车辆到确认到达的时间）
        # 优先使用 start_time，如果没有则使用 created_at
        start_time_str = vehicle.get('start_time') or vehicle.get('created_at')
        duration_minutes = None
        if start_time_str:
            try:
                start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                duration_minutes = max(0.1, (arrival_time - start_dt).total_seconds() / 60.0)
            except (ValueError, AttributeError):
                duration_minutes = None
        
        # 如果无法从时间戳计算，尝试使用用户报告的时间
        if duration_minutes is None:
            reported_duration = data.get('duration_minutes')
            try:
                duration_minutes = float(reported_duration) if reported_duration is not None else 0.0
            except (TypeError, ValueError):
                duration_minutes = 0.0
        
        duration_minutes = round(duration_minutes, 2)
        
        # 计算距离
        planned_distance_m = vehicle.get('planned_total_distance_m')
        if not planned_distance_m or planned_distance_m <= 0:
            planned_edges_for_distance = planned_path_edges_backup
            planned_distance_m = sum(
                float(edge.get('length_m') or edge.get('length') or 0.0)
                for edge in planned_edges_for_distance
            )
        planned_distance_m = float(round(planned_distance_m or 0.0, 3))
        
        avg_speed_kmph = calculate_average_speed_kmph(planned_distance_m, duration_minutes)
        
        # 准备路径数据（使用备份的数据）
        planned_path_edges = planned_path_edges_backup
        # 如果 planned_path_edges 是字典列表且已包含 id 字段，说明已经序列化过，直接使用
        if planned_path_edges and isinstance(planned_path_edges[0], dict) and 'id' in planned_path_edges[0]:
            # 已经是序列化的格式，直接使用
            path_edge_summaries = planned_path_edges
        else:
            # 需要序列化（可能是边对象列表）
            path_edge_summaries = serialize_path_edges(planned_path_edges) if planned_path_edges else []
        
        # 构建路径节点序列（确保至少包含起点和终点，使用备份的数据）
        planned_path_nodes = planned_path_nodes_backup
        start_node_id = vehicle.get('start_node')
        target_node_id = vehicle.get('target_node')
        
        # 如果路径节点为空或只有一个，从路径边重建
        if not planned_path_nodes or len(planned_path_nodes) < 2:
            if start_node_id and target_node_id and planned_path_edges:
                planned_path_nodes = build_node_sequence_from_path(start_node_id, planned_path_edges)
            # 如果重建失败，至少确保有起点和终点
            if not planned_path_nodes or len(planned_path_nodes) < 2:
                planned_path_nodes = []
                if start_node_id:
                    start_node_obj = get_node_by_id(start_node_id)
                    if start_node_obj:
                        planned_path_nodes.append({
                            'id': start_node_obj.get('id'),
                            'name': start_node_obj.get('name'),
                            'type': start_node_obj.get('type')
                        })
                if target_node_id and target_node_id != start_node_id:
                    target_node_obj = get_node_by_id(target_node_id)
                    if target_node_obj:
                        planned_path_nodes.append({
                            'id': target_node_obj.get('id'),
                            'name': target_node_obj.get('name'),
                            'type': target_node_obj.get('type')
                        })
        
        path_node_summaries = []
        for node in planned_path_nodes:
            if isinstance(node, dict):
                path_node_summaries.append({
                    'id': node.get('id'),
                    'name': node.get('name'),
                    'type': node.get('type')
                })
            elif isinstance(node, str):
                node_obj = get_node_by_id(node)
                if node_obj:
                    path_node_summaries.append({
                        'id': node_obj.get('id'),
                        'name': node_obj.get('name'),
                        'type': node_obj.get('type')
                    })
        
        # 确保至少包含起点和终点（DQN训练需要至少2个节点）
        if len(path_node_summaries) < 2:
            # 重新构建，确保包含起点和终点
            path_node_summaries = []
            if start_node_id:
                start_node_obj = get_node_by_id(start_node_id)
                if start_node_obj:
                    path_node_summaries.append({
                        'id': start_node_obj.get('id'),
                        'name': start_node_obj.get('name'),
                        'type': start_node_obj.get('type')
                    })
            if target_node_id and target_node_id != start_node_id:
                target_node_obj = get_node_by_id(target_node_id)
                if target_node_obj:
                    # 避免重复添加
                    if not any(n.get('id') == target_node_id for n in path_node_summaries):
                        path_node_summaries.append({
                            'id': target_node_obj.get('id'),
                            'name': target_node_obj.get('name'),
                            'type': target_node_obj.get('type')
                        })
        
        estimated_minutes = vehicle.get('estimated_time') or vehicle.get('route_estimated_minutes')
        estimated_delta = None
        if estimated_minutes is not None:
            try:
                estimated_delta = round(duration_minutes - float(estimated_minutes), 2)
            except (TypeError, ValueError):
                estimated_delta = None
        
        # 创建到达记录
        arrival_record = {
            'driver_id': driver_id,
            'driver_name': driver.get('name', driver_id),
            'vehicle_id': vehicle_id,
            'vehicle_type': vehicle.get('type'),
            'start_node': vehicle.get('start_node'),
            'target_node': vehicle.get('target_node'),
            'custom_speed_kmph': vehicle.get('custom_speed_kmph') or vehicle.get('speed_kmph'),
            'start_time': start_time_str,
            'arrival_time': vehicle['arrival_time'],
            'duration_minutes': duration_minutes,
            'distance_m': planned_distance_m,
            'avg_speed_kmph': avg_speed_kmph
        }
        
        arrival_records = system_state.get('arrival_records', [])
        arrival_records.append(arrival_record)
        system_state.set('arrival_records', arrival_records)
        
        # 创建行驶时间记录（用于训练）
        travel_record = {
            'record_id': f'TR-{uuid4().hex}',
            'driver_id': driver_id,
            'driver_name': driver.get('name', driver_id),
            'vehicle_id': vehicle_id,
            'vehicle_type': vehicle.get('type'),
            'start_node': vehicle.get('start_node'),
            'target_node': vehicle.get('target_node'),
            'route_key': f"{vehicle.get('start_node')}->{vehicle.get('target_node')}",
            'custom_speed_kmph': vehicle.get('custom_speed_kmph'),
            'speed_setting_kmph': vehicle.get('speed_kmph'),
            'custom_speed_source': vehicle.get('custom_speed_source'),
            'duration_minutes': duration_minutes,
            'distance_m': planned_distance_m,
            'average_speed_kmph': avg_speed_kmph,
            'estimated_minutes': estimated_minutes,
            'estimated_delta_minutes': estimated_delta,
            'start_time': start_time_str,
            'arrival_time': vehicle['arrival_time'],
            'route_request_time': vehicle.get('route_request_time'),
            'route_efficiency_score': vehicle.get('route_efficiency_score'),
            'path_edge_count': len(path_edge_summaries),
            'path_edges': path_edge_summaries,
            'path_node_count': len(path_node_summaries),
            'path_nodes': path_node_summaries,
            'weight_tons': vehicle.get('weight'),
            'width_m': vehicle.get('width'),
            'data_version': 1,
            'created_at': arrival_time.isoformat(),
            'weekday': arrival_time.weekday(),
            'hour_of_day': arrival_time.hour,
            'source': 'driver_feedback'
        }
        
        # 保存到行驶时间数据库
        append_travel_time_record(travel_record)
        save_travel_time_database(force=True)  # 立即保存
        
        # 记录路线耗时统计
        from backend.utils.persistence import record_route_duration
        record_route_duration(
            vehicle.get('start_node'),
            vehicle.get('target_node'),
            duration_minutes,
            vehicle_type=vehicle.get('type'),
            custom_speed_kmph=arrival_record.get('custom_speed_kmph'),
            distance_m=planned_distance_m,
            avg_speed_kmph=avg_speed_kmph
        )
        
        # 更新司机最后活跃时间
        driver['last_active'] = arrival_time.isoformat()
        drivers[driver_id] = driver
        system_state.set('drivers', drivers)
        
        # 保存车辆数据（包含清除的路径数据）到 system_state
        system_state.set('vehicles', vehicles)
        
        # 尝试通过 WebSocket 广播车辆更新（如果可用）
        try:
            import sys
            if 'app' in sys.modules:
                app_module = sys.modules['app']
                socketio = getattr(app_module, 'socketio', None)
                if socketio is not None:
                    socketio.emit('vehicle_update', {
                        'vehicles': system_state.get('vehicles', []),
                        'monitor_data': system_state.get('monitor_data', {}),
                        'timestamp': arrival_time.isoformat()
                    }, namespace='/')
        except Exception as ws_error:
            # WebSocket 广播失败不影响到达记录的保存
            pass
        
        return jsonify({
            'success': True,
            'message': '到达记录已保存',
            'arrival_record': arrival_record,
            'travel_record': travel_record
        })

