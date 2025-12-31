/**
 * TypeScript 类型定义文件
 */

// 节点类型
export interface Node {
    id: string;
    x: number;
    y: number;
    type?: 'entrance' | 'crossroad' | 'work-area' | 'start';
    name?: string;
}

// 道路类型
export interface Edge {
    id: string;
    start: string;
    end: string;
    length?: number;
    direction?: string;
    congestion_coeff?: number;
}

// 车辆类型
export interface Vehicle {
    id: string;
    type: string;
    driver_id?: string;
    driver_name?: string;
    status: 'idle' | 'moving' | 'arrived' | 'waiting';
    current_node?: string;
    target_node?: string;
    path_nodes?: string[];
    efficiency_score?: number;
    x?: number;
    y?: number;
}

// 监控数据类型
export interface MonitorData {
    total_vehicles?: number;
    moving_vehicles?: number;
    idle_vehicles?: number;
    arrived_vehicles?: number;
    average_efficiency?: number;
    total_trips?: number;
    completed_trips?: number;
}

// API 响应类型
export interface ApiResponse<T = any> {
    success: boolean;
    message?: string;
    data?: T;
    [key: string]: any;
}

// 调度状态类型
export interface DispatchStatus {
    success: boolean;
    dispatch_running: boolean;
    message?: string;
}

// 图表数据类型
export interface ChartData {
    labels: string[];
    datasets: Array<{
        label?: string;
        data: number[];
        [key: string]: any;
    }>;
}

// 错误类型
export interface AppError {
    type: 'network' | 'validation' | 'server' | 'unknown';
    message: string;
    details?: any;
}

