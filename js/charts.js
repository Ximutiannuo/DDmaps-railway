/**
 * 图表模块
 * 处理所有数据可视化相关的功能
 */

// 全局图表实例
let charts = {};

/**
 * 初始化所有图表
 */
function initCharts() {
    // 检查 Chart.js 是否已加载
    if (typeof Chart === 'undefined') {
        console.warn('⚠️ Chart.js 库未加载，图表功能不可用');
        return;
    }

    // 初始化效率趋势图
    const efficiencyCtx = document.getElementById('efficiency-chart');
    if (efficiencyCtx) {
        charts.efficiency = new Chart(efficiencyCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '平均效率',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 5,
                        bottom: 5,
                        left: 5,
                        right: 5
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1.0,
                        title: {
                            display: true,
                            text: '效率分数'
                        }
                    }
                }
            }
        });
    }

    // 初始化车辆类型分布图
    const vehicleTypeCtx = document.getElementById('vehicle-type-chart');
    if (vehicleTypeCtx) {
        charts.vehicleType = new Chart(vehicleTypeCtx, {
            type: 'pie',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#3498db',
                        '#2ecc71',
                        '#f39c12',
                        '#8e44ad',
                        '#16a085',
                        '#e74c3c',
                        '#3498db'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 5,
                        bottom: 5,
                        left: 5,
                        right: 5
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // 初始化道路拥堵热力图数据
    const congestionCtx = document.getElementById('congestion-chart');
    if (congestionCtx) {
        charts.congestion = new Chart(congestionCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: '拥堵系数',
                    data: [],
                    backgroundColor: function(context) {
                        // 安全检查：确保 parsed 存在
                        if (!context || !context.parsed) {
                            return '#2ecc71'; // 默认颜色
                        }
                        const value = context.parsed.y;
                        if (typeof value !== 'number' || isNaN(value)) {
                            return '#2ecc71'; // 默认颜色
                        }
                        if (value > 2.0) return '#e74c3c';
                        if (value > 1.5) return '#f39c12';
                        return '#2ecc71';
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 5,
                        bottom: 5,
                        left: 5,
                        right: 5
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '拥堵系数'
                        }
                    }
                }
            }
        });
    }
}

/**
 * 更新效率趋势图
 * @param {Array} vehicles - 车辆数组
 */
function updateEfficiencyChart(vehicles = []) {
    if (!charts.efficiency) return;

    const movingVehicles = vehicles.filter(v => v && v.status === 'moving' && v.efficiency_score !== null && v.efficiency_score !== undefined);
    if (movingVehicles.length === 0) {
        return;
    }

    const avgEfficiency = movingVehicles.reduce((sum, v) => sum + (v.efficiency_score || 0), 0) / movingVehicles.length;
    if (isNaN(avgEfficiency)) {
        return;
    }

    const now = new Date().toLocaleTimeString();
    const chart = charts.efficiency;
    if (!chart.data || !chart.data.labels || !chart.data.datasets || !chart.data.datasets[0]) {
        return;
    }

    chart.data.labels.push(now);
    chart.data.datasets[0].data.push(avgEfficiency);

    // 只保留最近20个数据点
    if (chart.data.labels.length > 20) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }

    chart.update('none');
}

/**
 * 更新车辆类型分布图
 * @param {Array} vehicles - 车辆数组
 */
function updateVehicleTypeChart(vehicles = []) {
    if (!charts.vehicleType) return;

    const typeCount = {};
    vehicles.forEach(v => {
        if (v && v.type) {
            typeCount[v.type] = (typeCount[v.type] || 0) + 1;
        }
    });

    const chart = charts.vehicleType;
    if (!chart.data || !chart.data.datasets || !chart.data.datasets[0]) {
        return;
    }

    chart.data.labels = Object.keys(typeCount);
    chart.data.datasets[0].data = Object.values(typeCount);
    chart.update('none');
}

/**
 * 更新拥堵图表
 * @param {Array} edges - 道路数组
 */
function updateCongestionChart(edges = []) {
    if (!charts.congestion) return;

    const congestedEdges = edges.filter(e => e && e.congestion_coeff && e.congestion_coeff > 1.0)
        .sort((a, b) => (b.congestion_coeff || 0) - (a.congestion_coeff || 0))
        .slice(0, 10);

    const chart = charts.congestion;
    if (!chart.data || !chart.data.datasets || !chart.data.datasets[0]) {
        return;
    }

    if (congestedEdges.length === 0) {
        chart.data.labels = [];
        chart.data.datasets[0].data = [];
    } else {
        chart.data.labels = congestedEdges.map(e => e.id || '未知');
        chart.data.datasets[0].data = congestedEdges.map(e => e.congestion_coeff || 0);
    }

    chart.update('none');
}

/**
 * 更新所有图表
 * @param {Object} data - 数据对象 {vehicles, edges}
 */
function updateAllCharts(data = {}) {
    const { vehicles = [], edges = [] } = data;
    try {
        updateEfficiencyChart(vehicles);
    } catch (err) {
        console.error('更新效率图表失败:', err);
    }
    try {
        updateVehicleTypeChart(vehicles);
    } catch (err) {
        console.error('更新车辆类型图表失败:', err);
    }
    try {
        updateCongestionChart(edges);
    } catch (err) {
        console.error('更新拥堵图表失败:', err);
    }
}

// 导出函数（支持浏览器和 Node.js）
if (typeof window !== 'undefined') {
    // 浏览器环境：暴露到全局作用域
    window.TrafficCharts = {
        charts,
        initCharts,
        updateEfficiencyChart,
        updateVehicleTypeChart,
        updateCongestionChart,
        updateAllCharts,
    };
    // 为了兼容，也暴露到全局
    // 使用 Object.defineProperty 避免重复声明冲突
    if (!window.hasOwnProperty('charts')) {
        Object.defineProperty(window, 'charts', {
            get: () => charts,
            set: (value) => { charts = value; },
            configurable: true,
            enumerable: true
        });
    } else {
        // 如果已经存在，直接赋值
        window.charts = charts;
    }
    
    window.initCharts = initCharts;
    window.updateEfficiencyChart = updateEfficiencyChart;
    window.updateVehicleTypeChart = updateVehicleTypeChart;
    window.updateCongestionChart = updateCongestionChart;
    window.updateAllCharts = updateAllCharts;
}

if (typeof module !== 'undefined' && module.exports) {
    // Node.js 环境
    module.exports = {
        charts,
        initCharts,
        updateEfficiencyChart,
        updateVehicleTypeChart,
        updateCongestionChart,
        updateAllCharts,
    };
}

