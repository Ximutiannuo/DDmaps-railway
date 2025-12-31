/**
 * API 通信模块
 * 处理所有与后端的 HTTP 请求
 */

// API 基础 URL
function getApiBase() {
    const origin = window.location.origin;
    // 如果是 file:// 协议，使用默认的 localhost
    if (origin === 'null' || origin.startsWith('file://')) {
        return 'http://localhost:5000/api';
    }
    return origin + '/api';
}

const API_BASE = getApiBase();

/**
 * 统一的 API 调用函数
 * @param {string} endpoint - API 端点（不需要 /api 前缀）
 * @param {Object} options - 请求选项（method, body, headers 等）
 * @returns {Promise<Object>} 响应数据
 */
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };

    // 处理 cache 选项：如果 cache 是 false，转换为 'no-cache'，否则使用默认值或用户指定的值
    let cacheOption = 'default';
    if (options.cache === false) {
        cacheOption = 'no-cache';
    } else if (options.cache && typeof options.cache === 'string') {
        // 验证是否是有效的 cache 值
        const validCacheValues = ['default', 'no-store', 'reload', 'no-cache', 'force-cache', 'only-if-cached'];
        if (validCacheValues.includes(options.cache)) {
            cacheOption = options.cache;
        }
    }

    // 分离 fetch 选项和其他自定义选项
    const { cache, silent, ...fetchOptions } = options;

    const config = {
        ...defaultOptions,
        ...fetchOptions,
        cache: cacheOption, // 使用处理后的 cache 选项
        headers: {
            ...defaultOptions.headers,
            ...(fetchOptions.headers || {}),
        },
    };

    // 如果有 body，转换为 JSON
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }

    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            const errorText = await response.text();
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch {
                errorData = { message: errorText || `HTTP ${response.status}: ${response.statusText}` };
            }
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        if (!silent) { // 如果 silent 为 true，不输出错误
            console.error(`API 调用失败 [${endpoint}]:`, error);
        }
        throw error;
    }
}

/**
 * 获取路网数据（节点和道路）
 * @returns {Promise<Object>} 包含 nodes 和 edges 的对象
 */
async function fetchRoads() {
    try {
        const result = await apiCall('/roads');
        if (result.success && result.nodes && result.edges) {
            return {
                nodes: result.nodes,
                edges: result.edges,
            };
        }
        throw new Error(result.message || '获取路网数据失败');
    } catch (error) {
        console.error('获取路网数据失败:', error);
        throw error;
    }
}

/**
 * 获取车辆列表
 * @returns {Promise<Array>} 车辆数组
 */
async function fetchVehicles() {
    try {
        const result = await apiCall('/vehicles');
        if (result.success && result.vehicles) {
            return result.vehicles;
        }
        return [];
    } catch (error) {
        console.error('获取车辆列表失败:', error);
        return [];
    }
}

/**
 * 获取监控数据
 * @returns {Promise<Object>} 监控数据对象
 */
async function fetchMonitorData() {
    try {
        const result = await apiCall('/monitor');
        if (result.success && result.data) {
            return result.data;
        }
        return {};
    } catch (error) {
        console.error('获取监控数据失败:', error);
        return {};
    }
}

/**
 * 获取车辆类型
 * @returns {Promise<Object>} 车辆类型对象
 */
async function fetchVehicleTypes() {
    try {
        const result = await apiCall('/vehicle-types');
        if (result.success && result.types) {
            return result.types;
        }
        return {};
    } catch (error) {
        console.error('获取车辆类型失败:', error);
        return {};
    }
}

/**
 * 获取司机信息
 * @returns {Promise<Array>} 司机数组
 */
async function fetchDrivers() {
    try {
        const result = await apiCall('/drivers');
        if (result.success && result.drivers) {
            return result.drivers;
        }
        return [];
    } catch (error) {
        console.error('获取司机信息失败:', error);
        return [];
    }
}

/**
 * 获取地图背景
 * @returns {Promise<string|null>} 地图背景 URL 或 null
 */
async function fetchMapBackground() {
    try {
        const result = await apiCall('/map-background');
        if (result.success && result.url) {
            return result.url;
        }
        return null;
    } catch (error) {
        console.error('获取地图背景失败:', error);
        return null;
    }
}

/**
 * 启动调度
 * @returns {Promise<boolean>} 是否成功
 */
async function startDispatch() {
    try {
        const result = await apiCall('/dispatch/start', {
            method: 'POST',
        });
        return result.success === true;
    } catch (error) {
        console.error('启动调度失败:', error);
        return false;
    }
}

/**
 * 停止调度
 * @returns {Promise<boolean>} 是否成功
 */
async function stopDispatch() {
    try {
        const result = await apiCall('/dispatch/stop', {
            method: 'POST',
        });
        return result.success === true;
    } catch (error) {
        console.error('停止调度失败:', error);
        return false;
    }
}

/**
 * 获取调度状态
 * @returns {Promise<Object>} 调度状态对象
 */
async function getDispatchStatus() {
    try {
        const result = await apiCall('/dispatch/status');
        return result;
    } catch (error) {
        console.error('获取调度状态失败:', error);
        return { success: false, dispatch_running: false };
    }
}

// 导出函数（支持浏览器和 Node.js）
if (typeof window !== 'undefined') {
    // 浏览器环境：暴露到全局作用域
    window.TrafficAPI = {
        API_BASE,
        apiCall,
        fetchRoads,
        fetchVehicles,
        fetchMonitorData,
        fetchVehicleTypes,
        fetchDrivers,
        fetchMapBackground,
        startDispatch,
        stopDispatch,
        getDispatchStatus,
    };
    // 为了兼容，也暴露到全局
    // 使用 Object.defineProperty 避免重复声明冲突
    if (!window.hasOwnProperty('API_BASE')) {
        Object.defineProperty(window, 'API_BASE', {
            value: API_BASE,
            writable: false,
            configurable: true,
            enumerable: true
        });
    }
    
    if (!window.hasOwnProperty('apiCall')) {
        Object.defineProperty(window, 'apiCall', {
            value: apiCall,
            writable: false,
            configurable: true,
            enumerable: true
        });
    }
}

if (typeof module !== 'undefined' && module.exports) {
    // Node.js 环境
    module.exports = {
        API_BASE,
        apiCall,
        fetchRoads,
        fetchVehicles,
        fetchMonitorData,
        fetchVehicleTypes,
        fetchDrivers,
        fetchMapBackground,
        startDispatch,
        stopDispatch,
        getDispatchStatus,
    };
}

