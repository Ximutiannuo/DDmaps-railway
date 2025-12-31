
// 全局配置和状态变量

// API 基础路径设置
(function() {
    const getApiBase = () => {
        if (window.API_BASE) {
            return window.API_BASE;
        }
        const origin = window.location.origin;
        if (origin === 'null' || origin.startsWith('file://')) {
            return 'http://localhost:5000/api';
        }
        return origin + '/api';
    };
    
    // 确保 window.API_BASE 存在
    if (!window.API_BASE) {
        window.API_BASE = getApiBase();
    }
})();

// 全局常量配置
const MAP_UPLOAD_DEFAULT_HTML = `
    <p>点击或拖拽图片到这里上传</p>
    <p class="vehicle-info">支持 JPG、PNG 格式，建议尺寸 800x600 以上</p>
`;

const MAP_UPLOAD_SUCCESS_HTML = `
    <p>地图上传成功！</p>
    <p class="vehicle-info">点击可重新上传</p>
`;

// 节点类型配置（与后端一致）
const nodeTypes = {
    'entrance': { name: '进场口', color: '#2ecc71' },
    'crossroad': { name: '交叉口', color: '#3498db' },
    'work-area': { name: '作业区', color: '#e74c3c' },
    'start': { name: '场外起点', color: '#9b59b6' }
};

// 方向类型配置（与后端一致）
const defaultDirectionTypes = {
    'two-way': { 'name': '双向通行', 'description': '允许双向行驶' },
    'north': { 'name': '北向单行', 'description': '只允许从南向北行驶' },
    'south': { 'name': '南向单行', 'description': '只允许从北向南行驶' },
    'east': { 'name': '东向单行', 'description': '只允许从西向东行驶' },
    'west': { 'name': '西向单行', 'description': '只允许从东向西行驶' },
    'northeast': { 'name': '东北向单行', 'description': '只允许从西南向东北行驶' },
    'northwest': { 'name': '西北向单行', 'description': '只允许从东南向西北行驶' },
    'southeast': { 'name': '东南向单行', 'description': '只允许从西北向东南行驶' },
    'southwest': { 'name': '西南向单行', 'description': '只允许从东北向西南行驶' }
};

// 全局状态变量
// 使用 var 确保全局作用域（虽然不推荐，但为了兼容旧代码）
// 或者直接挂载到 window
window.nodes = [];
window.edges = [];
window.vehicles = [];
window.mapTextLabels = [];  // 地图文字框列表
window.vehicleCounter = 1;
window.monitorData = {};
window.travelTimeRecords = [];
window.editMode = false;
window.mapBackground = null;
window.vehicleTypes = {};
window.directionTypes = {};
window.drivers = {};
window.driverRoutes = {};
window.activeDriverId = null;

// 为了兼容使用 let/const 的代码，我们在 window 上定义这些属性
// 注意：在模块化脚本中，直接使用 nodes 可能会报错，除非它们是显式全局的。
// 在非模块化脚本（目前的做法）中，window.nodes 和 nodes 是一样的。

