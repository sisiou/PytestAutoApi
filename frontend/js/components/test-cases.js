// 测试用例页面JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initTestCasesPage();
});

// 页面初始化
function initTestCasesPage() {
    // 加载测试用例数据
    loadTestCases();
    
    // 加载API列表
    loadAPIList();
    
    // 加载接口文档列表
    loadAPIDocList();
    
    // 绑定事件监听器
    bindEventListeners();
    
    // 初始化视图模式
    initViewMode();
}

// 绑定事件监听器
function bindEventListeners() {
    // 刷新按钮
    document.getElementById('refreshBtn').addEventListener('click', function() {
        showLoadingState();
        loadTestCases();
    });
    
    // 运行所有测试按钮
    document.getElementById('runAllBtn').addEventListener('click', function() {
        showRunModal('all');
    });
    
    // 生成测试用例按钮
    document.getElementById('generateBtn').addEventListener('click', function() {
        showGenerateModal();
    });
    
    // 搜索输入
    document.getElementById('searchInput').addEventListener('input', function() {
        filterTestCases();
    });
    
    // 筛选器
    document.getElementById('statusFilter').addEventListener('change', function() {
        filterTestCases();
    });
    
    document.getElementById('typeFilter').addEventListener('change', function() {
        filterTestCases();
    });
    
    document.getElementById('apiFilter').addEventListener('change', function() {
        filterTestCases();
    });
    
    // 视图模式切换
    document.getElementById('listView').addEventListener('change', function() {
        switchViewMode('list');
    });
    
    document.getElementById('gridView').addEventListener('change', function() {
        switchViewMode('grid');
    });
    
    // 生成测试用例模态框
    document.getElementById('confirmGenerateBtn').addEventListener('click', function() {
        generateTestCases();
    });
    
    // 运行测试模态框
    document.getElementById('cancelRunBtn').addEventListener('click', function() {
        hideRunModal();
    });
    
    document.getElementById('viewResultsBtn').addEventListener('click', function() {
        hideRunModal();
        // 可以在这里添加跳转到测试结果的逻辑
    });
}

// 初始化视图模式
function initViewMode() {
    const listView = document.getElementById('listView');
    const gridView = document.getElementById('gridView');
    
    // 默认使用列表视图
    listView.checked = true;
    switchViewMode('list');
}

// 切换视图模式
function switchViewMode(mode) {
    const testCasesList = document.getElementById('testCasesList');
    
    if (mode === 'grid') {
        testCasesList.classList.add('test-case-grid');
        renderTestCasesGrid();
    } else {
        testCasesList.classList.remove('test-case-grid');
        renderTestCasesList();
    }
}

// 加载测试用例数据
function loadTestCases() {
    showLoadingState();
    
    // 从后端API获取测试用例列表
    fetch('http://localhost:19028/api/test-cases', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取测试用例列表失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('从后端加载的测试用例列表:', data);
        
        // 存储测试用例数据
        window.currentTestCases = data || [];
        
        // 更新统计数据
        updateStatistics(window.currentTestCases);
        
        // 根据当前视图模式渲染测试用例
        const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
        if (viewMode === 'grid') {
            renderTestCasesGrid();
        } else {
            renderTestCasesList();
        }
    })
    .catch(error => {
        console.error('加载测试用例失败:', error);
        showNotification('加载测试用例失败: ' + error.message, 'error');
        
        // 如果加载失败，显示空状态
        window.currentTestCases = [];
        updateStatistics(window.currentTestCases);
        renderEmptyState();
    })
    .finally(() => {
        hideLoadingState();
    });
}

// 获取模拟测试用例数据
function getMockTestCases() {
    return [
        {
            id: 1,
            name: '用户登录 - 正常情况',
            description: '测试用户使用正确的用户名和密码登录',
            api: '用户登录API',
            apiId: 'api_1',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:22',
            duration: '0.32s',
            tags: ['登录', '正常流程']
        },
        {
            id: 2,
            name: '用户登录 - 错误密码',
            description: '测试用户使用错误的密码登录',
            api: '用户登录API',
            apiId: 'api_1',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:23',
            duration: '0.28s',
            tags: ['登录', '异常处理']
        },
        {
            id: 3,
            name: '用户登录 - 不存在的用户',
            description: '测试使用不存在的用户名登录',
            api: '用户登录API',
            apiId: 'api_1',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:24',
            duration: '0.31s',
            tags: ['登录', '异常处理']
        },
        {
            id: 4,
            name: '获取用户信息',
            description: '测试获取已登录用户的详细信息',
            api: '用户信息API',
            apiId: 'api_2',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:25',
            duration: '0.45s',
            tags: ['用户信息', '正常流程']
        },
        {
            id: 5,
            name: '获取用户信息 - 未登录',
            description: '测试未登录状态下获取用户信息',
            api: '用户信息API',
            apiId: 'api_2',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:26',
            duration: '0.29s',
            tags: ['用户信息', '异常处理']
        },
        {
            id: 6,
            name: '创建订单 - 正常情况',
            description: '测试创建订单的完整流程',
            api: '订单管理API',
            apiId: 'api_3',
            type: 'scenario',
            status: 'failed',
            lastRun: '2025-06-18 14:30:27',
            duration: '1.23s',
            tags: ['订单', '场景测试']
        },
        {
            id: 7,
            name: '创建订单 - 库存不足',
            description: '测试商品库存不足时创建订单',
            api: '订单管理API',
            apiId: 'api_3',
            type: 'boundary',
            status: 'passed',
            lastRun: '2025-06-18 14:30:28',
            duration: '0.67s',
            tags: ['订单', '边界测试']
        },
        {
            id: 8,
            name: '创建订单 - 无效商品ID',
            description: '测试使用无效商品ID创建订单',
            api: '订单管理API',
            apiId: 'api_3',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:29',
            duration: '0.34s',
            tags: ['订单', '异常处理']
        },
        {
            id: 9,
            name: '查询订单列表',
            description: '测试查询用户的订单列表',
            api: '订单查询API',
            apiId: 'api_4',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:30',
            duration: '0.56s',
            tags: ['订单', '查询']
        },
        {
            id: 10,
            name: '查询订单详情',
            description: '测试查询特定订单的详细信息',
            api: '订单查询API',
            apiId: 'api_4',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:31',
            duration: '0.41s',
            tags: ['订单', '查询']
        },
        {
            id: 11,
            name: '查询订单详情 - 不存在的订单ID',
            description: '测试查询不存在的订单详情',
            api: '订单查询API',
            apiId: 'api_4',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:32',
            duration: '0.28s',
            tags: ['订单', '异常处理']
        },
        {
            id: 12,
            name: '取消订单 - 正常情况',
            description: '测试取消未发货的订单',
            api: '订单管理API',
            apiId: 'api_3',
            type: 'scenario',
            status: 'passed',
            lastRun: '2025-06-18 14:30:33',
            duration: '0.89s',
            tags: ['订单', '场景测试']
        },
        {
            id: 13,
            name: '取消订单 - 已发货订单',
            description: '测试取消已发货的订单',
            api: '订单管理API',
            apiId: 'api_3',
            type: 'boundary',
            status: 'failed',
            lastRun: '2025-06-18 14:30:34',
            duration: '0.76s',
            tags: ['订单', '边界测试']
        },
        {
            id: 14,
            name: '添加商品到购物车',
            description: '测试添加商品到购物车的功能',
            api: '购物车API',
            apiId: 'api_5',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:35',
            duration: '0.52s',
            tags: ['购物车', '正常流程']
        },
        {
            id: 15,
            name: '添加商品到购物车 - 库存不足',
            description: '测试添加库存不足的商品到购物车',
            api: '购物车API',
            apiId: 'api_5',
            type: 'boundary',
            status: 'passed',
            lastRun: '2025-06-18 14:30:36',
            duration: '0.48s',
            tags: ['购物车', '边界测试']
        },
        {
            id: 16,
            name: '修改购物车商品数量',
            description: '测试修改购物车中商品的数量',
            api: '购物车API',
            apiId: 'api_5',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:37',
            duration: '0.43s',
            tags: ['购物车', '正常流程']
        },
        {
            id: 17,
            name: '修改购物车商品数量 - 超出库存',
            description: '测试将购物车商品数量修改为超出库存的值',
            api: '购物车API',
            apiId: 'api_5',
            type: 'boundary',
            status: 'passed',
            lastRun: '2025-06-18 14:30:38',
            duration: '0.46s',
            tags: ['购物车', '边界测试']
        },
        {
            id: 18,
            name: '删除购物车商品',
            description: '测试从购物车中删除商品',
            api: '购物车API',
            apiId: 'api_5',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:39',
            duration: '0.38s',
            tags: ['购物车', '正常流程']
        },
        {
            id: 19,
            name: '清空购物车',
            description: '测试清空用户购物车的功能',
            api: '购物车API',
            apiId: 'api_5',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:40',
            duration: '0.41s',
            tags: ['购物车', '正常流程']
        },
        {
            id: 20,
            name: '获取商品列表',
            description: '测试获取商品列表的功能',
            api: '商品API',
            apiId: 'api_6',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:41',
            duration: '0.63s',
            tags: ['商品', '查询']
        },
        {
            id: 21,
            name: '获取商品详情',
            description: '测试获取特定商品的详细信息',
            api: '商品API',
            apiId: 'api_6',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:42',
            duration: '0.51s',
            tags: ['商品', '查询']
        },
        {
            id: 22,
            name: '搜索商品',
            description: '测试根据关键词搜索商品',
            api: '商品API',
            apiId: 'api_6',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:43',
            duration: '0.72s',
            tags: ['商品', '搜索']
        },
        {
            id: 23,
            name: '商品分类浏览',
            description: '测试按分类浏览商品',
            api: '商品API',
            apiId: 'api_6',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:44',
            duration: '0.68s',
            tags: ['商品', '分类']
        },
        {
            id: 24,
            name: '用户注册 - 正常情况',
            description: '测试用户使用有效信息注册',
            api: '用户注册API',
            apiId: 'api_7',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:45',
            duration: '0.87s',
            tags: ['注册', '正常流程']
        },
        {
            id: 25,
            name: '用户注册 - 重复用户名',
            description: '测试使用已存在的用户名注册',
            api: '用户注册API',
            apiId: 'api_7',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:46',
            duration: '0.54s',
            tags: ['注册', '异常处理']
        },
        {
            id: 26,
            name: '用户注册 - 无效邮箱',
            description: '测试使用无效邮箱格式注册',
            api: '用户注册API',
            apiId: 'api_7',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:47',
            duration: '0.49s',
            tags: ['注册', '异常处理']
        },
        {
            id: 27,
            name: '用户注册 - 弱密码',
            description: '测试使用弱密码注册',
            api: '用户注册API',
            apiId: 'api_7',
            type: 'boundary',
            status: 'passed',
            lastRun: '2025-06-18 14:30:48',
            duration: '0.53s',
            tags: ['注册', '边界测试']
        },
        {
            id: 28,
            name: '修改用户信息',
            description: '测试修改用户的基本信息',
            api: '用户信息API',
            apiId: 'api_2',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:49',
            duration: '0.61s',
            tags: ['用户信息', '修改']
        },
        {
            id: 29,
            name: '修改密码',
            description: '测试修改用户密码的功能',
            api: '用户密码API',
            apiId: 'api_8',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:50',
            duration: '0.78s',
            tags: ['密码', '修改']
        },
        {
            id: 30,
            name: '修改密码 - 错误原密码',
            description: '测试使用错误的原密码修改密码',
            api: '用户密码API',
            apiId: 'api_8',
            type: 'exception',
            status: 'passed',
            lastRun: '2025-06-18 14:30:51',
            duration: '0.56s',
            tags: ['密码', '异常处理']
        },
        {
            id: 31,
            name: '重置密码',
            description: '测试通过邮箱重置密码',
            api: '用户密码API',
            apiId: 'api_8',
            type: 'scenario',
            status: 'passed',
            lastRun: '2025-06-18 14:30:52',
            duration: '1.12s',
            tags: ['密码', '重置']
        },
        {
            id: 32,
            name: '获取支付方式',
            description: '测试获取可用的支付方式列表',
            api: '支付API',
            apiId: 'api_9',
            type: 'basic',
            status: 'passed',
            lastRun: '2025-06-18 14:30:53',
            duration: '0.47s',
            tags: ['支付', '查询']
        },
        {
            id: 33,
            name: '创建支付',
            description: '测试创建订单支付',
            api: '支付API',
            apiId: 'api_9',
            type: 'scenario',
            status: 'failed',
            lastRun: '2025-06-18 14:30:54',
            duration: '1.34s',
            tags: ['支付', '场景测试']
        }
    ];
}

// 更新统计数据
function updateStatistics(testCases) {
    const totalCases = testCases.length;
    const passedCases = testCases.filter(tc => tc.status === 'passed').length;
    const failedCases = testCases.filter(tc => tc.status === 'failed').length;
    const skippedCases = testCases.filter(tc => tc.status === 'skipped').length;
    const passRate = totalCases > 0 ? ((passedCases / totalCases) * 100).toFixed(1) : 0;
    
    document.getElementById('totalCases').textContent = totalCases;
    document.getElementById('passedCases').textContent = passedCases;
    document.getElementById('failedCases').textContent = failedCases;
    document.getElementById('passRate').textContent = passRate + '%';
}

// 渲染测试用例列表
function renderTestCasesList() {
    const testCasesList = document.getElementById('testCasesList');
    const testCases = getFilteredTestCases();
    
    if (testCases.length === 0) {
        renderEmptyState();
        return;
    }
    
    let html = '';
    
    testCases.forEach(testCase => {
        html += `
            <div class="test-case-item" data-id="${testCase.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="test-name">${testCase.name}</div>
                        <div class="test-description">${testCase.description}</div>
                        <div class="test-meta">
                            <span class="status-badge ${testCase.status}">${getStatusText(testCase.status)}</span>
                            <span class="type-badge ${testCase.type}">${getTypeText(testCase.type)}</span>
                            <span class="badge bg-light text-dark">
                                <i class="fas fa-clock me-1"></i>${testCase.duration}
                            </span>
                            <span class="badge bg-light text-dark">
                                <i class="fas fa-code me-1"></i>${testCase.api}
                            </span>
                            <span class="badge bg-light text-dark">
                                <i class="fas fa-calendar me-1"></i>${testCase.lastRun}
                            </span>
                        </div>
                        <div class="test-tags">
                            ${testCase.tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                        </div>
                    </div>
                    <div class="test-actions">
                        <button class="btn btn-sm btn-outline-primary view-btn" data-id="${testCase.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success run-btn" data-id="${testCase.id}">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-warning edit-btn" data-id="${testCase.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${testCase.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    testCasesList.innerHTML = html;
    
    // 绑定测试用例操作按钮事件
    bindTestCaseActions();
}

// 渲染测试用例网格
function renderTestCasesGrid() {
    const testCasesList = document.getElementById('testCasesList');
    const testCases = getFilteredTestCases();
    
    if (testCases.length === 0) {
        renderEmptyState();
        return;
    }
    
    let html = '';
    
    testCases.forEach(testCase => {
        html += `
            <div class="card test-case-card ${testCase.status}" data-id="${testCase.id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title">${testCase.name}</h5>
                        <span class="status-badge ${testCase.status}">${getStatusText(testCase.status)}</span>
                    </div>
                    <p class="card-text text-muted small">${testCase.description}</p>
                    <div class="mb-3">
                        <span class="type-badge ${testCase.type}">${getTypeText(testCase.type)}</span>
                        <span class="badge bg-light text-dark ms-1">
                            <i class="fas fa-clock me-1"></i>${testCase.duration}
                        </span>
                    </div>
                    <div class="mb-3">
                        <div class="small text-muted mb-1">API: ${testCase.api}</div>
                        <div class="small text-muted">最后运行: ${testCase.lastRun}</div>
                    </div>
                    <div class="d-flex justify-content-between">
                        <div>
                            ${testCase.tags.slice(0, 2).map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                        </div>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary view-btn" data-id="${testCase.id}">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-success run-btn" data-id="${testCase.id}">
                                <i class="fas fa-play"></i>
                            </button>
                            <button class="btn btn-outline-warning edit-btn" data-id="${testCase.id}">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-outline-danger delete-btn" data-id="${testCase.id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    testCasesList.innerHTML = html;
    
    // 绑定测试用例操作按钮事件
    bindTestCaseActions();
}

// 绑定测试用例操作按钮事件
function bindTestCaseActions() {
    // 查看按钮
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            showTestCaseDetail(testCaseId);
        });
    });
    
    // 运行按钮
    document.querySelectorAll('.run-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            showRunModal(testCaseId);
        });
    });
    
    // 编辑按钮
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            editTestCase(testCaseId);
        });
    });
    
    // 删除按钮
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            deleteTestCase(testCaseId);
        });
    });
}

// 获取筛选后的测试用例
function getFilteredTestCases() {
    if (!window.currentTestCases) return [];
    
    let testCases = [...window.currentTestCases];
    
    // 搜索筛选
    const searchInput = document.getElementById('searchInput').value.toLowerCase();
    if (searchInput) {
        testCases = testCases.filter(tc => 
            tc.name.toLowerCase().includes(searchInput) || 
            tc.description.toLowerCase().includes(searchInput) ||
            tc.api.toLowerCase().includes(searchInput) ||
            tc.tags.some(tag => tag.toLowerCase().includes(searchInput))
        );
    }
    
    // 状态筛选
    const statusFilter = document.getElementById('statusFilter').value;
    if (statusFilter) {
        testCases = testCases.filter(tc => tc.status === statusFilter);
    }
    
    // 类型筛选
    const typeFilter = document.getElementById('typeFilter').value;
    if (typeFilter) {
        testCases = testCases.filter(tc => tc.type === typeFilter);
    }
    
    // API筛选
    const apiFilter = document.getElementById('apiFilter').value;
    if (apiFilter) {
        testCases = testCases.filter(tc => tc.apiId === apiFilter);
    }
    
    return testCases;
}

// 筛选测试用例
function filterTestCases() {
    const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
    if (viewMode === 'grid') {
        renderTestCasesGrid();
    } else {
        renderTestCasesList();
    }
}

// 显示测试用例详情
function showTestCaseDetail(testCaseId) {
    // 从后端API获取测试用例详情
    fetch(`http://localhost:19028/api/test-cases/${testCaseId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取测试用例详情失败');
        }
        return response.json();
    })
    .then(testCase => {
        console.log('从后端加载的测试用例详情:', testCase);
        
        // 填充详情标签页
        const detailsTab = document.getElementById('details');
        detailsTab.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <h6>测试用例名称</h6>
                    <p>${testCase.name}</p>
                </div>
                <div class="col-md-6">
                    <h6>状态</h6>
                    <p><span class="status-badge ${testCase.status}">${getStatusText(testCase.status)}</span></p>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <h6>类型</h6>
                    <p><span class="type-badge ${testCase.type}">${getTypeText(testCase.type)}</span></p>
                </div>
                <div class="col-md-6">
                    <h6>API</h6>
                    <p>${testCase.api || 'N/A'}</p>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-12">
                    <h6>描述</h6>
                    <p>${testCase.description || '无描述'}</p>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <h6>创建时间</h6>
                    <p>${testCase.created_at || 'N/A'}</p>
                </div>
                <div class="col-md-6">
                    <h6>HTTP方法</h6>
                    <p>${testCase.method || 'N/A'}</p>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-12">
                    <h6>标签</h6>
                    <div>
                        ${testCase.tags && testCase.tags.length > 0 ? testCase.tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('') : '无标签'}
                    </div>
                </div>
            </div>
        `;
        
        // 填充代码标签页
        const codeTab = document.getElementById('code');
        const testName = testCase.name.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
        const codeContent = `# ${testCase.name}
# ${testCase.description}

import pytest
import requests
import json

def test_${testName}():
    """
    ${testCase.description}
    """
    # API端点
    url = "https://api.example.com/${testCase.apiId || testCase.api}"
    
    # 请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your_token_here"
    }
    
    # 请求数据
    data = {
        # 根据实际API需求设置测试数据
        "param1": "value1",
        "param2": "value2"
    }
    
    # 发送请求
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    # 验证响应
    assert response.status_code == 200
    
    # 验证响应数据
    response_data = response.json()
    assert "result" in response_data
    
    # 更多断言...
    
    print("测试通过: ${testCase.name}")`;
        
        codeTab.innerHTML = `
            <div class="code-container">
                <pre><code class="language-python">${codeContent}</code></pre>
            </div>
        `;
        
        // 填充测试结果标签页
        const resultsTab = document.getElementById('results');
        resultsTab.innerHTML = `
            <div class="test-result-item ${testCase.status}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>测试执行结果</strong>
                        <div class="result-message">
                            ${testCase.status === 'passed' ? '测试通过' : '测试失败'}
                        </div>
                    </div>
                    <div class="result-timestamp">
                        ${testCase.lastRun}
                    </div>
                </div>
                ${testCase.status === 'failed' ? `
                <div class="mt-2">
                    <strong>失败原因:</strong>
                    <div class="alert alert-danger mt-1">
                        断言失败: 预期状态码为200，实际返回404
                    </div>
                </div>
                ` : ''}
                <div class="mt-2">
                    <strong>执行时长:</strong> ${testCase.duration}
                </div>
            </div>
        `;
        
        // 绑定模态框按钮事件
        const editBtn = document.getElementById('editBtn');
        const runBtn = document.getElementById('runBtn');
        
        if (editBtn) {
            editBtn.onclick = function() {
                hideTestCaseDetailModal();
                editTestCase(testCaseId);
            };
        }
        
        if (runBtn) {
            runBtn.onclick = function() {
                hideTestCaseDetailModal();
                showRunModal(testCaseId);
            };
        }
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('testCaseDetailModal'));
        modal.show();
        
        // 重新初始化代码高亮
        if (window.Prism) {
            Prism.highlightAll();
        }
    })
    .catch(error => {
        console.error('获取测试用例详情失败:', error);
        showNotification('获取测试用例详情失败: ' + error.message, 'error');
    });
}

// 隐藏测试用例详情模态框
function hideTestCaseDetailModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('testCaseDetailModal'));
    if (modal) modal.hide();
}

// 编辑测试用例
function editTestCase(testCaseId) {
    // 这里可以实现编辑测试用例的逻辑
    showNotification('编辑功能正在开发中', 'info');
}

// 删除测试用例
function deleteTestCase(testCaseId) {
    if (confirm('确定要删除这个测试用例吗？')) {
        // 从当前数据中删除测试用例
        window.currentTestCases = window.currentTestCases.filter(tc => tc.id != testCaseId);
        
        // 重新渲染列表
        const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
        if (viewMode === 'grid') {
            renderTestCasesGrid();
        } else {
            renderTestCasesList();
        }
        
        // 更新统计数据
        updateStatistics(window.currentTestCases);
        
        showNotification('测试用例已删除', 'success');
    }
}

// 显示运行测试模态框
function showRunModal(testCaseId) {
    const modal = new bootstrap.Modal(document.getElementById('runModal'));
    const runStatus = document.getElementById('runStatus');
    const runProgress = document.getElementById('runProgress');
    const viewResultsBtn = document.getElementById('viewResultsBtn');
    
    // 重置状态
    runStatus.textContent = '正在准备运行测试...';
    runProgress.style.width = '0%';
    runProgress.setAttribute('aria-valuenow', 0);
    viewResultsBtn.disabled = true;
    
    // 显示模态框
    modal.show();
    
    // 调用后端API运行测试
    const testCases = testCaseId === 'all' 
        ? getFilteredTestCases() 
        : window.currentTestCases.filter(tc => tc.id == testCaseId);
    
    const totalTests = testCases.length;
    let completedTests = 0;
    
    // 构建请求体
    const requestBody = {
        test_cases: testCases.map(tc => tc.id)
    };
    
    // 发送运行请求
    fetch('http://localhost:19028/api/test-cases/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('运行测试失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('测试运行结果:', data);
        
        // 更新测试用例状态
        if (data.results) {
            data.results.forEach(result => {
                const index = window.currentTestCases.findIndex(tc => tc.id === result.test_case_id);
                if (index !== -1) {
                    window.currentTestCases[index].status = result.status;
                    window.currentTestCases[index].lastRun = result.run_time;
                    window.currentTestCases[index].duration = result.duration;
                }
            });
        }
        
        // 更新进度到100%
        runProgress.style.width = '100%';
        runProgress.setAttribute('aria-valuenow', 100);
        runStatus.textContent = `测试完成! 共运行 ${totalTests} 个测试用例`;
        viewResultsBtn.disabled = false;
        
        // 刷新界面
        updateStatistics(window.currentTestCases);
        const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
        if (viewMode === 'grid') {
            renderTestCasesGrid();
        } else {
            renderTestCasesList();
        }
    })
    .catch(error => {
        console.error('运行测试失败:', error);
        runStatus.textContent = '运行测试失败: ' + error.message;
        showNotification('运行测试失败: ' + error.message, 'error');
    });
}

// 隐藏运行测试模态框
function hideRunModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('runModal'));
    if (modal) modal.hide();
}

// 显示生成测试用例模态框
function showGenerateModal() {
    const modal = new bootstrap.Modal(document.getElementById('generateModal'));
    modal.show();
}

// 生成测试用例
function generateTestCases() {
    const apiDocSelect = document.getElementById('apiDocSelect');
    const basicCheck = document.getElementById('basicCheck');
    const scenarioCheck = document.getElementById('scenarioCheck');
    const boundaryCheck = document.getElementById('boundaryCheck');
    const exceptionCheck = document.getElementById('exceptionCheck');
    
    if (!apiDocSelect.value) {
        showNotification('请选择接口文档', 'warning');
        return;
    }
    
    const selectedTypes = [];
    if (basicCheck.checked) selectedTypes.push('basic');
    if (scenarioCheck.checked) selectedTypes.push('scenario');
    if (boundaryCheck.checked) selectedTypes.push('boundary');
    if (exceptionCheck.checked) selectedTypes.push('exception');
    
    if (selectedTypes.length === 0) {
        showNotification('请至少选择一种测试用例类型', 'warning');
        return;
    }
    
    // 关闭模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('generateModal'));
    modal.hide();
    
    // 显示加载状态
    showLoadingState();
    
    // 调用后端API生成测试用例
    fetch('http://localhost:19028/api/test-cases/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            task_id: apiDocSelect.value,
            test_types: selectedTypes
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('生成测试用例失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('测试用例生成结果:', data);
        
        // 添加到现有测试用例
        if (data.test_cases && data.test_cases.length > 0) {
            window.currentTestCases = [...window.currentTestCases, ...data.test_cases];
            
            // 更新统计和渲染
            updateStatistics(window.currentTestCases);
            const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
            if (viewMode === 'grid') {
                renderTestCasesGrid();
            } else {
                renderTestCasesList();
            }
            
            showNotification(`成功生成 ${data.test_cases.length} 个测试用例`, 'success');
        } else {
            showNotification('未生成任何测试用例', 'warning');
        }
    })
    .catch(error => {
        console.error('生成测试用例失败:', error);
        showNotification('生成测试用例失败: ' + error.message, 'error');
    })
    .finally(() => {
        hideLoadingState();
    });
}

// 生成模拟测试用例
function generateMockTestCases(apiDocId, types) {
    const apiNames = {
        'api_1': '用户登录API',
        'api_2': '用户信息API',
        'api_3': '订单管理API',
        'api_4': '订单查询API',
        'api_5': '购物车API',
        'api_6': '商品API',
        'api_7': '用户注册API',
        'api_8': '用户密码API',
        'api_9': '支付API'
    };
    
    const typeNames = {
        'basic': '基础测试',
        'scenario': '场景测试',
        'boundary': '边界值测试',
        'exception': '异常测试'
    };
    
    const newTestCases = [];
    let maxId = Math.max(...window.currentTestCases.map(tc => tc.id));
    
    types.forEach(type => {
        const testCase = {
            id: ++maxId,
            name: `${apiNames[apiDocId]} - ${typeNames[type]}`,
            description: `自动生成的${typeNames[type]}用例，用于测试${apiNames[apiDocId]}`,
            api: apiNames[apiDocId],
            apiId: apiDocId,
            type: type,
            status: 'passed',
            lastRun: '尚未运行',
            duration: '-',
            tags: [typeNames[type], '自动生成']
        };
        
        newTestCases.push(testCase);
    });
    
    return newTestCases;
}

// 加载API列表
function loadAPIList() {
    const apiFilter = document.getElementById('apiFilter');
    
    // 获取所有API
    const apis = [
        { id: 'api_1', name: '用户登录API' },
        { id: 'api_2', name: '用户信息API' },
        { id: 'api_3', name: '订单管理API' },
        { id: 'api_4', name: '订单查询API' },
        { id: 'api_5', name: '购物车API' },
        { id: 'api_6', name: '商品API' },
        { id: 'api_7', name: '用户注册API' },
        { id: 'api_8', name: '用户密码API' },
        { id: 'api_9', name: '支付API' }
    ];
    
    // 清空现有选项
    apiFilter.innerHTML = '<option value="">所有API</option>';
    
    // 添加API选项
    apis.forEach(api => {
        const option = document.createElement('option');
        option.value = api.id;
        option.textContent = api.name;
        apiFilter.appendChild(option);
    });
}

// 加载接口文档列表
function loadAPIDocList() {
    const apiDocSelect = document.getElementById('apiDocSelect');
    
    // 清空现有选项
    apiDocSelect.innerHTML = '<option value="">请选择接口文档</option>';
    
    // 从后端API获取API文档列表
    fetch('http://localhost:19028/api/docs/list', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取接口文档列表失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('从后端加载的接口文档列表:', data);
        
        // 如果没有接口文档，显示提示
        if (!data || data.length === 0) {
            const option = document.createElement('option');
            option.value = "";
            option.textContent = "暂无接口文档，请先解析接口文档";
            option.disabled = true;
            apiDocSelect.appendChild(option);
            return;
        }
        
        // 添加接口文档选项
        data.forEach(doc => {
            const option = document.createElement('option');
            option.value = doc.task_id;
            option.textContent = `${doc.source.name} (${doc.api_count}个API)`;
            apiDocSelect.appendChild(option);
        });
    })
    .catch(error => {
        console.error('加载接口文档列表失败:', error);
        
        // 如果加载失败，显示错误提示
        const option = document.createElement('option');
        option.value = "";
        option.textContent = "加载失败，请刷新页面重试";
        option.disabled = true;
        apiDocSelect.appendChild(option);
        
        showNotification('加载接口文档列表失败: ' + error.message, 'error');
    });
}

// 获取状态文本
function getStatusText(status) {
    const statusMap = {
        'passed': '通过',
        'failed': '失败',
        'skipped': '跳过',
        'running': '运行中'
    };
    
    return statusMap[status] || status;
}

// 获取类型文本
function getTypeText(type) {
    const typeMap = {
        'basic': '基础测试',
        'scenario': '场景测试',
        'boundary': '边界值测试',
        'exception': '异常测试'
    };
    
    return typeMap[type] || type;
}

// 显示加载状态
function showLoadingState() {
    const testCasesList = document.getElementById('testCasesList');
    testCasesList.innerHTML = `
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <div>正在加载测试用例...</div>
        </div>
    `;
}

// 隐藏加载状态
function hideLoadingState() {
    // 加载完成后，渲染列表会自动替换加载状态
}

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1050';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// 渲染空状态
function renderEmptyState() {
    const testCasesList = document.getElementById('testCasesList');
    testCasesList.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">
                <i class="fas fa-vial"></i>
            </div>
            <div class="empty-title">没有找到测试用例</div>
            <div class="empty-description">请尝试调整搜索条件或筛选器</div>
            <button class="btn btn-primary" id="generateFromEmptyBtn">
                <i class="fas fa-plus me-2"></i>生成测试用例
            </button>
        </div>
    `;
    
    // 绑定空状态下的生成按钮事件
    document.getElementById('generateFromEmptyBtn').addEventListener('click', function() {
        showGenerateModal();
    });
}