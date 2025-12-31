/**
 * 工具函数模块
 * 包含常用的工具函数
 */

/**
 * 防抖函数
 * @param {Function} func - 要防抖的函数
 * @param {number} wait - 等待时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 * @param {Function} func - 要节流的函数
 * @param {number} limit - 时间限制（毫秒）
 * @returns {Function} 节流后的函数
 */
function throttle(func, limit = 1000) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * HTML 转义
 * @param {string} text - 要转义的文本
 * @returns {string} 转义后的文本
 */
function escapeHtml(text) {
    if (typeof text !== 'string') {
        return String(text);
    }
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * 格式化时间
 * @param {Date|string} date - 日期对象或日期字符串
 * @returns {string} 格式化后的时间字符串
 */
function formatTime(date) {
    if (!date) return '-';
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleString('zh-CN');
}

/**
 * 格式化时长（秒转分钟）
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时长字符串
 */
function formatDuration(seconds) {
    if (typeof seconds !== 'number' || isNaN(seconds)) return '-';
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes} 分 ${secs} 秒`;
}

/**
 * 下载 JSON 文件
 * @param {Object} data - 要下载的数据
 * @param {string} filename - 文件名
 */
function downloadJsonFile(data, filename = 'data.json') {
    try {
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('下载文件失败:', error);
        throw error;
    }
}

/**
 * 从 localStorage 读取数据
 * @param {string} key - 键名
 * @param {*} defaultValue - 默认值
 * @returns {*} 读取的值或默认值
 */
function getLocalStorage(key, defaultValue = null) {
    try {
        const value = localStorage.getItem(key);
        if (value === null) return defaultValue;
        return JSON.parse(value);
    } catch (error) {
        console.warn(`读取 localStorage [${key}] 失败:`, error);
        return defaultValue;
    }
}

/**
 * 保存数据到 localStorage
 * @param {string} key - 键名
 * @param {*} value - 要保存的值
 * @returns {boolean} 是否成功
 */
function setLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (error) {
        console.warn(`保存 localStorage [${key}] 失败:`, error);
        return false;
    }
}

/**
 * 计算两点之间的距离
 * @param {Object} point1 - 点1 {x, y}
 * @param {Object} point2 - 点2 {x, y}
 * @returns {number} 距离
 */
function calculateDistance(point1, point2) {
    const dx = point2.x - point1.x;
    const dy = point2.y - point1.y;
    return Math.sqrt(dx * dx + dy * dy);
}

/**
 * 验证节点数据
 * @param {Object} node - 节点对象
 * @returns {boolean} 是否有效
 */
function validateNode(node) {
    if (!node || typeof node !== 'object') return false;
    if (typeof node.id !== 'string' || !node.id.trim()) return false;
    if (typeof node.x !== 'number' || isNaN(node.x)) return false;
    if (typeof node.y !== 'number' || isNaN(node.y)) return false;
    return true;
}

/**
 * 验证道路数据
 * @param {Object} edge - 道路对象
 * @returns {boolean} 是否有效
 */
function validateEdge(edge) {
    if (!edge || typeof edge !== 'object') return false;
    if (typeof edge.id !== 'string' || !edge.id.trim()) return false;
    if (typeof edge.start !== 'string' || !edge.start.trim()) return false;
    if (typeof edge.end !== 'string' || !edge.end.trim()) return false;
    return true;
}

// 导出函数（支持浏览器和 Node.js）
if (typeof window !== 'undefined') {
    // 浏览器环境：暴露到全局作用域
    window.TrafficUtils = {
        debounce,
        throttle,
        escapeHtml,
        formatTime,
        formatDuration,
        downloadJsonFile,
        getLocalStorage,
        setLocalStorage,
        calculateDistance,
        validateNode,
        validateEdge,
    };
    // 为了兼容，也暴露常用函数到全局
    // 使用 Object.defineProperty 避免重复声明冲突
    if (!window.hasOwnProperty('debounce')) {
        window.debounce = debounce;
    }
    if (!window.hasOwnProperty('throttle')) {
        window.throttle = throttle;
    }
    if (!window.hasOwnProperty('escapeHtml')) {
        window.escapeHtml = escapeHtml;
    }
    if (!window.hasOwnProperty('formatTime')) {
        window.formatTime = formatTime;
    }
    if (!window.hasOwnProperty('downloadJsonFile')) {
        Object.defineProperty(window, 'downloadJsonFile', {
            value: downloadJsonFile,
            writable: false,
            configurable: true,
            enumerable: true
        });
    }
}

if (typeof module !== 'undefined' && module.exports) {
    // Node.js 环境
    module.exports = {
        debounce,
        throttle,
        escapeHtml,
        formatTime,
        formatDuration,
        downloadJsonFile,
        getLocalStorage,
        setLocalStorage,
        calculateDistance,
        validateNode,
        validateEdge,
    };
}

