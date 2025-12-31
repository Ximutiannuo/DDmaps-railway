/**
 * API 通信模块 (TypeScript 版本)
 */

import { ApiResponse, Node, Edge, Vehicle, MonitorData, DispatchStatus } from './types';

// API 基础 URL
function getApiBase(): string {
    const origin = window.location.origin;
    if (origin === 'null' || origin.startsWith('file://')) {
        return 'http://localhost:5000/api';
    }
    return `${origin}/api`;
}

const API_BASE = getApiBase();

/**
 * 统一的 API 调用函数
 */
async function apiCall<T = any>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions: RequestInit = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const config: RequestInit = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {}),
        },
    };

    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            const errorText = await response.text();
            let errorData: { message?: string };
            try {
                errorData = JSON.parse(errorText);
            } catch {
                errorData = { message: errorText || `HTTP ${response.status}: ${response.statusText}` };
            }
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data: T = await response.json();
        return data;
    } catch (error) {
        console.error(`API 调用失败 [${endpoint}]:`, error);
        throw error;
    }
}

/**
 * 获取路网数据
 */
export async function fetchRoads(): Promise<{ nodes: Node[]; edges: Edge[] }> {
    const result = await apiCall<ApiResponse<{ nodes: Node[]; edges: Edge[] }>>('/roads');
    if (result.success && result.data?.nodes && result.data?.edges) {
        return {
            nodes: result.data.nodes,
            edges: result.data.edges,
        };
    }
    throw new Error(result.message || '获取路网数据失败');
}

/**
 * 获取车辆列表
 */
export async function fetchVehicles(): Promise<Vehicle[]> {
    const result = await apiCall<ApiResponse<{ vehicles: Vehicle[] }>>('/vehicles');
    if (result.success && result.data?.vehicles) {
        return result.data.vehicles;
    }
    return [];
}

/**
 * 获取监控数据
 */
export async function fetchMonitorData(): Promise<MonitorData> {
    const result = await apiCall<ApiResponse<MonitorData>>('/monitor');
    if (result.success && result.data) {
        return result.data;
    }
    return {};
}

/**
 * 启动调度
 */
export async function startDispatch(): Promise<boolean> {
    const result = await apiCall<ApiResponse>('/dispatch/start', {
        method: 'POST',
    });
    return result.success === true;
}

/**
 * 停止调度
 */
export async function stopDispatch(): Promise<boolean> {
    const result = await apiCall<ApiResponse>('/dispatch/stop', {
        method: 'POST',
    });
    return result.success === true;
}

/**
 * 获取调度状态
 */
export async function getDispatchStatus(): Promise<DispatchStatus> {
    try {
        return await apiCall<DispatchStatus>('/dispatch/status');
    } catch (error) {
        console.error('获取调度状态失败:', error);
        return { success: false, dispatch_running: false };
    }
}

export { API_BASE, apiCall };

