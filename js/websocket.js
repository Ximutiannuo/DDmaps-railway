/**
 * WebSocket 通信模块
 * 处理实时数据推送
 */

// 使用全局变量，避免重复声明
if (typeof window !== 'undefined' && !window.__traffic_websocket_socket) {
    window.__traffic_websocket_socket = null;
    window.__traffic_websocket_connected = false;
}

let socket = window.__traffic_websocket_socket;
let websocketConnected = window.__traffic_websocket_connected;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
let isInitializing = false; // 防止重复初始化
let reconnectTimer = null; // 重连定时器
let lastReconnectTime = 0; // 上次重连时间
const MIN_RECONNECT_INTERVAL = 5000; // 最小重连间隔（5秒）

// HTTP 轮询相关变量
let pollingInterval = null; // 轮询定时器
let pollingCallback = null; // 轮询回调函数
const POLLING_INTERVAL_ACTIVE_MS = 500; // 活动时轮询间隔（500毫秒）
const POLLING_INTERVAL_IDLE_MS = 2000; // 空闲时轮询间隔（2秒）
let currentPollingInterval = POLLING_INTERVAL_ACTIVE_MS; // 当前使用的轮询间隔
let lastActivityTime = Date.now(); // 上次活动时间
const IDLE_THRESHOLD_MS = 5000; // 5秒无活动视为空闲

// 连接健康检查相关变量
let connectionHealthCheck = null; // 连接健康检查定时器
const CONNECTION_CHECK_INTERVAL = 30000; // 连接健康检查间隔（30秒）
let wsStatus = { available: true, onPythonAnywhere: false }; // 保存 WebSocket 状态，供健康检查使用

// 同步函数，确保变量同步到 window 对象
function syncSocketVars() {
    if (typeof window !== 'undefined') {
        // 同步到 window 对象，供 HTML 代码访问
        window.__traffic_websocket_socket = socket;
        window.__traffic_websocket_connected = websocketConnected;
    }
}

/**
 * 检测 WebSocket 是否可用（带重试机制）
 * @returns {Promise<{available: boolean, onPythonAnywhere: boolean}>} WebSocket 状态信息
 */
async function checkWebSocketAvailable(retryCount = 0, maxRetries = 3) {
    try {
        const apiBase = window.API_BASE || (window.location.origin + '/api');
        const url = `${apiBase}/websocket-status`;
        
        // 添加超时控制
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                // 如果返回非200状态，在局域网环境下默认允许尝试连接
                if (retryCount < maxRetries) {
                    // 延迟后重试
                    await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
                    return checkWebSocketAvailable(retryCount + 1, maxRetries);
                }
                // 重试次数用尽，在局域网环境下默认允许尝试
                console.debug('WebSocket 状态检测返回非 200，将尝试连接');
                return {
                    available: true, // 允许尝试连接
                    onPythonAnywhere: false
                };
            }
            
            const data = await response.json();
            const available = data.success && data.websocket_enabled === true;
            
            // 如果检测到不可用，但在局域网环境下，允许重试一次
            if (!available && !data.on_pythonanywhere && retryCount < maxRetries) {
                console.debug(`WebSocket 检测为不可用，${1000 * (retryCount + 1)}ms 后重试...`);
                await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
                return checkWebSocketAvailable(retryCount + 1, maxRetries);
            }
            
            return {
                available: available,
                onPythonAnywhere: data.on_pythonanywhere === true
            };
        } catch (fetchError) {
            clearTimeout(timeoutId);
            // 网络错误或超时，在局域网环境下允许重试
            if (retryCount < maxRetries) {
                console.debug(`WebSocket 状态检测失败，${1000 * (retryCount + 1)}ms 后重试:`, fetchError.message);
                await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
                return checkWebSocketAvailable(retryCount + 1, maxRetries);
            }
            // 重试次数用尽，在局域网环境下默认允许尝试连接
            console.debug('WebSocket 状态检测失败（可能是后端还在初始化），将尝试连接');
            return {
                available: true, // 允许尝试连接
                onPythonAnywhere: false
            };
        }
    } catch (error) {
        // 其他错误，在局域网环境下默认允许尝试连接
        console.debug('WebSocket 状态检测异常，将尝试连接:', error.message);
        return {
            available: true, // 允许尝试连接
            onPythonAnywhere: false
        };
    }
}

/**
 * 初始化 WebSocket 连接
 * @param {Function} onVehicleUpdate - 车辆更新回调函数
 * @param {Function} onConnect - 连接成功回调
 * @param {Function} onDisconnect - 断开连接回调
 */
async function initWebSocket(onVehicleUpdate, onConnect, onDisconnect) {
    // 先检测 WebSocket 是否可用（带重试机制，避免初始化时序问题）
    let wsStatus = { available: true, onPythonAnywhere: false }; // 默认允许尝试连接
    try {
        wsStatus = await checkWebSocketAvailable();
    } catch (error) {
        console.warn('⚠️ WebSocket 状态检测失败，将尝试连接:', error);
        // 检测失败时，默认允许尝试连接（让 Socket.IO 自动处理）
        wsStatus = { available: true, onPythonAnywhere: false };
    }
    
    // 如果在 PythonAnywhere 环境，直接使用轮询，不尝试连接 Socket.IO（避免 WebSocket 连接错误）
    if (wsStatus.onPythonAnywhere) {
        console.log('ℹ️ 检测到 PythonAnywhere 环境，直接使用 HTTP 轮询模式（不支持 WebSocket）');
        startPolling(onVehicleUpdate);
        if (onConnect) onConnect(); // 调用连接回调，表示已"连接"（轮询模式）
        return;
    }
    
    // 如果不在 PythonAnywhere，直接尝试连接 Socket.IO（让 Socket.IO 自动处理降级）
    // 即使检测显示不可用，也尝试连接（可能是初始化时序问题）
    if (wsStatus.available) {
        console.log('✅ 检测到 WebSocket 可用，正在连接...');
    } else {
        console.log('🔌 尝试连接 WebSocket（将自动降级到轮询）...');
    }
    
    // 检查 Socket.IO 是否已加载
    if (typeof io === 'undefined') {
        console.warn('⚠️ Socket.IO 库未加载，WebSocket 功能不可用，使用 HTTP 轮询');
        startPolling(onVehicleUpdate);
        if (onConnect) onConnect();
        return;
    }

    // 防止重复初始化
    if (isInitializing) {
        console.warn('⚠️ WebSocket 正在初始化中，跳过重复调用');
        return;
    }

    // 如果已有连接且正在连接中，先断开
    if (socket && socket.connected) {
        console.log('ℹ️ 已有活跃连接，先断开旧连接');
        socket.disconnect();
        socket = null;
    }

    // 清除之前的重连定时器
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    // 检查重连间隔
    const now = Date.now();
    if (now - lastReconnectTime < MIN_RECONNECT_INTERVAL) {
        const waitTime = MIN_RECONNECT_INTERVAL - (now - lastReconnectTime);
        console.log(`⏳ 距离上次重连时间过短，等待 ${waitTime}ms 后重连`);
        reconnectTimer = setTimeout(() => {
            initWebSocket(onVehicleUpdate, onConnect, onDisconnect);
        }, waitTime);
        return;
    }

    isInitializing = true;
    lastReconnectTime = now;

    try {
        const wsUrl = window.location.origin;
        console.log(`🔌 正在连接 WebSocket: ${wsUrl}`);
        
        // 先断开旧连接（如果存在）
        if (socket) {
            socket.removeAllListeners();
            socket.disconnect();
            socket = null;
        }
        
        // 根据检测结果决定传输方式
        // 如果在 PythonAnywhere 环境，强制只使用轮询，不尝试 WebSocket
        // 如果检测到 WebSocket 可用，优先使用 WebSocket，否则只使用轮询
        const transports = wsStatus.onPythonAnywhere ? ['polling'] : (wsStatus.available ? ['websocket', 'polling'] : ['polling']);
        
        // 保存 wsStatus 到模块级变量，供健康检查使用
        const currentWsStatus = wsStatus;
        
        socket = io(wsUrl, {
            transports: transports,  // 根据环境选择传输方式
            reconnection: !wsStatus.onPythonAnywhere, // PythonAnywhere 上不自动重连（因为只使用轮询）
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000, // 减少最大重连延迟到5秒，更快恢复连接
            reconnectionAttempts: wsStatus.onPythonAnywhere ? 0 : Infinity, // PythonAnywhere 上不重连
            timeout: 20000, // 减少到20秒，更快检测连接问题
            forceNew: false, // 复用连接
            autoConnect: true,
            upgrade: !wsStatus.onPythonAnywhere && wsStatus.available,  // PythonAnywhere 上不允许升级到 WebSocket
            rememberUpgrade: !wsStatus.onPythonAnywhere,  // PythonAnywhere 上不记住升级状态
            // 添加 ping 配置，与后端匹配
            pingTimeout: 120000,  // 2分钟（与后端 ping_timeout 匹配）
            pingInterval: 30000   // 30秒（与后端 ping_interval 匹配）
        });

        socket.on('connect', () => {
            isInitializing = false;
            websocketConnected = true;
            reconnectAttempts = 0;
            syncSocketVars(); // 同步变量
            console.log('✅ WebSocket 已连接');
            updateConnectionStatus(true);
            // WebSocket 连接成功后，停止轮询（如果正在轮询）
            if (pollingInterval) {
                console.log('✅ WebSocket 已连接，停止轮询模式');
                stopPolling();
            }
            // 启动连接健康检查（仅在非 PythonAnywhere 环境）
            if (!currentWsStatus.onPythonAnywhere) {
                startConnectionHealthCheck();
            }
            if (onConnect) onConnect();
        });

        socket.on('disconnect', (reason) => {
            isInitializing = false;
            websocketConnected = false;
            syncSocketVars(); // 同步变量
            console.warn('⚠️ WebSocket 已断开:', reason);
            updateConnectionStatus(false);
            
            // 如果是因为 400 错误或会话问题，强制重新连接
            if (reason === 'transport close' || reason === 'ping timeout' || reason === 'transport error') {
                console.log('🔄 检测到传输错误，将重新建立连接...');
                // 延迟后重新初始化连接，清除旧的会话
                setTimeout(() => {
                    if (socket && !socket.connected) {
                        console.log('🔄 重新初始化 WebSocket 连接...');
                        socket.removeAllListeners();
                        socket.disconnect();
                        socket = null;
                        // 重新初始化连接
                        initWebSocket(onVehicleUpdate, onConnect, onDisconnect);
                    }
                }, 2000);
            } else if (reason === 'io server disconnect') {
                // 服务器主动断开，可能是服务器重启或维护
                console.log('🔄 服务器主动断开，Socket.IO 将自动重连...');
            } else {
                // 其他断开原因（网络问题、超时等），Socket.IO 会自动重连
                console.log('🔄 连接断开，Socket.IO 将自动重连...');
            }
            
            // 如果 WebSocket 断开，启动轮询作为备用，确保数据同步
            if (!pollingInterval && onVehicleUpdate) {
                console.log('🔄 WebSocket 断开，启动轮询模式作为备用...');
                startPolling(onVehicleUpdate);
            }
            
            if (onDisconnect) onDisconnect();
        });

        socket.on('vehicle_update', (data) => {
            if (data && onVehicleUpdate) {
                onVehicleUpdate(data);
            }
        });

        socket.on('connect_error', (error) => {
            isInitializing = false;
            // 检查是否是 400 错误或会话问题
            const errorMsg = error.message || error.toString();
            if (errorMsg.includes('400') || errorMsg.includes('BAD REQUEST') || errorMsg.includes('Invalid session')) {
                console.warn('⚠️ WebSocket 连接错误（会话无效），将重新建立连接:', errorMsg);
                // 清除旧连接，重新初始化
                setTimeout(() => {
                    if (socket && !socket.connected) {
                        console.log('🔄 清除旧会话，重新初始化连接...');
                        socket.removeAllListeners();
                        socket.disconnect();
                        socket = null;
                        // 重新初始化连接
                        initWebSocket(onVehicleUpdate, onConnect, onDisconnect);
                    }
                }, 2000);
            } else {
                // 其他错误，让 Socket.IO 自动重连
                console.debug('WebSocket 连接错误（将自动重连）:', errorMsg);
            }
        });
        
        // 监听重连成功事件
        socket.on('reconnect', (attemptNumber) => {
            isInitializing = false;
            console.log(`✅ WebSocket 重连成功 (尝试 ${attemptNumber} 次)`);
            reconnectAttempts = 0;
            websocketConnected = true;
            syncSocketVars();
            updateConnectionStatus(true);
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            if (onConnect) onConnect();
        });
        
        // 监听重连尝试事件
        socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 WebSocket 重连尝试 ${attemptNumber}/${MAX_RECONNECT_ATTEMPTS}...`);
        });
        
        // 监听重连失败事件（由于设置了无限重连，这个事件理论上不会触发）
        socket.on('reconnect_failed', () => {
            isInitializing = false;
            console.warn('⚠️ WebSocket 重连遇到问题，但将继续尝试重连');
            updateConnectionStatus(false);
            // 不切换到轮询，继续让 Socket.IO 尝试重连
        });

        // 请求初始数据
        socket.on('connected', () => {
            socket.emit('request_update');
        });

        // 初始化页面可见性和网络状态监听（仅在非 PythonAnywhere 环境）
        if (!currentWsStatus.onPythonAnywhere) {
            setupConnectionMonitoring();
        }

    } catch (error) {
        isInitializing = false;
        console.error('初始化 WebSocket 失败:', error);
        websocketConnected = false;
        syncSocketVars(); // 同步变量
        
        // 清理资源
        if (socket) {
            try {
                socket.removeAllListeners();
                socket.disconnect();
            } catch (e) {
                // 忽略清理错误
            }
            socket = null;
        }
        
        // 如果重连次数未达上限，延迟重连
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            const delay = Math.min(5000 * (reconnectAttempts + 1), 30000);
            reconnectTimer = setTimeout(() => {
                reconnectAttempts++;
                initWebSocket(onVehicleUpdate, onConnect, onDisconnect);
            }, delay);
        }
    }
}

/**
 * 启动连接健康检查
 * 定期检查连接状态，断开时主动重连
 */
function startConnectionHealthCheck() {
    // 如果已经在检查，不启动
    if (connectionHealthCheck) return;
    
    // 清除旧的检查器（如果存在）
    stopConnectionHealthCheck();
    
    connectionHealthCheck = setInterval(() => {
        // 检查连接状态，如果断开则尝试重连
        if (socket && !socket.connected) {
            console.log('🔄 健康检查：检测到连接断开，尝试重连...');
            socket.connect();
        }
    }, CONNECTION_CHECK_INTERVAL);
    
    console.log('✅ 已启动连接健康检查（每30秒检查一次）');
}

/**
 * 停止连接健康检查
 */
function stopConnectionHealthCheck() {
    if (connectionHealthCheck) {
        clearInterval(connectionHealthCheck);
        connectionHealthCheck = null;
        console.log('⏹️ 已停止连接健康检查');
    }
}

/**
 * 设置连接监控（页面可见性、网络状态等）
 */
function setupConnectionMonitoring() {
    if (typeof document === 'undefined') return;
    
    // 页面可见性检测 - 当标签页恢复时检查连接
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && socket && !socket.connected) {
            console.log('🔄 页面恢复可见，检查 WebSocket 连接...');
            socket.connect();
        }
    });

    // 窗口焦点检测 - 当窗口获得焦点时检查连接
    window.addEventListener('focus', () => {
        if (socket && !socket.connected) {
            console.log('🔄 窗口获得焦点，检查 WebSocket 连接...');
            socket.connect();
        }
    });

    // 网络状态监听 - 当网络恢复时检查连接
    if (typeof navigator !== 'undefined' && 'onLine' in navigator) {
        window.addEventListener('online', () => {
            console.log('🔄 网络已恢复，检查 WebSocket 连接...');
            if (socket && !socket.connected) {
                socket.connect();
            }
        });

        window.addEventListener('offline', () => {
            console.warn('⚠️ 网络已断开');
        });
    }
    
    console.log('✅ 已设置连接监控（页面可见性、网络状态）');
}

/**
 * 断开 WebSocket 连接
 */
function disconnectWebSocket() {
    // 停止轮询
    stopPolling();
    
    // 停止健康检查
    stopConnectionHealthCheck();
    
    // 清除重连定时器
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    
    isInitializing = false;
    reconnectAttempts = 0;
    
    if (socket) {
        try {
            socket.removeAllListeners(); // 移除所有监听器，防止内存泄漏
            socket.disconnect();
        } catch (e) {
            console.warn('断开 WebSocket 连接时出错:', e);
        }
        socket = null;
    }
    
    websocketConnected = false;
    syncSocketVars(); // 同步变量
}

/**
 * 请求数据更新
 */
function requestUpdate() {
    if (socket && websocketConnected) {
        socket.emit('request_update');
    }
}

/**
 * 更新连接状态显示
 * @param {boolean} connected - 是否已连接
 */
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('ws-status-indicator');
    if (indicator) {
        indicator.textContent = connected ? '🟢 实时连接' : '🔴 轮询模式';
        indicator.style.color = connected ? '#27ae60' : '#e74c3c';
    }
}

/**
 * 根据系统活动状态调整轮询间隔（智能轮询）
 */
function adjustPollingInterval() {
    const timeSinceLastActivity = Date.now() - lastActivityTime;
    const newInterval = timeSinceLastActivity > IDLE_THRESHOLD_MS 
        ? POLLING_INTERVAL_IDLE_MS 
        : POLLING_INTERVAL_ACTIVE_MS;
    
    // 如果间隔发生变化，重启轮询
    if (newInterval !== currentPollingInterval && pollingInterval && pollingCallback) {
        const wasActive = currentPollingInterval === POLLING_INTERVAL_ACTIVE_MS;
        currentPollingInterval = newInterval;
        
        // 清除旧定时器
        clearInterval(pollingInterval);
        
        // 创建新定时器
        pollingInterval = setInterval(() => {
            fetchMonitorData();
            adjustPollingInterval(); // 每次轮询后检查是否需要调整间隔
        }, currentPollingInterval);
        
        console.log(`🔄 轮询间隔已调整为 ${currentPollingInterval}ms (${currentPollingInterval === POLLING_INTERVAL_ACTIVE_MS ? '活动' : '空闲'}模式)`);
    } else if (newInterval !== currentPollingInterval) {
        // 仅更新间隔值，不重启（避免频繁重启）
        currentPollingInterval = newInterval;
    }
}

/**
 * 启动 HTTP 轮询（WebSocket 不可用时的降级方案）
 * @param {Function} onVehicleUpdate - 车辆更新回调函数
 */
function startPolling(onVehicleUpdate) {
    // 如果已经在轮询，先停止
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    
    // 如果 WebSocket 已连接，不启动轮询
    if (socket && socket.connected) {
        console.log('ℹ️ WebSocket 已连接，不需要启动轮询');
        return;
    }
    
    pollingCallback = onVehicleUpdate;
    lastActivityTime = Date.now(); // 初始化活动时间
    currentPollingInterval = POLLING_INTERVAL_ACTIVE_MS; // 初始使用活动间隔
    
    // 延迟执行第一次，避免立即请求
    setTimeout(() => {
        fetchMonitorData();
    }, 500);
    
    // 设置定时轮询（初始使用活动间隔）
    pollingInterval = setInterval(() => {
        fetchMonitorData();
        adjustPollingInterval(); // 每次轮询后检查是否需要调整间隔
    }, currentPollingInterval);
    
    console.log(`🔄 已启动 HTTP 轮询模式（智能间隔：活动时 ${POLLING_INTERVAL_ACTIVE_MS}ms，空闲时 ${POLLING_INTERVAL_IDLE_MS}ms）`);
    updateConnectionStatus(false);
}

/**
 * 停止 HTTP 轮询
 */
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    pollingCallback = null;
    console.log('⏹️ 已停止 HTTP 轮询');
}

/**
 * 从 API 获取监控数据（用于轮询）
 */
async function fetchMonitorData() {
    try {
        // 使用 API_BASE 确保 URL 正确
        const apiBase = window.API_BASE || (window.location.origin + '/api');
        const url = `${apiBase}/monitor`;
        
        // 使用 AbortController 替代 AbortSignal.timeout（更好的兼容性）
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            // 检查响应状态
            if (!response.ok) {
                // 400 错误通常是请求格式问题，记录详细信息但不中断轮询
                if (response.status === 400) {
                    try {
                        const errorText = await response.text();
                        console.warn('轮询获取监控数据返回 400 错误:', errorText.substring(0, 200));
                    } catch (e) {
                        console.warn('轮询获取监控数据返回 400 错误，无法读取错误详情');
                    }
                    // 静默处理，不中断轮询
                    return;
                }
                // 其他错误也静默处理，避免中断轮询
                console.debug(`轮询获取监控数据返回 ${response.status} 错误`);
                return;
            }
            
            const data = await response.json();
            
            if (data && data.success && pollingCallback) {
                // 检测系统活动状态：如果有车辆或车辆数量发生变化，认为系统活跃
                const vehicles = data.monitor_data?.vehicles || [];
                const hasActiveVehicles = vehicles.length > 0;
                
                if (hasActiveVehicles) {
                    // 有车辆活动，更新活动时间
                    lastActivityTime = Date.now();
                }
                
                // 转换为 WebSocket 格式的数据
                const vehicleUpdate = {
                    vehicles: vehicles,
                    monitor_data: data.monitor_data || {},
                    timestamp: new Date().toISOString()
                };
                pollingCallback(vehicleUpdate);
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            // 如果是超时或网络错误，静默处理
            if (fetchError.name === 'AbortError') {
                // 超时，静默处理
                return;
            }
            throw fetchError;
        }
    } catch (error) {
        // 静默处理错误，避免中断轮询
        // 只在非网络错误时输出调试信息
        if (error.message && !error.message.includes('Failed to fetch') && !error.message.includes('NetworkError')) {
            console.debug('轮询获取监控数据失败:', error.message || error);
        }
    }
}

/**
 * 获取连接状态
 * @returns {boolean} 是否已连接（WebSocket 或轮询）
 */
function isConnected() {
    return (websocketConnected && socket && socket.connected) || pollingInterval !== null;
}

// 导出函数（支持浏览器和 Node.js）
if (typeof window !== 'undefined') {
    // 浏览器环境：暴露到全局作用域
    window.TrafficWebSocket = {
        initWebSocket,
        disconnectWebSocket,
        requestUpdate,
        updateConnectionStatus,
        isConnected,
        startPolling,
        stopPolling,
        checkWebSocketAvailable,
        get socket() { return socket; },
        get connected() { return websocketConnected || pollingInterval !== null; },
    };
    // 为了兼容，也暴露到全局
    window.initWebSocket = initWebSocket;
    window.disconnectWebSocket = disconnectWebSocket;
    window.requestUpdate = requestUpdate;
    window.updateConnectionStatus = updateConnectionStatus;
    window.isWebSocketConnected = isConnected;
    
    // 暴露 socket 和 websocketConnected 的 getter/setter（避免重复声明）
    // 使用 Object.defineProperty 而不是直接赋值，避免与 HTML 中的声明冲突
    if (!window.hasOwnProperty('socket')) {
        Object.defineProperty(window, 'socket', {
            get: () => socket,
            set: (value) => {
                socket = value;
                syncSocketVars();
            },
            configurable: true,
            enumerable: true
        });
    }
    
    if (!window.hasOwnProperty('websocketConnected')) {
        Object.defineProperty(window, 'websocketConnected', {
            get: () => websocketConnected,
            set: (value) => {
                websocketConnected = value;
                syncSocketVars();
            },
            configurable: true,
            enumerable: true
        });
    }
    
    // 初始化同步
    syncSocketVars();
}

if (typeof module !== 'undefined' && module.exports) {
    // Node.js 环境
    module.exports = {
        initWebSocket,
        disconnectWebSocket,
        requestUpdate,
        updateConnectionStatus,
        isConnected,
        get socket() { return socket; },
        get connected() { return websocketConnected; },
    };
}

