// 接口文档页面JavaScript

// 文档上传相关全局变量
let uploadedFiles = [];
let currentFile = null;
let parsedApiData = null;

// 场景和关联关系相关变量
let scenes = [];
let relations = [];

// 从URL获取文档ID
function getDocIdFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('doc_id') || urlParams.get('id');
}

// 初始化函数 - 确保在主JS加载后再执行
function initApiDocsApp() {
    console.log('接口文档页面初始化开始 - v1.1');
    
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
        
        // 初始化文档上传功能
        if (typeof initDocumentUpload === 'function') {
            initDocumentUpload();
            console.log('initDocumentUpload 执行完成');
        }
        
        // 加载已上传的文件列表
        if (typeof loadUploadedFiles === 'function') {
            loadUploadedFiles();
            console.log('loadUploadedFiles 执行完成');
        }
        
        // 初始化场景和关联关系
        if (typeof loadScenesAndRelations === 'function') {
            loadScenesAndRelations();
            console.log('loadScenesAndRelations 执行完成');
        }
        
        console.log('接口文档页面初始化完成');
    } catch (error) {
        console.error('接口文档页面初始化过程中出错:', error);
    }
}

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('接口文档页面 DOMContentLoaded 事件触发');
    console.log('检查全局API对象:', typeof window.API);
    console.log('检查全局bootstrap对象:', typeof window.bootstrap);
    
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

// 初始化接口文档页面
function initApiDocsPage() {
    console.log('初始化接口文档页面');
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 绑定事件监听器
function bindEventListeners() {
    console.log('绑定事件监听器');
    
    // 监听API列表更新事件
    window.addEventListener('apiListUpdated', function(event) {
        console.log('收到API列表更新事件:', event.detail);
        loadApiData();
    });
    
    // 检查localStorage中的API列表更新标记
    const apiListUpdated = localStorage.getItem('apiListUpdated');
    if (apiListUpdated) {
        console.log('检测到API列表已更新标记，刷新列表');
        localStorage.removeItem('apiListUpdated');
        loadApiData();
    }
    
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
    
    // 添加场景按钮
    const addSceneBtn = document.getElementById('addSceneBtn');
    if (addSceneBtn) {
        addSceneBtn.addEventListener('click', function() {
            // 清空表单
            document.getElementById('addSceneForm').reset();
            // 填充API列表
            populateApiCheckboxList();
            // 显示模态框
            const sceneModal = new bootstrap.Modal(document.getElementById('addSceneModal'));
            sceneModal.show();
        });
    }
    
    // 添加关联关系按钮
    const addRelationBtn = document.getElementById('addRelationBtn');
    if (addRelationBtn) {
        addRelationBtn.addEventListener('click', function() {
            // 清空表单
            document.getElementById('addRelationForm').reset();
            // 填充API选项
            populateApiSelectOptions();
            // 显示模态框
            const relationModal = new bootstrap.Modal(document.getElementById('addRelationModal'));
            relationModal.show();
        });
    }
    
    // 保存场景按钮
    const saveSceneBtn = document.getElementById('saveSceneBtn');
    if (saveSceneBtn) {
        saveSceneBtn.addEventListener('click', function() {
            saveScene();
        });
    }
    
    // 保存关联关系按钮
    const saveRelationBtn = document.getElementById('saveRelationBtn');
    if (saveRelationBtn) {
        saveRelationBtn.addEventListener('click', function() {
            saveRelation();
        });
    }
    
    // 置信度滑块
    const confidenceSlider = document.getElementById('confidence');
    const confidenceValue = document.getElementById('confidenceValue');
    if (confidenceSlider && confidenceValue) {
        confidenceSlider.addEventListener('input', function() {
            confidenceValue.textContent = this.value + '%';
        });
    }
    
    // 添加场景模态框显示事件
    const addSceneModal = document.getElementById('addSceneModal');
    if (addSceneModal) {
        addSceneModal.addEventListener('show.bs.modal', function() {
            populateApiCheckboxList();
        });
    }
    
    // 添加关联关系模态框显示事件
    const addRelationModal = document.getElementById('addRelationModal');
    if (addRelationModal) {
        addRelationModal.addEventListener('show.bs.modal', function() {
            populateApiSelectOptions();
        });
    }
}

// 加载API数据
function loadApiData() {
    console.log('开始加载API数据');
    showLoading();
    
    // 尝试从后端加载API数据
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.LIST), {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('加载API数据失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('从后端加载的API数据:', data);
        
        // 如果后端有数据，使用后端数据
        if (data && data.length > 0) {
            renderApiList(data);
            updateApiStats(data);
            updateFilterOptions(data);
            hideLoading();
            return;
        }
        
        // 如果后端没有数据，使用模拟数据
        console.log('后端没有API数据，使用模拟数据');
        const mockApiData = getMockApiData();
        renderApiList(mockApiData);
        updateApiStats(mockApiData);
        updateFilterOptions(mockApiData);
        hideLoading();
    })
    .catch(error => {
        console.error('加载API数据失败，使用模拟数据:', error);
        
        // 如果加载失败，使用模拟数据
        const mockApiData = getMockApiData();
        renderApiList(mockApiData);
        updateApiStats(mockApiData);
        updateFilterOptions(mockApiData);
        hideLoading();
    });
}

// 获取模拟API数据
function getMockApiData() {
    return [
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
    
    // 存储API数据供后续使用
    window.apiData = apis;
    
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
async function generateTestCases() {
    const generateBtn = document.getElementById('generateTestBtn');
    if (!generateBtn) return;
    
    // 获取当前API ID
    const apiId = window.currentApiId;
    if (!apiId) {
        showSmartTestNotification('请先选择一个API', 'warning');
        return;
    }
    
    // 显示加载状态
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 生成中...';
    
    try {
        // 从全局API数据中获取当前API信息
        const api = window.apiData.find(item => item.id === apiId);
        if (!api) {
            throw new Error('找不到API信息');
        }
        
        // 获取文档ID
        const docTaskId = window.currentDocId || getDocIdFromUrl();
        if (!docTaskId) {
            throw new Error('文档ID缺失，请刷新页面重试');
        }
        
        // 准备请求数据
        const requestData = {
            api_path: api.path,
            api_method: api.method
        };
        
        // 调用后端API生成测试用例
        const response = await fetch(API_CONFIG.buildUrl(API_CONFIG.DOCS.GENERATE_TEST_CASES.replace('{doc_task_id}', docTaskId)), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '生成测试用例失败');
        }
        
        const result = await response.json();
        
        // 显示成功消息
        showSmartTestNotification(`测试用例生成成功！共生成 ${result.data.test_cases_count || 0} 个测试用例`, 'success');
        
        // 关闭API详情模态框
        const modalElement = document.getElementById('apiDetailModal');
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }
        
        // 跳转到测试用例页面
        setTimeout(() => {
            window.location.href = 'test-cases.html';
        }, 1000);
        
    } catch (error) {
        console.error('生成测试用例失败:', error);
        showSmartTestNotification('生成测试用例失败: ' + error.message, 'error');
    } finally {
        // 重置按钮状态
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-vial me-2"></i>生成测试用例';
    }
}

// 快速解析飞书API
function quickParseFeishuApi() {
    console.log('开始快速解析飞书API');
    
    // 创建预设URL列表模态框
    const urlModal = document.createElement('div');
    urlModal.className = 'modal fade';
    urlModal.id = 'feishuUrlModal';
    urlModal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-feather-alt text-primary me-2"></i>
                        飞书接口文档解析
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="feishuApiUrl" class="form-label">选择或输入飞书接口文档URL</label>
                        <select class="form-select mb-2" id="feishuApiPreset">
                            <option value="">-- 选择预设API --</option>
                            <option value="https://open.feishu.cn/document/server-docs/im-v1/message/create">发送消息</option>
                            <option value="https://open.feishu.cn/document/server-docs/im-v1/message/list">获取消息列表</option>
                            <option value="https://open.feishu.cn/document/server-docs/im-v1/message/recv">接收消息</option>
                            <option value="https://open.feishu.cn/document/server-docs/contact/v3/users/get">获取用户信息</option>
                            <option value="https://open.feishu.cn/document/server-docs/contact/v3/users/batch_get_id">批量获取用户ID</option>
                            <option value="https://open.feishu.cn/document/server-docs/contact/v3/department/list">获取部门列表</option>
                            <option value="https://open.feishu.cn/document/server-docs/drive/v1/files/upload_all">上传文件</option>
                            <option value="https://open.feishu.cn/document/server-docs/drive/v1/files/download">下载文件</option>
                            <option value="https://open.feishu.cn/document/server-docs/application-v6/tenant/custom_app_auth">应用授权</option>
                        </select>
                        <input type="url" class="form-control" id="feishuApiUrl" placeholder="https://open.feishu.cn/document/server-docs/...">
                        <div class="form-text">支持飞书开放平台接口文档URL，可以从下拉列表选择预设API或输入自定义URL</div>
                    </div>
                    <div class="alert alert-light">
                        <h6><i class="fas fa-lightbulb text-warning me-1"></i> 使用提示</h6>
                        <ul class="mb-0 small">
                            <li>飞书接口文档通常包含在 https://open.feishu.cn/document/ 域名下</li>
                            <li>系统会自动从文档中提取API端点、参数和响应信息</li>
                            <li>解析完成后，API将自动添加到当前API列表中</li>
                        </ul>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                    <button type="button" class="btn btn-primary" id="confirmFeishuParseBtn">
                        <i class="fas fa-rocket me-1"></i>解析飞书API
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(urlModal);
    
    // 显示模态框
    const modal = new bootstrap.Modal(urlModal);
    modal.show();
    
    // 预设URL选择事件
    const presetSelect = document.getElementById('feishuApiPreset');
    const urlInput = document.getElementById('feishuApiUrl');
    if (presetSelect && urlInput) {
        presetSelect.addEventListener('change', function() {
            if (this.value) {
                urlInput.value = this.value;
            }
        });
    }
    
    // 绑定确认解析按钮事件
    const confirmBtn = document.getElementById('confirmFeishuParseBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            const url = urlInput.value.trim();
            
            if (!url) {
                showSmartTestNotification('请输入有效的飞书接口文档URL', 'warning');
                return;
            }
            
            // 验证是否是飞书API文档URL
            if (!url.includes('open.feishu.cn/document/')) {
                showSmartTestNotification('请输入有效的飞书接口文档URL，应包含 open.feishu.cn/document/', 'warning');
                return;
            }
            
            // 关闭模态框
            modal.hide();
            
            // 调用解析函数
            parseApiDocument(url, '飞书API');
        });
    }
}

// 解析接口文档
function parseApiDocs() {
    console.log('开始解析接口文档');
    
    // 创建URL输入模态框
    const urlModal = document.createElement('div');
    urlModal.className = 'modal fade';
    urlModal.id = 'urlInputModal';
    urlModal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">输入接口文档URL</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="apiDocUrl" class="form-label">接口文档URL</label>
                        <input type="url" class="form-control" id="apiDocUrl" placeholder="https://open.feishu.cn/document/...">
                        <div class="form-text">支持飞书开放平台接口文档URL</div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                    <button type="button" class="btn btn-primary" id="confirmParseBtn">解析</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(urlModal);
    
    // 显示模态框
    const modal = new bootstrap.Modal(urlModal);
    modal.show();
    
    // 绑定确认解析按钮事件
    const confirmBtn = document.getElementById('confirmParseBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            const urlInput = document.getElementById('apiDocUrl');
            const url = urlInput.value.trim();
            
            if (!url) {
                showSmartTestNotification('请输入有效的接口文档URL', 'warning');
                return;
            }
            
            // 关闭模态框
            modal.hide();
            
            // 调用解析函数
            parseApiDocument(url, '接口文档');
        });
    }
}

// 通用解析接口文档函数
function parseApiDocument(url, docType) {
    console.log('开始解析接口文档:', url);
    const parseBtn = document.getElementById('parseApiBtn');
    const quickParseBtn = document.getElementById('quickParseFeishuBtn');
    
    // 显示加载状态
    if (parseBtn) {
        parseBtn.disabled = true;
        parseBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 解析中...';
    }
    
    if (quickParseBtn) {
        quickParseBtn.disabled = true;
        quickParseBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 解析中...';
    }
    
    showSmartTestNotification(`正在解析${docType}...`, 'info');
    
    // 调用后端API解析接口
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    const parseUrl = baseUrl + (docsEndpoint.PARSE_URL || '/api/docs/parse-url');
    
    fetch(parseUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('解析失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('接口文档解析成功:', data);
        showSmartTestNotification(`${docType}解析成功！`, 'success');
        
        // 重新加载数据
        loadApiData();
    })
    .catch(error => {
        console.error('解析接口文档失败:', error);
        showSmartTestNotification(`解析${docType}失败: ` + error.message, 'error');
    })
    .finally(() => {
        // 重置按钮状态
        if (parseBtn) {
            parseBtn.disabled = false;
            parseBtn.innerHTML = '<i class="fas fa-file-import me-1"></i>解析接口文档';
        }
        
        if (quickParseBtn) {
            quickParseBtn.disabled = false;
            quickParseBtn.innerHTML = '<i class="fas fa-rocket me-1"></i>快速解析';
        }
        
        // 移除模态框
        setTimeout(() => {
            const feishuModal = document.getElementById('feishuUrlModal');
            const urlModal = document.getElementById('urlInputModal');
            
            if (feishuModal && document.body.contains(feishuModal)) {
                document.body.removeChild(feishuModal);
            }
            
            if (urlModal && document.body.contains(urlModal)) {
                document.body.removeChild(urlModal);
            }
        }, 500);
    });
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
    showSmartTestNotification(message, type);
}

// 初始化图表
function initCharts() {
    // 这里可以初始化各种图表
    console.log('初始化图表');
}

// ============ 文档上传功能相关函数 ============

// 初始化文档上传功能
function initDocumentUpload() {
    console.log('初始化文档上传功能');
    
    // 绑定文档上传相关事件
    bindDocumentUploadEvents();
}

// 绑定文档上传相关事件
function bindDocumentUploadEvents() {
    const uploadModal = document.getElementById('documentUploadModal');
    if (!uploadModal) return;
    
    // 文件选择按钮
    const selectFileBtn = document.getElementById('selectFileBtn');
    if (selectFileBtn) {
        selectFileBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.click();
        });
    }
    
    // 文件选择变化
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
            }
        });
    }
    
    // 拖拽上传区域
    const uploadContainer = document.getElementById('uploadContainer');
    if (uploadContainer) {
        // 防止默认拖拽行为
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadContainer.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        // 拖拽样式
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadContainer.addEventListener(eventName, function() {
                uploadContainer.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadContainer.addEventListener(eventName, function() {
                uploadContainer.classList.remove('dragover');
            }, false);
        });
        
        // 处理拖拽文件
        uploadContainer.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                handleFileUpload(files[0]);
            }
        }, false);
    }
}

// 防止默认行为
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// 处理文件上传
function handleFileUpload(file) {
    console.log('处理文件上传:', file.name);
    
    // 验证文件类型
    if (!isValidFileType(file.name)) {
        showSmartTestNotification('不支持的文件类型，请上传 OpenAPI 3.0.0 JSON 或 YAML 格式的文件', 'error');
        return;
    }
    
    // 验证文件大小 (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showSmartTestNotification('文件大小不能超过 10MB', 'error');
        return;
    }
    
    // 保存当前文件
    currentFile = file;
    
    // 显示上传进度
    showUploadProgress();
    
    // 创建FormData
    const formData = new FormData();
    formData.append('file', file);
    
    // 上传文件
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.UPLOAD), {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('上传失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('上传成功:', data);
        
        // 更新上传进度
        updateUploadProgress(100);
        
        // 添加到已上传文件列表
        addToUploadedFiles(file, data);
        
        // 延迟一下，让用户看到100%进度
        setTimeout(() => {
            hideUploadProgress();
            showProcessingStatus();
            
            // 解析文档
            parseDocument(data.file_id);
        }, 500);
    })
    .catch(error => {
        console.error('上传失败:', error);
        hideUploadProgress();
        showUploadError(error.message);
    });
}

// 验证文件类型
function isValidFileType(filename) {
    const validExtensions = ['.json', '.yaml', '.yml'];
    const fileExtension = filename.substring(filename.lastIndexOf('.')).toLowerCase();
    return validExtensions.includes(fileExtension);
}

// 显示上传进度
function showUploadProgress() {
    const uploadContainer = document.getElementById('uploadContainer');
    const uploadProgress = document.getElementById('uploadProgress');
    
    if (uploadContainer) {
        uploadContainer.classList.add('uploading');
    }
    
    if (uploadProgress) {
        uploadProgress.style.display = 'block';
        updateUploadProgress(0);
    }
}

// 更新上传进度
function updateUploadProgress(percent) {
    const uploadPercent = document.getElementById('uploadPercent');
    const uploadProgressBar = document.getElementById('uploadProgressBar');
    
    if (uploadPercent) {
        uploadPercent.textContent = `${percent}%`;
    }
    
    if (uploadProgressBar) {
        uploadProgressBar.style.width = `${percent}%`;
    }
}

// 隐藏上传进度
function hideUploadProgress() {
    const uploadContainer = document.getElementById('uploadContainer');
    const uploadProgress = document.getElementById('uploadProgress');
    
    if (uploadContainer) {
        uploadContainer.classList.remove('uploading');
    }
    
    if (uploadProgress) {
        uploadProgress.style.display = 'none';
    }
}

// 显示上传错误
function showUploadError(message) {
    const uploadContainer = document.getElementById('uploadContainer');
    
    if (uploadContainer) {
        uploadContainer.classList.add('error');
        setTimeout(() => {
            uploadContainer.classList.remove('error');
        }, 3000);
    }
    
    showSmartTestNotification(message, 'error');
}

// 显示处理状态
function showProcessingStatus() {
    const processingStatus = document.getElementById('processingStatus');
    
    if (processingStatus) {
        processingStatus.style.display = 'block';
    }
}

// 隐藏处理状态
function hideProcessingStatus() {
    const processingStatus = document.getElementById('processingStatus');
    
    if (processingStatus) {
        processingStatus.style.display = 'none';
    }
}

// 解析文档
function parseDocument(fileId) {
    console.log('解析文档:', fileId);
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    const parseUrl = baseUrl + (docsEndpoint.PARSE || '/api/docs/parse') + `/${fileId}`;
    
    fetch(parseUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('解析失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('解析成功:', data);
        
        // 保存解析结果
        parsedApiData = data;
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 关闭上传模态框
        const uploadModal = document.getElementById('documentUploadModal');
        if (uploadModal) {
            const modal = bootstrap.Modal.getInstance(uploadModal);
            if (modal) modal.hide();
        }
        
        // 刷新接口文档列表
        loadApiData();
        
        // 通知成功
        showSmartTestNotification('文档解析成功', 'success');
    })
    .catch(error => {
        console.error('解析失败:', error);
        hideProcessingStatus();
        showSmartTestNotification(error.message, 'error');
    });
}

// 添加到已上传文件列表
function addToUploadedFiles(file, data) {
    const fileInfo = {
        id: data.file_id,
        name: file.name,
        size: file.size,
        uploadTime: new Date().toISOString(),
        status: 'uploaded'
    };
    
    uploadedFiles.push(fileInfo);
    
    // 更新文件列表显示
    updateFileListDisplay();
}

// 更新文件列表显示
function updateFileListDisplay() {
    console.log('updateFileListDisplay函数被调用');
    const fileList = document.getElementById('uploadedFileList');
    console.log('uploadedFileList元素:', fileList);
    
    if (!fileList) {
        console.error('找不到uploadedFileList元素');
        return;
    }
    
    console.log('uploadedFiles数组:', uploadedFiles);
    console.log('uploadedFiles数组长度:', uploadedFiles.length);
    
    if (uploadedFiles.length === 0) {
        fileList.innerHTML = '<p class="text-muted">暂无已上传文件</p>';
        console.log('显示"暂无已上传文件"');
        return;
    }
    
    // 清空现有列表
    fileList.innerHTML = '';
    
    uploadedFiles.forEach(file => {
        const statusIcon = file.status === 'uploaded' ? 
            '<i class="fas fa-check-circle text-success"></i>' : 
            '<i class="fas fa-exclamation-circle text-danger"></i>';
        
        const statusText = file.status === 'uploaded' ? '已上传' : '上传失败';
        
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-icon-small">
                <i class="fas fa-file-code"></i>
            </div>
            <div class="file-info">
                <div class="file-name">${file.name}</div>
                <div class="file-size">${formatFileSize(file.size)} · ${formatDate(file.uploadTime)}</div>
            </div>
            <div class="file-status">
                ${statusIcon} ${statusText}
            </div>
            <div class="file-actions">
                <button class="btn btn-sm btn-outline-primary" onclick="viewFileDetails('${file.id}')">
                    <i class="fas fa-eye"></i> 查看
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('${file.id}')">
                    <i class="fas fa-trash"></i> 删除
                </button>
            </div>
        `;
        
        fileList.appendChild(fileItem);
        console.log('添加文件项:', file.name);
    });
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// 查看文件详情
function viewFileDetails(fileId) {
    // 跳转到测试中心页面并指定文件ID
    window.location.href = `test-center.html?fileId=${fileId}`;
}

// 删除文件
function deleteFile(fileId) {
    if (!confirm('确定要删除这个文件吗？')) {
        return;
    }
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    const deleteUrl = baseUrl + (docsEndpoint.DELETE || '/api/docs/delete') + `/${fileId}`;
    
    fetch(deleteUrl, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('删除失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('删除成功:', data);
        
        // 从列表中移除
        uploadedFiles = uploadedFiles.filter(file => file.id !== fileId);
        
        // 更新显示
        updateFileListDisplay();
        
        showSmartTestNotification('文件删除成功', 'success');
    })
    .catch(error => {
        console.error('删除失败:', error);
        showSmartTestNotification(error.message, 'error');
    });
}

// 加载已上传的文件列表
function loadUploadedFiles() {
    console.log('开始加载已上传文件列表...');
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    const listUrl = baseUrl + (docsEndpoint.OPENAPI_LIST || '/api/docs/openapi/list');
    
    fetch(listUrl, {
        method: 'GET'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('加载文件列表失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('已上传文件列表:', data);
        
        if (data && data.data && data.data.length > 0) {
            // 将后端返回的文档格式转换为前端期望的格式
            uploadedFiles = data.data.map(doc => ({
                id: doc.file_id,
                name: doc.file_name,
                size: doc.file_size,
                uploadTime: doc.upload_time,
                status: doc.status
            }));
            console.log('转换后的文件列表:', uploadedFiles);
        } else {
            // 如果没有文件，设置为空数组
            uploadedFiles = [];
            console.log('没有找到已上传的文件');
        }
        
        // 无论是否有数据，都要更新显示
        console.log('调用updateFileListDisplay函数');
        updateFileListDisplay();
    })
    .catch(error => {
        console.error('加载文件列表失败:', error);
        // 加载失败时也要更新显示，显示错误信息
        const fileList = document.getElementById('uploadedFileList');
        if (fileList) {
            fileList.innerHTML = '<p class="text-danger">加载文件列表失败，请刷新页面重试</p>';
        }
    });
}

// 加载场景和关联关系
function loadScenesAndRelations() {
    // 加载场景
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.SCENES.LIST), {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('加载场景列表失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('从后端加载的场景数据:', data);
        scenes = data || [];
        displayScenes();
    })
    .catch(error => {
        console.error('加载场景列表失败:', error);
        // 如果加载失败，使用空数组
        scenes = [];
        displayScenes();
    });
    
    // 加载关联关系
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.RELATIONS.LIST), {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('加载关联关系列表失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('从后端加载的关联关系数据:', data);
        relations = data || [];
        displayRelations();
    })
    .catch(error => {
        console.error('加载关联关系列表失败:', error);
        // 如果加载失败，使用空数组
        relations = [];
        displayRelations();
    });
}

// 显示场景列表
function displayScenes() {
    const sceneList = document.getElementById('sceneList');
    if (!sceneList) return;
    
    if (scenes.length === 0) {
        sceneList.innerHTML = '<p class="text-muted">暂无场景，请添加场景</p>';
        return;
    }
    
    sceneList.innerHTML = '';
    
    scenes.forEach(scene => {
        const sceneCard = document.createElement('div');
        sceneCard.className = 'scene-card';
        
        // 获取场景类型的中文名称
        const sceneTypeMap = {
            'user-registration': '用户注册',
            'user-login': '用户登录',
            'e-commerce': '电商流程',
            'data-query': '数据查询',
            'data-modification': '数据修改',
            'custom': '自定义'
        };
        
        const sceneTypeName = sceneTypeMap[scene.type] || scene.type;
        
        sceneCard.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${scene.name}</h6>
                    <span class="scene-type-badge">${sceneTypeName}</span>
                    <p class="text-muted small mt-2 mb-1">${scene.description || '暂无描述'}</p>
                    <div class="mt-2">
                        <small class="text-muted">相关API: ${scene.apis ? scene.apis.length : 0}个</small>
                    </div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                        操作
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="editScene('${scene.id}')">编辑</a></li>
                        <li><a class="dropdown-item text-danger" href="#" onclick="deleteScene('${scene.id}')">删除</a></li>
                    </ul>
                </div>
            </div>
        `;
        
        sceneList.appendChild(sceneCard);
    });
}

// 显示关联关系列表
function displayRelations() {
    const relationList = document.getElementById('relationList');
    if (!relationList) return;
    
    if (relations.length === 0) {
        relationList.innerHTML = '<p class="text-muted">暂无关联关系，请添加关联关系</p>';
        return;
    }
    
    relationList.innerHTML = '';
    
    relations.forEach(relation => {
        const relationCard = document.createElement('div');
        relationCard.className = 'relation-card';
        
        // 获取关联类型的中文名称
        const relationTypeMap = {
            'sequential': '顺序执行',
            'dependency': '依赖关系',
            'data-flow': '数据流',
            'conditional': '条件执行',
            'alternative': '替代方案'
        };
        
        const relationTypeName = relationTypeMap[relation.type] || relation.type;
        
        relationCard.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-2">
                        <span class="relation-type-badge me-2">${relationTypeName}</span>
                        <small class="text-muted">置信度: ${relation.confidence || 50}%</small>
                    </div>
                    <div class="mb-2">
                        <strong>源API:</strong> ${relation.sourceApi || '未指定'} <i class="fas fa-arrow-right mx-2"></i> <strong>目标API:</strong> ${relation.targetApi || '未指定'}
                    </div>
                    <p class="text-muted small mb-2">${relation.description || '暂无描述'}</p>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${relation.confidence || 50}%"></div>
                    </div>
                </div>
                <div class="dropdown ms-3">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                        操作
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="editRelation('${relation.id}')">编辑</a></li>
                        <li><a class="dropdown-item text-danger" href="#" onclick="deleteRelation('${relation.id}')">删除</a></li>
                    </ul>
                </div>
            </div>
        `;
        
        relationList.appendChild(relationCard);
    });
}

// 填充API复选框列表（用于场景选择）
function populateApiCheckboxList() {
    const apiCheckboxList = document.getElementById('apiCheckboxList');
    if (!apiCheckboxList) return;
    
    // 获取当前API列表
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.LIST), {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取API列表失败');
        }
        return response.json();
    })
    .then(data => {
        const apis = data || [];
        
        if (apis.length === 0) {
            apiCheckboxList.innerHTML = '<p class="text-muted">暂无API可选</p>';
            return;
        }
        
        apiCheckboxList.innerHTML = '';
        
        apis.forEach(api => {
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check';
            
            checkboxDiv.innerHTML = `
                <input class="form-check-input" type="checkbox" value="${api.id || api.path}" id="api_${api.id || api.path.replace(/[^a-zA-Z0-9]/g, '_')}">
                <label class="form-check-label" for="api_${api.id || api.path.replace(/[^a-zA-Z0-9]/g, '_')}">
                    ${api.method} ${api.path}
                </label>
            `;
            
            apiCheckboxList.appendChild(checkboxDiv);
        });
    })
    .catch(error => {
        console.error('获取API列表失败:', error);
        apiCheckboxList.innerHTML = '<p class="text-danger">加载API列表失败</p>';
    });
}

// 填充API选择选项（用于关联关系）
function populateApiSelectOptions() {
    const sourceApiSelect = document.getElementById('sourceApi');
    const targetApiSelect = document.getElementById('targetApi');
    
    if (!sourceApiSelect || !targetApiSelect) return;
    
    // 获取当前API列表
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.LIST), {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取API列表失败');
        }
        return response.json();
    })
    .then(data => {
        const apis = data || [];
        
        if (apis.length === 0) {
            sourceApiSelect.innerHTML = '<option value="">暂无API可选</option>';
            targetApiSelect.innerHTML = '<option value="">暂无API可选</option>';
            return;
        }
        
        // 保存当前选中的值
        const sourceApiValue = sourceApiSelect.value;
        const targetApiValue = targetApiSelect.value;
        
        // 清空并重新填充选项
        sourceApiSelect.innerHTML = '<option value="">请选择源API</option>';
        targetApiSelect.innerHTML = '<option value="">请选择目标API</option>';
        
        apis.forEach(api => {
            const optionValue = api.id || api.path;
            const optionText = `${api.method} ${api.path}`;
            
            sourceApiSelect.innerHTML += `<option value="${optionValue}">${optionText}</option>`;
            targetApiSelect.innerHTML += `<option value="${optionValue}">${optionText}</option>`;
        });
        
        // 恢复之前选中的值
        sourceApiSelect.value = sourceApiValue;
        targetApiSelect.value = targetApiValue;
    })
    .catch(error => {
        console.error('获取API列表失败:', error);
        sourceApiSelect.innerHTML = '<option value="">加载API列表失败</option>';
        targetApiSelect.innerHTML = '<option value="">加载API列表失败</option>';
    });
}

// 保存场景
function saveScene() {
    const sceneName = document.getElementById('sceneName').value.trim();
    const sceneType = document.getElementById('sceneType').value;
    const sceneDescription = document.getElementById('sceneDescription').value.trim();
    
    if (!sceneName) {
        showSmartTestNotification('请输入场景名称', 'error');
        return;
    }
    
    if (!sceneType) {
        showSmartTestNotification('请选择场景类型', 'error');
        return;
    }
    
    // 获取选中的API
    const selectedApis = [];
    const apiCheckboxes = document.querySelectorAll('#apiCheckboxList input[type="checkbox"]:checked');
    
    apiCheckboxes.forEach(checkbox => {
        selectedApis.push(checkbox.value);
    });
    
    const sceneData = {
        name: sceneName,
        type: sceneType,
        description: sceneDescription,
        apis: selectedApis
    };
    
    // 发送到后端
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const scenesEndpoint = endpoints.SCENES || {};
    const createUrl = baseUrl + (scenesEndpoint.CREATE || '/api/scenes/create');
    
    fetch(createUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(sceneData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('保存场景失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('场景保存成功:', data);
        
        // 添加到本地场景列表
        scenes.push({
            id: data.id || Date.now().toString(),
            ...sceneData
        });
        
        // 更新显示
        displayScenes();
        
        // 关闭模态框
        const sceneModal = bootstrap.Modal.getInstance(document.getElementById('addSceneModal'));
        if (sceneModal) sceneModal.hide();
        
        // 重置表单
        document.getElementById('addSceneForm').reset();
        
        // 显示成功消息
        showSmartTestNotification('场景保存成功', 'success');
    })
    .catch(error => {
        console.error('保存场景失败:', error);
        showSmartTestNotification(error.message, 'error');
    });
}

// 保存关联关系
function saveRelation() {
    const sourceApi = document.getElementById('sourceApi').value;
    const targetApi = document.getElementById('targetApi').value;
    const relationType = document.getElementById('relationType').value;
    const relationDescription = document.getElementById('relationDescription').value.trim();
    const confidence = document.getElementById('confidence').value;
    
    if (!sourceApi) {
        showSmartTestNotification('请选择源API', 'error');
        return;
    }
    
    if (!targetApi) {
        showSmartTestNotification('请选择目标API', 'error');
        return;
    }
    
    if (!relationType) {
        showSmartTestNotification('请选择关联类型', 'error');
        return;
    }
    
    if (sourceApi === targetApi) {
        showSmartTestNotification('源API和目标API不能相同', 'error');
        return;
    }
    
    const relationData = {
        sourceApi: sourceApi,
        targetApi: targetApi,
        type: relationType,
        description: relationDescription,
        confidence: parseInt(confidence)
    };
    
    // 发送到后端
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const relationsEndpoint = endpoints.RELATIONS || {};
    const createUrl = baseUrl + (relationsEndpoint.CREATE || '/api/relations/create');
    
    fetch(createUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(relationData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('保存关联关系失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('关联关系保存成功:', data);
        
        // 添加到本地关联关系列表
        relations.push({
            id: data.id || Date.now().toString(),
            ...relationData
        });
        
        // 更新显示
        displayRelations();
        
        // 关闭模态框
        const relationModal = bootstrap.Modal.getInstance(document.getElementById('addRelationModal'));
        if (relationModal) relationModal.hide();
        
        // 重置表单
        document.getElementById('addRelationForm').reset();
        document.getElementById('confidenceValue').textContent = '50%';
        
        // 显示成功消息
        showSmartTestNotification('关联关系保存成功', 'success');
    })
    .catch(error => {
        console.error('保存关联关系失败:', error);
        showSmartTestNotification(error.message, 'error');
    });
}

// 编辑场景
function editScene(sceneId) {
    // 找到要编辑的场景
    const scene = scenes.find(s => s.id === sceneId);
    if (!scene) {
        showSmartTestNotification('找不到指定的场景', 'error');
        return;
    }
    
    // 填充表单
    document.getElementById('sceneName').value = scene.name;
    document.getElementById('sceneType').value = scene.type;
    document.getElementById('sceneDescription').value = scene.description || '';
    
    // 清空并重新选中API
    const apiCheckboxes = document.querySelectorAll('#apiCheckboxList input[type="checkbox"]');
    apiCheckboxes.forEach(checkbox => {
        checkbox.checked = scene.apis && scene.apis.includes(checkbox.value);
    });
    
    // 显示模态框
    const sceneModal = new bootstrap.Modal(document.getElementById('addSceneModal'));
    sceneModal.show();
}

// 删除场景
function deleteScene(sceneId) {
    if (!confirm('确定要删除这个场景吗？')) {
        return;
    }
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const scenesEndpoint = endpoints.SCENES || {};
    const deleteUrl = baseUrl + (scenesEndpoint.DELETE || '/api/scenes/delete') + `/${sceneId}`;
    
    fetch(deleteUrl, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('删除场景失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('场景删除成功:', data);
        
        // 从本地列表中移除
        scenes = scenes.filter(s => s.id !== sceneId);
        
        // 更新显示
        displayScenes();
        
        // 显示成功消息
        showSmartTestNotification('场景删除成功', 'success');
    })
    .catch(error => {
        console.error('删除场景失败:', error);
        showSmartTestNotification(error.message, 'error');
    });
}

// 编辑关联关系
function editRelation(relationId) {
    // 找到要编辑的关联关系
    const relation = relations.find(r => r.id === relationId);
    if (!relation) {
        showSmartTestNotification('找不到指定的关联关系', 'error');
        return;
    }
    
    // 填充表单
    document.getElementById('sourceApi').value = relation.sourceApi;
    document.getElementById('targetApi').value = relation.targetApi;
    document.getElementById('relationType').value = relation.type;
    document.getElementById('relationDescription').value = relation.description || '';
    document.getElementById('confidence').value = relation.confidence || 50;
    document.getElementById('confidenceValue').textContent = (relation.confidence || 50) + '%';
    
    // 显示模态框
    const relationModal = new bootstrap.Modal(document.getElementById('addRelationModal'));
    relationModal.show();
}

// 删除关联关系
function deleteRelation(relationId) {
    if (!confirm('确定要删除这个关联关系吗？')) {
        return;
    }
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const relationsEndpoint = endpoints.RELATIONS || {};
    const deleteUrl = baseUrl + (relationsEndpoint.DELETE || '/api/relations/delete') + `/${relationId}`;
    
    fetch(deleteUrl, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('删除关联关系失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('关联关系删除成功:', data);
        
        // 从本地列表中移除
        relations = relations.filter(r => r.id !== relationId);
        
        // 更新显示
        displayRelations();
        
        // 显示成功消息
        showSmartTestNotification('关联关系删除成功', 'success');
    })
    .catch(error => {
        console.error('删除关联关系失败:', error);
        showSmartTestNotification(error.message, 'error');
    });
}