// API文档页面JavaScript

// 初始化函数 - 确保在主JS加载后再执行
function initApiDocsApp() {
    console.log('API文档页面初始化开始');
    
    try {
        // 确保所有必要的函数都已定义
        if (typeof initApiDocsPage === 'function') {
            initApiDocsPage();
            console.log('initApiDocsPage 执行完成');
        } else {
            console.error('initApiDocsPage 函数未定义');
        }
        
        if (typeof bindEventListeners === 'function') {
            bindEventListeners();
            console.log('bindEventListeners 执行完成');
        } else {
            console.error('bindEventListeners 函数未定义');
        }
        
        if (typeof loadApiData === 'function') {
            loadApiData();
            console.log('loadApiData 执行完成');
        } else {
            console.error('loadApiData 函数未定义');
        }
        
        console.log('API文档页面初始化完成');
    } catch (error) {
        console.error('API文档页面初始化过程中出错:', error);
    }
}

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('API文档页面 DOMContentLoaded 事件触发');
    
    // 延迟初始化，确保main.js中的函数已定义
    setTimeout(initApiDocsApp, 100);
});

// 如果DOM已经加载完成，直接执行初始化
if (document.readyState === 'loading') {
    // DOM还在加载中，等待DOMContentLoaded事件
    console.log('DOM正在加载中，等待DOMContentLoaded事件');
} else {
    // DOM已经加载完成，直接执行初始化
    console.log('DOM已经加载完成，直接执行初始化');
    setTimeout(initApiDocsApp, 100);
}

// 初始化API文档页面
function initApiDocsPage() {
    console.log('初始化API文档页面');
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 绑定事件监听器
function bindEventListeners() {
    console.log('绑定事件监听器');
    
    // 刷新按钮
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            console.log('刷新按钮被点击');
            loadApiData();
        });
    } else {
        console.error('找不到刷新按钮元素');
    }
    
    // 解析API文档按钮
    const parseBtn = document.getElementById('parseApiBtn');
    if (parseBtn) {
        parseBtn.addEventListener('click', function() {
            console.log('解析API文档按钮被点击');
            parseApiDocs();
        });
    } else {
        console.error('找不到解析API文档按钮元素');
    }
    
    // 搜索输入
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterApis();
        });
    }
    
    // 方法筛选
    const methodFilter = document.getElementById('methodFilter');
    if (methodFilter) {
        methodFilter.addEventListener('change', function() {
            filterApis();
        });
    }
    
    // 标签筛选
    const tagFilter = document.getElementById('tagFilter');
    if (tagFilter) {
        tagFilter.addEventListener('change', function() {
            filterApis();
        });
    }
    
    // 生成测试用例按钮
    const generateTestBtn = document.getElementById('generateTestBtn');
    if (generateTestBtn) {
        generateTestBtn.addEventListener('click', function() {
            generateTestCases();
        });
    }
}

// 加载API数据
function loadApiData() {
    console.log('开始加载API数据');
    showLoading();
    
    try {
        // 模拟API数据
        const mockApiData = [
        {
            id: 'api_1',
            method: 'POST',
            path: '/api/auth/login',
            summary: '用户登录',
            description: '用户使用用户名和密码进行登录，成功后返回访问令牌',
            tags: ['authentication'],
            parameters: [
                {
                    name: 'username',
                    type: 'string',
                    required: true,
                    description: '用户名'
                },
                {
                    name: 'password',
                    type: 'string',
                    required: true,
                    description: '密码'
                }
            ],
            responses: [
                {
                    code: 200,
                    description: '登录成功',
                    example: {
                        token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                        user: {
                            id: 'user_123',
                            username: 'testuser',
                            email: 'test@example.com'
                        }
                    }
                },
                {
                    code: 401,
                    description: '认证失败',
                    example: {
                        error: '用户名或密码错误'
                    }
                }
            ]
        },
        {
            id: 'api_2',
            method: 'POST',
            path: '/api/auth/register',
            summary: '用户注册',
            description: '新用户注册账号，需要提供用户名、密码和邮箱',
            tags: ['authentication'],
            parameters: [
                {
                    name: 'username',
                    type: 'string',
                    required: true,
                    description: '用户名'
                },
                {
                    name: 'password',
                    type: 'string',
                    required: true,
                    description: '密码'
                },
                {
                    name: 'email',
                    type: 'string',
                    required: true,
                    description: '邮箱地址'
                }
            ],
            responses: [
                {
                    code: 201,
                    description: '注册成功',
                    example: {
                        message: '用户注册成功',
                        user: {
                            id: 'user_456',
                            username: 'newuser',
                            email: 'newuser@example.com'
                        }
                    }
                },
                {
                    code: 400,
                    description: '请求参数错误',
                    example: {
                        error: '用户名已存在'
                    }
                }
            ]
        },
        {
            id: 'api_3',
            method: 'GET',
            path: '/api/user/profile',
            summary: '获取用户信息',
            description: '获取当前登录用户的详细信息',
            tags: ['user'],
            parameters: [],
            responses: [
                {
                    code: 200,
                    description: '获取成功',
                    example: {
                        id: 'user_123',
                        username: 'testuser',
                        email: 'test@example.com',
                        avatar: 'https://example.com/avatar.jpg',
                        created_at: '2023-01-01T00:00:00Z'
                    }
                },
                {
                    code: 401,
                    description: '未授权',
                    example: {
                        error: '请先登录'
                    }
                }
            ]
        },
        {
            id: 'api_4',
            method: 'PUT',
            path: '/api/user/profile',
            summary: '更新用户信息',
            description: '更新当前登录用户的信息',
            tags: ['user'],
            parameters: [
                {
                    name: 'username',
                    type: 'string',
                    required: false,
                    description: '用户名'
                },
                {
                    name: 'email',
                    type: 'string',
                    required: false,
                    description: '邮箱地址'
                },
                {
                    name: 'avatar',
                    type: 'string',
                    required: false,
                    description: '头像URL'
                }
            ],
            responses: [
                {
                    code: 200,
                    description: '更新成功',
                    example: {
                        message: '用户信息更新成功',
                        user: {
                            id: 'user_123',
                            username: 'updateduser',
                            email: 'updated@example.com',
                            avatar: 'https://example.com/newavatar.jpg'
                        }
                    }
                },
                {
                    code: 400,
                    description: '请求参数错误',
                    example: {
                        error: '邮箱格式不正确'
                    }
                }
            ]
        },
        {
            id: 'api_5',
            method: 'GET',
            path: '/api/products',
            summary: '获取产品列表',
            description: '获取所有产品的列表，支持分页和筛选',
            tags: ['e-commerce'],
            parameters: [
                {
                    name: 'page',
                    type: 'integer',
                    required: false,
                    description: '页码'
                },
                {
                    name: 'limit',
                    type: 'integer',
                    required: false,
                    description: '每页数量'
                },
                {
                    name: 'category',
                    type: 'string',
                    required: false,
                    description: '产品分类'
                }
            ],
            responses: [
                {
                    code: 200,
                    description: '获取成功',
                    example: {
                        products: [
                            {
                                id: 'prod_1',
                                name: '示例产品',
                                price: 99.99,
                                category: 'electronics'
                            }
                        ],
                        pagination: {
                            page: 1,
                            limit: 10,
                            total: 50
                        }
                    }
                }
            ]
        },
        {
            id: 'api_6',
            method: 'POST',
            path: '/api/products',
            summary: '创建产品',
            description: '创建新产品',
            tags: ['e-commerce'],
            parameters: [
                {
                    name: 'name',
                    type: 'string',
                    required: true,
                    description: '产品名称'
                },
                {
                    name: 'price',
                    type: 'number',
                    required: true,
                    description: '产品价格'
                },
                {
                    name: 'category',
                    type: 'string',
                    required: true,
                    description: '产品分类'
                }
            ],
            responses: [
                {
                    code: 201,
                    description: '创建成功',
                    example: {
                        message: '产品创建成功',
                        product: {
                            id: 'prod_new',
                            name: '新产品',
                            price: 149.99,
                            category: 'electronics'
                        }
                    }
                }
            ]
        },
        {
            id: 'api_7',
            method: 'POST',
            path: '/api/cart/add',
            summary: '添加到购物车',
            description: '将产品添加到购物车',
            tags: ['shopping'],
            parameters: [
                {
                    name: 'product_id',
                    type: 'string',
                    required: true,
                    description: '产品ID'
                },
                {
                    name: 'quantity',
                    type: 'integer',
                    required: true,
                    description: '数量'
                }
            ],
            responses: [
                {
                    code: 200,
                    description: '添加成功',
                    example: {
                        message: '产品已添加到购物车',
                        cart: {
                            items: [
                                {
                                    product_id: 'prod_1',
                                    quantity: 2
                                }
                            ],
                            total: 199.98
                        }
                    }
                }
            ]
        },
        {
            id: 'api_8',
            method: 'GET',
            path: '/api/cart',
            summary: '获取购物车',
            description: '获取当前用户的购物车内容',
            tags: ['shopping'],
            parameters: [],
            responses: [
                {
                    code: 200,
                    description: '获取成功',
                    example: {
                        items: [
                            {
                                product_id: 'prod_1',
                                name: '示例产品',
                                price: 99.99,
                                quantity: 2
                            }
                        ],
                        total: 199.98
                    }
                }
            ]
        },
        {
            id: 'api_9',
            method: 'DELETE',
            path: '/api/cart/remove',
            summary: '从购物车移除',
            description: '从购物车中移除产品',
            tags: ['shopping'],
            parameters: [
                {
                    name: 'product_id',
                    type: 'string',
                    required: true,
                    description: '产品ID'
                }
            ],
            responses: [
                {
                    code: 200,
                    description: '移除成功',
                    example: {
                        message: '产品已从购物车移除',
                        cart: {
                            items: [],
                            total: 0
                        }
                    }
                },
                {
                    code: 404,
                    description: '产品不在购物车中',
                    example: {
                        error: '产品不在购物车中'
                    }
                }
            ]
        }
    ];
    
    // 渲染API列表
    renderApiList(mockApiData);
    
    // 更新API统计
    updateApiStats(mockApiData);
    
    // 更新筛选器选项
    updateFilterOptions(mockApiData);
    
    // 存储API数据供后续使用
    window.apiData = mockApiData;
    
    hideLoading();
    console.log('API数据加载完成');
    } catch (error) {
        console.error('加载API数据时出错:', error);
        hideLoading();
        showNotification('加载API数据失败', 'danger');
    }
}

// 渲染API列表
function renderApiList(apis) {
    const apiList = document.getElementById('apiList');
    if (!apiList) return;
    
    apiList.innerHTML = '';
    
    if (apis.length === 0) {
        apiList.innerHTML = '<div class="alert alert-info">没有找到匹配的API</div>';
        return;
    }
    
    apis.forEach(api => {
        const apiItem = document.createElement('div');
        apiItem.className = 'api-item card mb-3';
        apiItem.dataset.method = api.method;
        apiItem.dataset.tags = api.tags.join(',');
        apiItem.dataset.searchText = `${api.path} ${api.summary} ${api.description}`.toLowerCase();
        
        const methodClass = api.method === 'GET' ? 'success' : 
                           api.method === 'POST' ? 'primary' : 
                           api.method === 'PUT' ? 'warning' : 
                           api.method === 'DELETE' ? 'danger' : 'secondary';
        
        apiItem.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title">
                            <span class="badge bg-${methodClass} me-2">${api.method}</span>
                            ${api.path}
                        </h5>
                        <p class="card-text">${api.summary}</p>
                        <div class="mt-2">
                            ${api.tags.map(tag => `<span class="badge bg-light text-dark me-1">${tag}</span>`).join('')}
                        </div>
                    </div>
                    <button class="btn btn-outline-primary btn-sm" onclick="viewApiDetail('${api.id}')">
                        查看详情
                    </button>
                </div>
            </div>
        `;
        
        apiList.appendChild(apiItem);
    });
}

// 更新API统计
function updateApiStats(apis) {
    const totalApis = document.getElementById('totalApis');
    const getApis = document.getElementById('getApis');
    const postApis = document.getElementById('postApis');
    const otherApis = document.getElementById('otherApis');
    
    if (totalApis) totalApis.textContent = apis.length;
    
    const getCount = apis.filter(api => api.method === 'GET').length;
    if (getApis) getApis.textContent = getCount;
    
    const postCount = apis.filter(api => api.method === 'POST').length;
    if (postApis) postApis.textContent = postCount;
    
    const otherCount = apis.length - getCount - postCount;
    if (otherApis) otherApis.textContent = otherCount;
}

// 更新筛选器选项
function updateFilterOptions(apiData) {
    // 更新标签筛选器
    const tagFilter = document.getElementById('tagFilter');
    if (tagFilter) {
        const tags = [...new Set(apiData.flatMap(api => api.tags))];
        tagFilter.innerHTML = '<option value="">所有标签</option>';
        tags.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag;
            option.textContent = tag;
            tagFilter.appendChild(option);
        });
    }
}

// 筛选API
function filterApis() {
    const searchInput = document.getElementById('searchInput');
    const methodFilter = document.getElementById('methodFilter');
    const tagFilter = document.getElementById('tagFilter');
    
    if (!searchInput || !methodFilter || !tagFilter) return;
    
    const searchTerm = searchInput.value.toLowerCase();
    const selectedMethod = methodFilter.value;
    const selectedTag = tagFilter.value;
    
    const apiItems = document.querySelectorAll('.api-item');
    
    apiItems.forEach(item => {
        let show = true;
        
        // 搜索筛选
        if (searchTerm && !item.dataset.searchText.includes(searchTerm)) {
            show = false;
        }
        
        // 方法筛选
        if (selectedMethod && item.dataset.method !== selectedMethod) {
            show = false;
        }
        
        // 标签筛选
        if (selectedTag && !item.dataset.tags.includes(selectedTag)) {
            show = false;
        }
        
        item.style.display = show ? 'block' : 'none';
    });
}

// 查看API详情
function viewApiDetail(apiId) {
    const api = window.apiData.find(a => a.id === apiId);
    if (!api) return;
    
    const modalContent = document.getElementById('apiDetailContent');
    if (!modalContent) return;
    
    // 构建API详情HTML
    let detailHtml = `
        <ul class="nav nav-tabs api-detail-tabs" id="apiDetailTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="basic-tab" data-bs-toggle="tab" data-bs-target="#basic" type="button" role="tab">基本信息</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="params-tab" data-bs-toggle="tab" data-bs-target="#params" type="button" role="tab">参数</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="responses-tab" data-bs-toggle="tab" data-bs-target="#responses" type="button" role="tab">响应</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="example-tab" data-bs-toggle="tab" data-bs-target="#example" type="button" role="tab">示例</button>
            </li>
        </ul>
        <div class="tab-content" id="apiDetailTabContent">
            <div class="tab-pane fade show active" id="basic" role="tabpanel">
                <div class="mt-3">
                    <div class="row mb-3">
                        <div class="col-sm-3"><strong>方法:</strong></div>
                        <div class="col-sm-9"><span class="api-method method-${api.method.toLowerCase()}">${api.method}</span></div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-sm-3"><strong>路径:</strong></div>
                        <div class="col-sm-9"><code>${api.path}</code></div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-sm-3"><strong>描述:</strong></div>
                        <div class="col-sm-9">${api.description}</div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-sm-3"><strong>标签:</strong></div>
                        <div class="col-sm-9">
                            ${api.tags.map(tag => `<span class="badge bg-light text-dark me-1">${tag}</span>`).join('')}
                        </div>
                    </div>
                </div>
            </div>
            <div class="tab-pane fade" id="params" role="tabpanel">
                <div class="mt-3">
                    ${api.parameters.length > 0 ? `
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>参数名</th>
                                    <th>类型</th>
                                    <th>必需</th>
                                    <th>描述</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${api.parameters.map(param => `
                                    <tr>
                                        <td>${param.name}</td>
                                        <td>${param.type}</td>
                                        <td>${param.required ? '<span class="badge bg-danger">是</span>' : '<span class="badge bg-secondary">否</span>'}</td>
                                        <td>${param.description}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    ` : '<p>此API没有参数。</p>'}
                </div>
            </div>
            <div class="tab-pane fade" id="responses" role="tabpanel">
                <div class="mt-3">
                    ${api.responses.map(response => `
                        <div class="card mb-3">
                            <div class="card-header ${response.code >= 200 && response.code < 300 ? 'bg-success text-white' : 'bg-danger text-white'}">
                                ${response.code} - ${response.description}
                            </div>
                            <div class="card-body">
                                <pre class="code-block json-example">${formatJson(response.example)}</pre>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="tab-pane fade" id="example" role="tabpanel">
                <div class="mt-3">
                    <div class="api-highlight">
                        <div class="api-highlight-title">请求示例</div>
                        <div class="api-highlight-content">
                            <pre class="code-block">${generateExampleRequest(api)}</pre>
                        </div>
                    </div>
                    <div class="api-highlight">
                        <div class="api-highlight-title">响应示例</div>
                        <div class="api-highlight-content">
                            <pre class="code-block json-example">${formatJson(api.responses[0].example)}</pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    modalContent.innerHTML = detailHtml;
    
    // 显示模态框
    const modalElement = document.getElementById('apiDetailModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
    
    // 保存当前API ID供生成测试用例使用
    window.currentApiId = apiId;
}

// 生成示例请求
function generateExampleRequest(api) {
    let request = `${api.method} ${api.path} HTTP/1.1\n`;
    request += 'Host: example.com\n';
    request += 'Content-Type: application/json\n';
    
    if (api.method !== 'GET') {
        const body = {};
        api.parameters.forEach(param => {
            if (param.required) {
                if (param.type === 'string') {
                    body[param.name] = param.name.includes('email') ? 'example@example.com' : 'example_value';
                } else if (param.type === 'integer') {
                    body[param.name] = 1;
                } else if (param.type === 'boolean') {
                    body[param.name] = true;
                } else {
                    body[param.name] = {};
                }
            }
        });
        
        request += `Content-Length: ${JSON.stringify(body).length}\n\n`;
        request += JSON.stringify(body, null, 2);
    } else {
        request += '\n';
    }
    
    return request;
}

// 格式化JSON
function formatJson(json) {
    return JSON.stringify(json, null, 2);
}

// 为特定API生成测试用例
function generateTestForApi(apiId) {
    viewApiDetail(apiId);
    // 模态框打开后，用户可以点击"生成测试用例"按钮
}

// 生成测试用例
function generateTestCases() {
    const generateBtn = document.getElementById('generateTestBtn');
    if (!generateBtn) return;
    
    // 显示加载状态
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 生成中...';
    
    // 模拟生成过程
    setTimeout(() => {
        // 重置按钮状态
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-vial me-2"></i>生成测试用例';
        
        // 显示成功消息
        showNotification('测试用例生成成功！', 'success');
        
        // 跳转到测试用例页面
        window.location.href = 'test-cases.html';
    }, 2000);
}

// 解析API文档
function parseApiDocs() {
    console.log('开始解析API文档');
    const parseBtn = document.getElementById('parseApiBtn');
    if (!parseBtn) return;
    
    // 显示加载状态
    parseBtn.disabled = true;
    parseBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 解析中...';
    
    showNotification('正在解析API文档...', 'info');
    
    // 模拟解析过程
    setTimeout(() => {
        // 重置按钮状态
        parseBtn.disabled = false;
        parseBtn.innerHTML = '<i class="fas fa-file-import me-2"></i>解析API文档';
        
        showNotification('API文档解析成功！', 'success');
        
        // 重新加载数据
        loadApiData();
    }, 2000);
}

// 显示加载状态
function showLoading() {
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.id = 'loadingOverlay';
    loadingOverlay.innerHTML = '<div class="loading-spinner"></div>';
    document.body.appendChild(loadingOverlay);
}

// 隐藏加载状态
function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// 显示提示消息（兼容旧代码）
function showToast(message, type = 'info') {
    showNotification(message, type);
}

// 初始化图表
function initCharts() {
    // 这里可以初始化各种图表
    console.log('初始化图表');
}