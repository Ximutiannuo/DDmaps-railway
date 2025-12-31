/**
 * 工具函数模块 (TypeScript 版本)
 */

import { Node, Edge } from './types';

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number = 300
): (...args: Parameters<T>) => void {
    let timeout: ReturnType<typeof setTimeout> | null = null;
    return function executedFunction(...args: Parameters<T>) {
        const later = () => {
            timeout = null;
            func(...args);
        };
        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
    func: T,
    limit: number = 1000
): (...args: Parameters<T>) => void {
    let inThrottle: boolean = false;
    return function executedFunction(...args: Parameters<T>) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * HTML 转义
 */
export function escapeHtml(text: string | number | null | undefined): string {
    if (text === null || text === undefined) return '';
    const str = String(text);
    const map: Record<string, string> = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return str.replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * 格式化时间
 */
export function formatTime(date: Date | string | null | undefined): string {
    if (!date) return '-';
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleString('zh-CN');
}

/**
 * 计算两点之间的距离
 */
export function calculateDistance(
    point1: { x: number; y: number },
    point2: { x: number; y: number }
): number {
    const dx = point2.x - point1.x;
    const dy = point2.y - point1.y;
    return Math.sqrt(dx * dx + dy * dy);
}

/**
 * 验证节点数据
 */
export function validateNode(node: any): node is Node {
    if (!node || typeof node !== 'object') return false;
    if (typeof node.id !== 'string' || !node.id.trim()) return false;
    if (typeof node.x !== 'number' || isNaN(node.x)) return false;
    if (typeof node.y !== 'number' || isNaN(node.y)) return false;
    return true;
}

/**
 * 验证道路数据
 */
export function validateEdge(edge: any): edge is Edge {
    if (!edge || typeof edge !== 'object') return false;
    if (typeof edge.id !== 'string' || !edge.id.trim()) return false;
    if (typeof edge.start !== 'string' || !edge.start.trim()) return false;
    if (typeof edge.end !== 'string' || !edge.end.trim()) return false;
    return true;
}

