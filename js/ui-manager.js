// UI 管理模块
// 提供 Toast 通知、错误处理、按钮状态管理等功能

// 访问全局变量（通过 window 对象）
const getGlobalVars = () => ({
    nodes: window.nodes || [],
    edges: window.edges || [],
    vehicles: window.vehicles || [],
    monitorData: window.monitorData || {},
    vehicleTypes: window.vehicleTypes || {}
});

// 日志函数（如果存在）
const log = window.log || console.log.bind(console);
const logError = window.logError || console.error.bind(console);
const logWarn = window.logWarn || console.warn.bind(console);

        function updateVehicleList(sortByEfficiency = false) {
            const vehicleList = document.getElementById('vehicle-list');
            vehicleList.innerHTML = '';

            let displayVehicles = [...vehicles];
            if (sortByEfficiency) {
                displayVehicles.sort((a, b) => {
                    const sa = a.efficiency_score || 999999;
                    const sb = b.efficiency_score || 999999;
                    return sa - sb;
                });
            }

            if (displayVehicles.length === 0) {
                vehicleList.innerHTML = '<div class="loading">暂无车辆</div>';
                return;
            }

            displayVehicles.forEach(vehicle => {
                const vehicleItem = document.createElement('div');
                vehicleItem.className = 'vehicle-item';

                const leftDiv = document.createElement('div');
                let driverInfo = '';
                if (vehicle.driver_id) {
                    driverInfo = `<div class="vehicle-info" style="color: #27ae60;">👤 司机: ${vehicle.driver_name || vehicle.driver_id}</div>`;
                }
                
                leftDiv.innerHTML = `<strong>${vehicle.id}</strong> - ${vehicle.type}
                    <div class="vehicle-info">载重: ${vehicle.weight}吨 | 宽度: ${vehicle.width}米</div>
                    ${driverInfo}
                    <div class="vehicle-info">状态: ${vehicle.status || 'moving'}</div>`;

                const rightDiv = document.createElement('div');
                const eff = vehicle.efficiency_score !== undefined && vehicle.efficiency_score !== null
                    ? `${vehicle.efficiency_score.toFixed(1)}`
                    : 'N/A';
                rightDiv.innerHTML = `起点: ${getNodeName(vehicle.start_node)}<br>目标: ${getNodeName(vehicle.target_node)}<br><small>效率: ${eff}</small>`;

                vehicleItem.appendChild(leftDiv);
                vehicleItem.appendChild(rightDiv);

                vehicleList.appendChild(vehicleItem);
            });
        }


// 导出到全局
if (typeof window !== 'undefined') {
    window.showToast = showToast;
    window.showError = showError;
    window.showSuccess = showSuccess;
    window.setButtonLoading = setButtonLoading;
    window.enhanceButton = enhanceButton;
    if (typeof updateVehicleList === 'function') {
        window.updateVehicleList = updateVehicleList;
    }
}
