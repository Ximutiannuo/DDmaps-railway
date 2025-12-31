"""
DQN (Deep Q-Network) 服务模块
"""
import math
import random
from typing import Dict, Any, List, Optional

try:
    import torch  # type: ignore
    from torch import nn  # type: ignore
except ImportError:
    torch = None  # type: ignore
    nn = None  # type: ignore

from backend.models.system_state import system_state
from backend.services.path_planning_service import (
    get_node_by_id,
    get_edges_connected_to_node,
    get_edge_length_m
)
from backend.utils.logger import logger


class RoadEnvironment:
    """基于当前路网与数据库构建的强化学习环境"""

    def __init__(self, state_ref: Dict[str, Any]):
        self.state_ref = state_ref
        self.state_dim = 8
        self.action_dim = 5

    def _normalize(self, value: float, scale: float) -> float:
        if scale == 0:
            return 0.0
        return float(value) / float(scale)

    def _direction_to_scalar(self, direction: str | None) -> float:
        if not direction:
            return 0.0
        mapping = {
            'two-way': 0.0,
            'east': 0.1,
            'northeast': 0.2,
            'north': 0.3,
            'northwest': 0.4,
            'west': 0.5,
            'southwest': 0.6,
            'south': 0.7,
            'southeast': 0.8
        }
        return mapping.get(direction, 0.9)

    def build_state_vector(self, current_node_id: str | None, target_node_id: str | None) -> List[float]:
        if not current_node_id or not target_node_id:
            return [0.0] * self.state_dim
        current_node = get_node_by_id(current_node_id)
        target_node = get_node_by_id(target_node_id)
        if not current_node or not target_node:
            return [0.0] * self.state_dim

        dx = target_node['x'] - current_node['x']
        dy = target_node['y'] - current_node['y']
        distance = math.hypot(dx, dy)
        congestion = system_state.get('node_congestion', {}).get(current_node_id, 0) / 3.0
        work_zone_flag = 1.0 if current_node_id in system_state.get('work_zones', set()) else 0.0
        connected_edges = len(get_edges_connected_to_node(current_node_id))
        max_nodes = max(1, len(system_state.get('nodes', [])))

        state_vec = [
            self._normalize(current_node['x'], 1500.0),
            self._normalize(current_node['y'], 1500.0),
            self._normalize(dx, 1500.0),
            self._normalize(dy, 1500.0),
            self._normalize(distance, 2000.0),
            congestion,
            work_zone_flag,
            connected_edges / max_nodes
        ]
        return state_vec

    def build_action_vector(self, edge: Dict[str, Any] | None) -> List[float]:
        if not edge:
            return [0.0] * self.action_dim
        length_norm = self._normalize(get_edge_length_m(edge), 2000.0)
        congestion_norm = self._normalize(edge.get('congestion_coeff', 1.0), 5.0)
        availability = 1.0 if edge.get('is_available', True) else 0.0
        direction_scalar = self._direction_to_scalar(edge.get('direction'))
        width_norm = self._normalize(edge.get('max_width', 5.0), 10.0)
        return [
            length_norm,
            congestion_norm,
            availability,
            direction_scalar,
            width_norm
        ]

    def get_available_edges(self, node_id: str | None) -> List[Dict[str, Any]]:
        if not node_id:
            return []
        edges = [
            edge for edge in system_state.get('edges', [])
            if edge.get('start_node') == node_id and edge.get('is_available', True)
        ]
        return edges

    def build_transition_samples(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        samples: List[Dict[str, Any]] = []
        stats = {
            'total_records': len(records),
            'no_path_nodes': 0,
            'path_too_short': 0,
            'no_target_node': 0,
            'no_valid_edges': 0,
            'successful': 0,
            'edge_not_found_details': []  # 添加详细信息用于调试
        }
        
        for record in records:
            path_nodes = record.get('path_nodes')
            if not path_nodes:
                stats['no_path_nodes'] += 1
                continue
            if len(path_nodes) < 2:
                stats['path_too_short'] += 1
                continue
            target_node_id = record.get('target_node')
            if not target_node_id and isinstance(path_nodes[-1], dict):
                target_node_id = path_nodes[-1].get('id') or path_nodes[-1].get('target')
            if not target_node_id:
                stats['no_target_node'] += 1
                continue

            duration_penalty = float(record.get('duration_minutes') or 0.0)
            path_edges = self._normalize_path_edges(record)
            record_samples = 0
            missing_edges = []  # 记录找不到的边
            
            for idx in range(len(path_nodes) - 1):
                current_meta = path_nodes[idx]
                next_meta = path_nodes[idx + 1]
                current_node_id = str(current_meta.get('id') if isinstance(current_meta, dict) else current_meta).strip()
                next_node_id = str(next_meta.get('id') if isinstance(next_meta, dict) else next_meta).strip()
                if not current_node_id or not next_node_id:
                    continue
                
                edge = self._find_edge_in_path(current_node_id, next_node_id, path_edges)
                if not edge:
                    edge = self._find_edge_in_graph(current_node_id, next_node_id)
                if not edge:
                    missing_edges.append(f"{current_node_id}->{next_node_id}")
                    continue
                done = next_node_id == target_node_id
                reward = self._calculate_reward(edge, done, duration_penalty)
                sample = {
                    'state_vec': self.build_state_vector(current_node_id, target_node_id),
                    'action_vec': self.build_action_vector(edge),
                    'reward': reward,
                    'next_state_vec': self.build_state_vector(next_node_id, target_node_id),
                    'done': done,
                    'next_node': next_node_id,
                    'target_node': target_node_id
                }
                samples.append(sample)
                record_samples += 1
            
            if record_samples > 0:
                stats['successful'] += 1
            else:
                stats['no_valid_edges'] += 1
                if missing_edges:
                    stats['edge_not_found_details'].append({
                        'record_id': record.get('record_id', 'unknown'),
                        'start_node': record.get('start_node'),
                        'target_node': record.get('target_node'),
                        'missing_edges': missing_edges,
                        'path_nodes_count': len(path_nodes),
                        'path_edges_count': len(path_edges)
                    })
        
        # 如果没有生成样本，保存统计信息以便调试
        if not samples:
            import json
            from backend.utils.logger import logger
            
            # 记录详细的调试信息
            logger.warning(f"DQN训练数据问题：统计信息={json.dumps(stats, ensure_ascii=False)}")
            if stats.get('edge_not_found_details'):
                for detail in stats['edge_not_found_details']:
                    logger.warning(f"找不到边的记录详情：{json.dumps(detail, ensure_ascii=False)}")
            
            # 提供更详细的错误信息
            error_msg = (
                f'行驶时间数据库中缺少可用于训练的路径样本。\n'
                f'统计信息：{json.dumps(stats, ensure_ascii=False, indent=2)}\n'
                f'可能原因：\n'
                f'1. 记录中缺少 path_nodes 字段或路径节点数少于2个\n'
                f'2. 记录中缺少 target_node 字段\n'
                f'3. 路径中的节点在当前路网中找不到对应的边\n'
            )
            
            if stats.get('edge_not_found_details'):
                error_msg += f'\n找不到边的详细信息：\n'
                for detail in stats['edge_not_found_details']:
                    error_msg += f"  记录ID: {detail.get('record_id')}, 起点: {detail.get('start_node')}, 终点: {detail.get('target_node')}\n"
                    error_msg += f"  缺失的边: {', '.join(detail.get('missing_edges', []))}\n"
                    error_msg += f"  路径节点数: {detail.get('path_nodes_count')}, 路径边数: {detail.get('path_edges_count')}\n"
            
            error_msg += f'\n请检查：\n'
            error_msg += f'1. 导入的数据中的节点ID是否与当前路网中的节点ID匹配\n'
            error_msg += f'2. path_edges 中的边是否包含正确的 start_node 和 end_node 字段\n'
            error_msg += f'3. 当前路网是否包含这些节点和边\n'
            
            raise ValueError(error_msg)
        return samples

    def _normalize_path_edges(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        path_edges = record.get('path_edges') or []
        normalized_edges: List[Dict[str, Any]] = []
        for edge_meta in path_edges:
            if isinstance(edge_meta, dict):
                normalized_edges.append(edge_meta)
        return normalized_edges

    def _find_edge_in_path(self, start_node_id: str, end_node_id: str, path_edges: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """在路径边中查找边（支持多种格式）"""
        start_node_id = str(start_node_id).strip()
        end_node_id = str(end_node_id).strip()
        
        for edge_meta in path_edges:
            if not isinstance(edge_meta, dict):
                continue
            # 尝试多种字段名
            start = str(edge_meta.get('start_node') or edge_meta.get('start') or edge_meta.get('from') or '').strip()
            end = str(edge_meta.get('end_node') or edge_meta.get('end') or edge_meta.get('to') or '').strip()
            
            if start == start_node_id and end == end_node_id:
                edge_id = edge_meta.get('id') or edge_meta.get('edge_id')
                if edge_id:
                    # 尝试在当前路网中查找
                    edge = next((e for e in system_state.get('edges', []) if str(e.get('id', '')).strip() == str(edge_id).strip()), None)
                    if edge:
                        return edge
                # 如果找不到，返回边元数据本身（至少包含基本信息）
                return edge_meta
        return None

    def _find_edge_in_graph(self, start_node_id: str, end_node_id: str) -> Optional[Dict[str, Any]]:
        """在当前路网中查找边（支持双向匹配）"""
        start_node_id = str(start_node_id).strip()
        end_node_id = str(end_node_id).strip()
        
        edges = system_state.get('edges', [])
        
        # 首先尝试精确匹配（start_node -> end_node）
        for edge in edges:
            edge_start = str(edge.get('start_node', '')).strip()
            edge_end = str(edge.get('end_node', '')).strip()
            if edge_start == start_node_id and edge_end == end_node_id:
                return edge
        
        # 如果找不到，尝试反向匹配（双向道路）
        for edge in edges:
            edge_start = str(edge.get('start_node', '')).strip()
            edge_end = str(edge.get('end_node', '')).strip()
            direction = edge.get('direction', 'two-way')
            # 如果是双向道路，允许反向匹配
            if direction == 'two-way' and edge_start == end_node_id and edge_end == start_node_id:
                return edge
        
        return None

    def _calculate_reward(self, edge: Dict[str, Any], done: bool, duration_penalty: float) -> float:
        length_penalty = get_edge_length_m(edge) / 100.0
        congestion_penalty = edge.get('congestion_coeff', 1.0)
        reward = - (length_penalty + congestion_penalty)
        if done:
            reward += max(1.0, 10.0 - duration_penalty * 0.2)
        return reward


if nn is not None and torch is not None:

    class StateActionQNetwork(nn.Module):  # type: ignore[misc]
        """简单的前馈神经网络，用于估计 Q(s, a)"""

        def __init__(self, input_dim: int, hidden_dim: int = 128):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, 1)
            )

        def forward(self, x):
            return self.net(x)


    class DeepQLearningPlanner:
        """封装 DQN 逻辑（经验样本来自行驶时间数据库）"""

        def __init__(self, environment: RoadEnvironment, hidden_dim: int = 128, lr: float = 1e-3, gamma: float = 0.95):
            self.env = environment
            self.gamma = gamma
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            input_dim = self.env.state_dim + self.env.action_dim
            self.model = StateActionQNetwork(input_dim, hidden_dim).to(self.device)
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
            self.loss_fn = nn.MSELoss()
            self.is_trained = False

        def train_from_records(
            self,
            records: List[Dict[str, Any]],
            epochs: int = 5,
            batch_size: int = 64,
            gamma: Optional[float] = None
        ) -> Dict[str, Any]:
            if gamma is not None:
                self.gamma = float(gamma)
            samples = self.env.build_transition_samples(records)
            if not samples:
                raise ValueError('行驶时间数据库中缺少可用于训练的路径样本，请先收集更多带 path_nodes 的记录')
            avg_losses: List[float] = []

            for epoch in range(max(1, epochs)):
                random.shuffle(samples)
                epoch_losses: List[float] = []
                for i in range(0, len(samples), max(1, batch_size)):
                    batch = samples[i:i + batch_size]
                    batch_loss = self._train_batch(batch)
                    epoch_losses.append(batch_loss)
                if epoch_losses:
                    avg_losses.append(sum(epoch_losses) / len(epoch_losses))

            self.is_trained = True
            return {
                'epochs': epochs,
                'samples': len(samples),
                'avg_loss': sum(avg_losses) / len(avg_losses) if avg_losses else 0.0,
                'device': str(self.device),
                'gamma': self.gamma
            }

        def _train_batch(self, batch: List[Dict[str, Any]]) -> float:
            batch_losses: List[torch.Tensor] = []
            for item in batch:
                state_action = torch.tensor(
                    item['state_vec'] + item['action_vec'],
                    dtype=torch.float32,
                    device=self.device
                )
                q_pred = self.model(state_action).squeeze()
                target_value = item['reward']
                if not item['done']:
                    next_actions = self.env.get_available_edges(item['next_node'])
                    if next_actions:
                        next_q_values = []
                        for next_edge in next_actions:
                            sa_next = torch.tensor(
                                item['next_state_vec'] + self.env.build_action_vector(next_edge),
                                dtype=torch.float32,
                                device=self.device
                            )
                            next_q = self.model(sa_next)
                            next_q_values.append(next_q)
                        if next_q_values:
                            max_next_q = torch.max(torch.stack(next_q_values))
                            target_value += self.gamma * float(max_next_q.item())
                target_tensor = torch.tensor([target_value], dtype=torch.float32, device=self.device)
                loss = self.loss_fn(q_pred.view_as(target_tensor), target_tensor)
                batch_losses.append(loss)

            if not batch_losses:
                return 0.0
            batch_loss = torch.stack(batch_losses).mean()
            self.optimizer.zero_grad()
            batch_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=2.0)
            self.optimizer.step()
            return float(batch_loss.item())

        def predict_route(self, start_node_id: str, target_node_id: str, epsilon: float = 0.0, max_steps: int = 200) -> List[Dict[str, Any]]:
            if not self.is_trained:
                raise RuntimeError('DQN 尚未训练，请先调用 /api/dqn/train')
            current_node = start_node_id
            route_edges: List[Dict[str, Any]] = []
            visited_nodes = set()

            for _ in range(max_steps):
                if current_node == target_node_id:
                    break
                visited_nodes.add(current_node)
                available_edges = self.env.get_available_edges(current_node)
                if not available_edges:
                    break

                if random.random() < max(0.0, epsilon):
                    chosen_edge = random.choice(available_edges)
                else:
                    chosen_edge = self._select_best_edge(current_node, target_node_id, available_edges)

                if not chosen_edge:
                    break

                route_edges.append({
                    'id': chosen_edge.get('id'),
                    'start_node': chosen_edge.get('start_node'),
                    'end_node': chosen_edge.get('end_node'),
                    'length_m': get_edge_length_m(chosen_edge),
                    'congestion_coeff': chosen_edge.get('congestion_coeff', 1.0)
                })
                current_node = chosen_edge.get('end_node')
                if current_node in visited_nodes:
                    break

            return route_edges

        def _select_best_edge(
            self,
            current_node_id: str,
            target_node_id: str,
            edges: List[Dict[str, Any]]
        ) -> Optional[Dict[str, Any]]:
            best_edge: Optional[Dict[str, Any]] = None
            best_q: Optional[float] = None
            state_vec = self.env.build_state_vector(current_node_id, target_node_id)
            for edge in edges:
                state_action_vec = torch.tensor(
                    state_vec + self.env.build_action_vector(edge),
                    dtype=torch.float32,
                    device=self.device
                )
                q_value = float(self.model(state_action_vec).item())
                if best_q is None or q_value > best_q:
                    best_q = q_value
                    best_edge = edge
            return best_edge

else:

    StateActionQNetwork = None  # type: ignore

    class DeepQLearningPlanner:  # type: ignore
        """占位符：在未安装 PyTorch 时阻止实例化"""

        def __init__(self, *_args, **_kwargs):
            raise RuntimeError('当前环境未安装 PyTorch，无法启用 DQN 功能。请先运行 pip install torch')


# 全局 DQN 规划器实例
_dqn_planner = None


def ensure_dqn_planner() -> DeepQLearningPlanner:
    """懒加载 DQN 规划器（支持运行时检测 PyTorch）"""
    global _dqn_planner, torch, nn
    # 运行时检测 PyTorch 是否可用
    if torch is None or nn is None:
        try:
            import torch as _torch
            from torch import nn as _nn
            torch = _torch
            nn = _nn
            logger.info("PyTorch 在 dqn_service 中运行时检测成功")
        except ImportError:
            raise RuntimeError('当前环境未安装 PyTorch，无法启用 DQN 功能。如果已安装，请重启应用。')
    if _dqn_planner is None:
        environment = RoadEnvironment(system_state.get_state() if hasattr(system_state, 'get_state') else system_state)
        _dqn_planner = DeepQLearningPlanner(environment)
    return _dqn_planner


def get_dqn_planner() -> Optional[DeepQLearningPlanner]:
    """获取 DQN 规划器实例（如果已创建）"""
    return _dqn_planner

