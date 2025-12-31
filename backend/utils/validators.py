"""
输入验证工具模块
提供统一的输入验证函数
"""
import re
from typing import Any, Dict, Optional, List, Union
from flask import jsonify


class ValidationError(Exception):
    """验证错误异常"""
    pass


def validate_string(value: Any, field_name: str, min_length: int = 1, max_length: int = 100, 
                   allow_empty: bool = False, pattern: Optional[str] = None) -> str:
    """
    验证字符串输入
    
    Args:
        value: 要验证的值
        field_name: 字段名称（用于错误消息）
        min_length: 最小长度
        max_length: 最大长度
        allow_empty: 是否允许空字符串
        pattern: 正则表达式模式（可选）
    
    Returns:
        验证后的字符串
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    if value is None:
        if allow_empty:
            return ""
        raise ValidationError(f"{field_name} 不能为空")
    
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} 必须是字符串")
    
    value = value.strip()
    
    if not allow_empty and len(value) == 0:
        raise ValidationError(f"{field_name} 不能为空")
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} 长度不能少于 {min_length} 个字符")
    
    if len(value) > max_length:
        raise ValidationError(f"{field_name} 长度不能超过 {max_length} 个字符")
    
    if pattern and not re.match(pattern, value):
        raise ValidationError(f"{field_name} 格式不正确")
    
    return value


def validate_number(value: Any, field_name: str, min_value: Optional[float] = None, 
                   max_value: Optional[float] = None, allow_none: bool = False) -> Optional[float]:
    """
    验证数字输入
    
    Args:
        value: 要验证的值
        field_name: 字段名称
        min_value: 最小值
        max_value: 最大值
        allow_none: 是否允许 None
    
    Returns:
        验证后的数字
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} 不能为空")
    
    try:
        num_value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} 必须是数字")
    
    if min_value is not None and num_value < min_value:
        raise ValidationError(f"{field_name} 不能小于 {min_value}")
    
    if max_value is not None and num_value > max_value:
        raise ValidationError(f"{field_name} 不能大于 {max_value}")
    
    return num_value


def validate_integer(value: Any, field_name: str, min_value: Optional[int] = None, 
                    max_value: Optional[int] = None, allow_none: bool = False) -> Optional[int]:
    """
    验证整数输入
    
    Args:
        value: 要验证的值
        field_name: 字段名称
        min_value: 最小值
        max_value: 最大值
        allow_none: 是否允许 None
    
    Returns:
        验证后的整数
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    num_value = validate_number(value, field_name, min_value, max_value, allow_none)
    if num_value is None:
        return None
    
    if not num_value.is_integer():
        raise ValidationError(f"{field_name} 必须是整数")
    
    return int(num_value)


def validate_boolean(value: Any, field_name: str, allow_none: bool = False) -> Optional[bool]:
    """
    验证布尔值输入
    
    Args:
        value: 要验证的值
        field_name: 字段名称
        allow_none: 是否允许 None
    
    Returns:
        验证后的布尔值
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} 不能为空")
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        if value_lower in ('false', '0', 'no', 'off'):
            return False
    
    raise ValidationError(f"{field_name} 必须是布尔值")


def validate_choice(value: Any, field_name: str, choices: List[Any], allow_none: bool = False) -> Optional[Any]:
    """
    验证选择值（枚举）
    
    Args:
        value: 要验证的值
        field_name: 字段名称
        choices: 允许的值列表
        allow_none: 是否允许 None
    
    Returns:
        验证后的值
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} 不能为空")
    
    if value not in choices:
        raise ValidationError(f"{field_name} 必须是以下值之一: {', '.join(map(str, choices))}")
    
    return value


def validate_node_id(node_id: Any, field_name: str = "节点ID") -> str:
    """
    验证节点ID格式
    
    Args:
        node_id: 节点ID
        field_name: 字段名称
    
    Returns:
        验证后的节点ID
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    return validate_string(
        node_id, 
        field_name, 
        min_length=1, 
        max_length=50,
        pattern=r'^[A-Z0-9_]+$'  # 只允许大写字母、数字和下划线
    )


def validate_edge_id(edge_id: Any, field_name: str = "边ID") -> str:
    """
    验证边ID格式
    
    Args:
        edge_id: 边ID
        field_name: 字段名称
    
    Returns:
        验证后的边ID
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    return validate_string(
        edge_id, 
        field_name, 
        min_length=1, 
        max_length=50,
        pattern=r'^[A-Z0-9_]+$'  # 只允许大写字母、数字和下划线
    )


def validate_vehicle_type(vehicle_type: Any) -> str:
    """
    验证车辆类型
    
    Args:
        vehicle_type: 车辆类型
    
    Returns:
        验证后的车辆类型
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    valid_types = ['渣土车', '材料车', '工程车', '特种车']
    return validate_choice(vehicle_type, "车辆类型", valid_types)


def validate_direction(direction: Any, allow_none: bool = False) -> Optional[str]:
    """
    验证道路方向
    
    Args:
        direction: 方向值
        allow_none: 是否允许 None
    
    Returns:
        验证后的方向
    
    Raises:
        ValidationError: 验证失败时抛出
    """
    valid_directions = ['two-way', 'one-way', 'east', 'west', 'north', 'south', 
                       'northeast', 'northwest', 'southeast', 'southwest']
    return validate_choice(direction, "道路方向", valid_directions, allow_none)


def validate_request_data(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    根据模式验证请求数据
    
    Args:
        data: 请求数据字典
        schema: 验证模式，格式为 {字段名: {验证规则}}
    
    Returns:
        验证后的数据字典
    
    Raises:
        ValidationError: 验证失败时抛出
    
    Example:
        schema = {
            'name': {'type': 'string', 'required': True, 'min_length': 1, 'max_length': 50},
            'age': {'type': 'integer', 'required': True, 'min_value': 0, 'max_value': 150},
            'email': {'type': 'string', 'required': False, 'pattern': r'^[^@]+@[^@]+\.[^@]+$'}
        }
    """
    validated_data = {}
    errors = []
    
    for field_name, rules in schema.items():
        value = data.get(field_name)
        required = rules.get('required', False)
        
        # 检查必填字段
        if required and (value is None or (isinstance(value, str) and not value.strip())):
            errors.append(f"{field_name} 是必填字段")
            continue
        
        # 如果字段为空且不是必填，跳过验证
        if value is None or (isinstance(value, str) and not value.strip()):
            if not required:
                continue
        
        try:
            field_type = rules.get('type', 'string')
            
            if field_type == 'string':
                validated_value = validate_string(
                    value,
                    field_name,
                    min_length=rules.get('min_length', 1),
                    max_length=rules.get('max_length', 100),
                    allow_empty=not required,
                    pattern=rules.get('pattern')
                )
            elif field_type == 'number':
                validated_value = validate_number(
                    value,
                    field_name,
                    min_value=rules.get('min_value'),
                    max_value=rules.get('max_value'),
                    allow_none=not required
                )
            elif field_type == 'integer':
                validated_value = validate_integer(
                    value,
                    field_name,
                    min_value=rules.get('min_value'),
                    max_value=rules.get('max_value'),
                    allow_none=not required
                )
            elif field_type == 'boolean':
                validated_value = validate_boolean(
                    value,
                    field_name,
                    allow_none=not required
                )
            elif field_type == 'choice':
                validated_value = validate_choice(
                    value,
                    field_name,
                    choices=rules.get('choices', []),
                    allow_none=not required
                )
            else:
                validated_value = value  # 未知类型，直接使用原值
            
            validated_data[field_name] = validated_value
            
        except ValidationError as e:
            errors.append(str(e))
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    return validated_data


def handle_validation_error(error: ValidationError):
    """
    处理验证错误，返回 Flask JSON 响应
    
    Args:
        error: ValidationError 异常
    
    Returns:
        Flask JSON 响应
    """
    return jsonify({
        'success': False,
        'message': str(error)
    }), 400

