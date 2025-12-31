/**
 * 工具函数单元测试
 * 使用简单的测试框架
 */

// 简单的测试框架
const TestRunner = {
    tests: [],
    passed: 0,
    failed: 0,

    test(name, fn) {
        this.tests.push({ name, fn });
    },

    async run() {
        console.log('🧪 开始运行测试...\n');
        
        for (const { name, fn } of this.tests) {
            try {
                await fn();
                this.passed++;
                console.log(`✅ ${name}`);
            } catch (error) {
                this.failed++;
                console.error(`❌ ${name}`);
                console.error(`   错误: ${error.message}`);
                if (error.stack) {
                    console.error(`   堆栈: ${error.stack.split('\n')[1]}`);
                }
            }
        }

        console.log(`\n📊 测试结果: ${this.passed} 通过, ${this.failed} 失败`);
        return this.failed === 0;
    }
};

// 断言函数
function assert(condition, message) {
    if (!condition) {
        throw new Error(message || '断言失败');
    }
}

function assertEqual(actual, expected, message) {
    if (actual !== expected) {
        throw new Error(message || `期望 ${expected}，实际得到 ${actual}`);
    }
}

function assertApproxEqual(actual, expected, tolerance = 0.0001, message) {
    if (Math.abs(actual - expected) > tolerance) {
        throw new Error(message || `期望约等于 ${expected}，实际得到 ${actual}`);
    }
}

// 加载工具函数（如果在 Node.js 环境）
let utils;
if (typeof require !== 'undefined') {
    utils = require('../js/utils.js');
} else {
    // 浏览器环境，假设已经加载
    utils = window.utils || {};
}

// 测试用例
TestRunner.test('escapeHtml - 转义特殊字符', () => {
    assertEqual(utils.escapeHtml('<script>alert("xss")</script>'), 
                '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
    assertEqual(utils.escapeHtml('&'), '&amp;');
    assertEqual(utils.escapeHtml("'"), '&#039;');
});

TestRunner.test('escapeHtml - 处理非字符串', () => {
    assertEqual(utils.escapeHtml(null), '');
    assertEqual(utils.escapeHtml(undefined), '');
    assertEqual(utils.escapeHtml(123), '123');
});

TestRunner.test('calculateDistance - 计算两点距离', () => {
    const dist = utils.calculateDistance({ x: 0, y: 0 }, { x: 3, y: 4 });
    assertApproxEqual(dist, 5);
    
    const dist2 = utils.calculateDistance({ x: 1, y: 1 }, { x: 4, y: 5 });
    assertApproxEqual(dist2, 5);
});

TestRunner.test('validateNode - 验证有效节点', () => {
    assert(utils.validateNode({ id: 'n1', x: 10, y: 20 }));
    assert(utils.validateNode({ id: 'n2', x: 0, y: 0, type: 'entrance' }));
});

TestRunner.test('validateNode - 拒绝无效节点', () => {
    assert(!utils.validateNode(null));
    assert(!utils.validateNode({}));
    assert(!utils.validateNode({ id: '', x: 10, y: 20 }));
    assert(!utils.validateNode({ id: 'n1', x: NaN, y: 20 }));
    assert(!utils.validateNode({ id: 'n1', x: 10 }));
});

TestRunner.test('validateEdge - 验证有效道路', () => {
    assert(utils.validateEdge({ id: 'e1', start: 'n1', end: 'n2' }));
    assert(utils.validateEdge({ id: 'e2', start: 'n1', end: 'n2', length: 100 }));
});

TestRunner.test('validateEdge - 拒绝无效道路', () => {
    assert(!utils.validateEdge(null));
    assert(!utils.validateEdge({}));
    assert(!utils.validateEdge({ id: 'e1', start: '', end: 'n2' }));
    assert(!utils.validateEdge({ id: 'e1', start: 'n1' }));
});

TestRunner.test('formatTime - 格式化时间', () => {
    const date = new Date('2024-01-01T12:00:00');
    const formatted = utils.formatTime(date);
    assert(formatted.includes('2024'));
    
    assertEqual(utils.formatTime(null), '-');
    assertEqual(utils.formatTime(undefined), '-');
});

// 防抖函数测试（需要异步）
TestRunner.test('debounce - 防抖功能', async () => {
    let callCount = 0;
    const debouncedFn = utils.debounce(() => {
        callCount++;
    }, 100);

    debouncedFn();
    debouncedFn();
    debouncedFn();
    
    assertEqual(callCount, 0); // 立即调用应该不会执行
    
    await new Promise(resolve => setTimeout(resolve, 150));
    assertEqual(callCount, 1); // 延迟后应该只执行一次
});

// 节流函数测试
TestRunner.test('throttle - 节流功能', async () => {
    let callCount = 0;
    const throttledFn = utils.throttle(() => {
        callCount++;
    }, 100);

    throttledFn();
    assertEqual(callCount, 1); // 第一次应该立即执行
    
    throttledFn();
    throttledFn();
    assertEqual(callCount, 1); // 节流期间不应该执行
    
    await new Promise(resolve => setTimeout(resolve, 150));
    throttledFn();
    assertEqual(callCount, 2); // 节流期过后应该可以执行
});

// 如果在 Node.js 环境，直接运行测试
if (typeof module !== 'undefined' && module.exports && typeof require !== 'undefined') {
    TestRunner.run().then(success => {
        process.exit(success ? 0 : 1);
    });
}

// 导出测试框架（用于浏览器环境）
if (typeof window !== 'undefined') {
    window.TestRunner = TestRunner;
    window.assert = assert;
    window.assertEqual = assertEqual;
    window.assertApproxEqual = assertApproxEqual;
}

