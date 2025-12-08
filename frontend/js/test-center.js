// 测试中心页面JavaScript - 合并API文档、智能测试生成和测试用例功能

// 全局变量
let currentStep = 1;
let apiDocData = null;
let testCases = [];
let scenarios = [];
let relations = [];
let selectedApis = new Set();

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initTestCenter();
});

// 加载已保存的数据
function loadSavedData() {
    const savedConfig = localStorage.getItem('testCenterConfig');
    if (savedConfig) {
        try {
            const configuration = JSON.parse(savedConfig);
            apiDocData = configuration.apiDocData;
            testCases = configuration.testCases || [];
            scenarios = configuration.scenarios || [];
            relations = configuration.relations || [];
            
            // 如果有API文档数据，显示文件信息
            if (apiDocData) {
                showSmartFileInfo('已保存的API文档', 0, apiDocData);
                
                const smartAnalyzeBtn = document.getElementById('smartAnalyzeBtn');
                if (smartAnalyzeBtn) {
                    smartAnalyzeBtn.disabled = false;
                } else {
                    console.warn('Element with ID "smartAnalyzeBtn" not found');
                }
            }
            
// 加载OpenAPI文档列表
async function loadOpenApiDocs() {
    console.log('开始加载OpenAPI文档列表');
    
    try {
        // 显示加载状态
        showLoading();
        
        // 检查API_CONFIG是否已定义
        if (!window.API_CONFIG) {
            console.warn('API_CONFIG未定义，使用默认值');
            window.API_CONFIG = {
                BASE_URL: 'http://127.0.0.1:5000'
            };
        }
        
        // 使用直接拼接URL的方式，避免undefined问题
        const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
        const apiUrl = baseUrl + '/api/docs/openapi-list';
        
        console.log('API请求URL:', apiUrl);
        
        // 设置10秒超时
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(apiUrl, {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`获取OpenAPI文档列表失败: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('OpenAPI文档列表响应:', data);
        
        // 获取表格体
        const tableBody = document.getElementById('openApiDocsTableBody');
        if (!tableBody) {
            console.error('找不到表格体元素: openApiDocsTableBody');
            hideLoading();
            return;
        }
        
        // 清空表格
        tableBody.innerHTML = '';
        
        // 检查是否有文档
        if (!data.success || !data.data || data.data.length === 0) {
            // 显示无文档提示
            const noDocsMessage = document.getElementById('noOpenApiDocsMessage');
            if (noDocsMessage) {
                noDocsMessage.style.display = 'block';
            }
            
            // 添加空行
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = `
                <td colspan="5" class="text-center text-muted">
                    暂无OpenAPI文档
                </td>
            `;
            tableBody.appendChild(emptyRow);
            
            hideLoading();
            return;
        }
        
        // 隐藏无文档提示
        const noDocsMessage = document.getElementById('noOpenApiDocsMessage');
        if (noDocsMessage) {
            noDocsMessage.style.display = 'none';
        }
        
        // 添加文档行
        data.data.forEach(doc => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${doc.file_id || ''}</td>
                <td>${doc.file_name || ''}</td>
                <td>${formatFileSize(doc.file_size || 0)}</td>
                <td>${formatDateTime(doc.upload_time)}</td>
                <td>${doc.api_count || 0}</td>
                <td>
                    <button class="btn btn-sm btn-outline-success" onclick="generateTestCasesFromOpenApi('${doc.file_id}', '${doc.file_name || ''}')">
                        <i class="fas fa-cogs"></i> 生成测试用例
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteOpenApiDoc('${doc.file_id}', '${doc.file_name || ''}')">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        console.log('OpenAPI文档列表加载完成');
        
    } catch (error) {
        console.error('加载OpenAPI文档列表失败:', error);
        
        // 显示错误信息
        const tableBody = document.getElementById('openApiDocsTableBody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger">
                        加载OpenAPI文档列表失败: ${error.message}
                    </td>
                </tr>
            `;
        }
        
        showNotification('加载OpenAPI文档列表失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 从OpenAPI文档生成测试用例
async function generateTestCasesFromOpenApi(fileId, fileName) {
    console.log(`开始从OpenAPI文档生成测试用例: ${fileName} (ID: ${fileId})`);
    
    try {
        // 显示加载状态
        showLoading();
        
        // 检查API_CONFIG是否已定义
        if (!window.API_CONFIG) {
            console.warn('API_CONFIG未定义，使用默认值');
            window.API_CONFIG = {
                BASE_URL: 'http://127.0.0.1:5000'
            };
        }
        
        // 使用直接拼接URL的方式，避免undefined问题
        const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
        const apiUrl = baseUrl + `/api/docs/generate-from-openapi/${fileId}`;
        
        console.log('API请求URL:', apiUrl);
        
        // 设置30秒超时（生成测试用例可能需要更长时间）
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`生成测试用例失败: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('生成测试用例响应:', data);
        
        if (data.success) {
            showNotification(`成功从 ${fileName} 生成测试用例`, 'success');
            
            // 刷新已上传文档列表，因为新生成的文档会出现在那里
            loadUploadedDocs();
            
            // 切换到测试用例标签页
            const testCasesTab = document.getElementById('test-cases-tab');
            if (testCasesTab) {
                const tab = new bootstrap.Tab(testCasesTab);
                tab.show();
            }
        } else {
            throw new Error(data.message || '生成测试用例失败');
        }
        
    } catch (error) {
        console.error('生成测试用例失败:', error);
        showNotification('生成测试用例失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 删除OpenAPI文档
async function deleteOpenApiDoc(fileId, fileName) {
    console.log(`开始删除OpenAPI文档: ${fileName} (ID: ${fileId})`);
    
    // 确认删除
    if (!confirm(`确定要删除OpenAPI文档 "${fileName}" 吗？此操作不可恢复。`)) {
        return;
    }
    
    try {
        // 显示加载状态
        showLoading();
        
        // 检查API_CONFIG是否已定义
        if (!window.API_CONFIG) {
            console.warn('API_CONFIG未定义，使用默认值');
            window.API_CONFIG = {
                BASE_URL: 'http://127.0.0.1:5000'
            };
        }
        
        // 使用直接拼接URL的方式，避免undefined问题
        const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
        const apiUrl = baseUrl + `/api/docs/delete-openapi/${fileId}`;
        
        console.log('API请求URL:', apiUrl);
        
        // 设置10秒超时
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(apiUrl, {
            method: 'DELETE',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`删除OpenAPI文档失败: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('删除OpenAPI文档响应:', data);
        
        if (data.success) {
            showNotification(`成功删除OpenAPI文档 "${fileName}"`, 'success');
            
            // 刷新OpenAPI文档列表
            loadOpenApiDocs();
        } else {
            throw new Error(data.message || '删除OpenAPI文档失败');
        }
        
    } catch (error) {
        console.error('删除OpenAPI文档失败:', error);
        showNotification('删除OpenAPI文档失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 加载测试用例
            if (testCases.length > 0) {
                loadTestCases();
            }
        } catch (error) {
            console.error('加载保存的配置失败:', error);
        }
    }
}

// 初始化测试中心
function initTestCenter() {
    // 初始化测试用例标签页
    initTestCasesTab();
    
    // 初始化已上传文档标签页
    initUploadedDocsTab();
    
    // 注意：不要在这里调用loadSavedData，因为它会在components/test-center.js中被调用
    // 避免重复初始化
}



// 初始化测试用例标签页
function initTestCasesTab() {
    // 运行所有测试按钮
    const runAllCasesBtn = document.getElementById('runAllCasesBtn');
    if (runAllCasesBtn) {
        runAllCasesBtn.addEventListener('click', runAllCases);
    }
    
    // 生成测试用例按钮
    const generateCasesBtn = document.getElementById('generateCasesBtn');
    if (generateCasesBtn) {
        generateCasesBtn.addEventListener('click', function() {
            // 显示提示信息，需要从API文档生成测试用例
            alert('请先在"接口文档"标签页中上传API文档，然后可以生成测试用例');
        });
    }
    
    // 搜索输入
    const searchCasesInput = document.getElementById('searchCasesInput');
    if (searchCasesInput) {
        searchCasesInput.addEventListener('input', filterTestCases);
    }
    
    // 筛选器
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', filterTestCases);
    }
    
    const typeFilter = document.getElementById('typeFilter');
    if (typeFilter) {
        typeFilter.addEventListener('change', filterTestCases);
    }
    
    const apiFilter = document.getElementById('apiFilter');
    if (apiFilter) {
        apiFilter.addEventListener('change', filterTestCases);
    }
    
    // 视图模式切换
    const listView = document.getElementById('listView');
    if (listView) {
        listView.addEventListener('change', function() {
            if (this.checked) {
                renderTestCasesList('list');
            }
        });
    }
    
    const gridView = document.getElementById('gridView');
    if (gridView) {
        gridView.addEventListener('change', function() {
            if (this.checked) {
                renderTestCasesList('grid');
            }
        });
    }
    
    // 加载测试用例
    loadTestCases();
}

// 初始化已上传文档标签页
function initUploadedDocsTab() {
    console.log('初始化已上传文档标签页');
    
    // 刷新文档按钮
    const refreshDocsBtn = document.getElementById('refreshDocsBtn');
    if (refreshDocsBtn) {
        refreshDocsBtn.addEventListener('click', loadUploadedDocs);
    } else {
        console.warn('Element with ID "refreshDocsBtn" not found');
    }
    
    // 刷新OpenAPI文档按钮
    const refreshOpenApiDocsBtn = document.getElementById('refreshOpenApiDocsBtn');
    if (refreshOpenApiDocsBtn) {
        refreshOpenApiDocsBtn.addEventListener('click', loadOpenApiDocs);
    } else {
        console.warn('Element with ID "refreshOpenApiDocsBtn" not found');
    }
    
    // 监听接口文档标签页激活事件
    const apiDocsTab = document.getElementById('api-docs-tab');
    if (apiDocsTab) {
        apiDocsTab.addEventListener('shown.bs.tab', function() {
            console.log('接口文档标签页被激活，加载已上传文档列表');
            loadUploadedDocs();
        });
    } else {
        console.warn('Element with ID "api-docs-tab" not found');
    }
    
    // 监听OpenAPI文档标签页激活事件
    const openApiDocsTab = document.getElementById('openapi-docs-tab');
    if (openApiDocsTab) {
        openApiDocsTab.addEventListener('shown.bs.tab', function() {
            console.log('OpenAPI文档标签页被激活，加载OpenAPI文档列表');
            loadOpenApiDocs();
        });
    } else {
        console.warn('Element with ID "openapi-docs-tab" not found');
    }
    
    // 初始加载已上传文档列表
    // 延迟500ms确保所有元素都已加载完成
    setTimeout(() => {
        console.log('延迟加载已上传文档列表');
        loadUploadedDocs();
    }, 500);
}

// 加载已上传的文档列表
async function loadUploadedDocs() {
    try {
        console.log('开始加载已上传的文档列表');
        
        // 显示加载状态
        showLoading();
        
        // 检查API_CONFIG是否已定义
        if (!window.API_CONFIG) {
            console.warn('API_CONFIG未定义，使用默认值');
            window.API_CONFIG = {
                BASE_URL: 'http://127.0.0.1:5000'
            };
        }
        
        // 使用直接拼接URL的方式，避免undefined问题
        const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
        const apiUrl = baseUrl + '/api/docs/list';
        
        console.log('API请求URL:', apiUrl);
        
        // 设置10秒超时
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(apiUrl, {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`获取文档列表失败: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('文档列表响应:', data);
        
        // 获取表格体
        const tableBody = document.getElementById('apiDocsTableBody');
        if (!tableBody) {
            console.error('找不到表格体元素: apiDocsTableBody');
            hideLoading();
            return;
        }
        
        // 清空表格
        tableBody.innerHTML = '';
        
        // 检查是否有文档
        if (!data.docs || data.docs.length === 0) {
            // 显示无文档提示
            const noDocsMessage = document.getElementById('noApiDocsMessage');
            if (noDocsMessage) {
                noDocsMessage.style.display = 'block';
            }
            
            // 添加空行
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = `
                <td colspan="5" class="text-center text-muted">
                    暂无已上传的文档
                </td>
            `;
            tableBody.appendChild(emptyRow);
            
            hideLoading();
            return;
        }
        
        // 隐藏无文档提示
        const noDocsMessage = document.getElementById('noApiDocsMessage');
        if (noDocsMessage) {
            noDocsMessage.style.display = 'none';
        }
        
        // 添加文档行
        data.docs.forEach(doc => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${doc.task_id || ''}</td>
                <td>${doc.filename || ''}</td>
                <td>${formatDateTime(doc.created_at)}</td>
                <td>${doc.api_count || 0}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewDocument('${doc.task_id}')">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDocument('${doc.task_id}', '${doc.filename || ''}')">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        console.log('文档列表加载完成');
        
    } catch (error) {
        console.error('加载文档列表失败:', error);
        
        // 显示错误信息
        const tableBody = document.getElementById('apiDocsTableBody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-danger">
                        加载文档列表失败: ${error.message}
                    </td>
                </tr>
            `;
        }
        
        showNotification('加载文档列表失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 筛选测试用例
function filterTestCases() {
    const searchCasesInput = document.getElementById('searchCasesInput');
    const statusFilter = document.getElementById('statusFilter');
    const typeFilter = document.getElementById('typeFilter');
    const apiFilter = document.getElementById('apiFilter');
    const listView = document.getElementById('listView');
    
    if (!searchCasesInput || !statusFilter || !typeFilter || !apiFilter || !listView) {
        console.warn('One or more filter elements not found');
        return;
    }
    
    const searchTerm = searchCasesInput.value.toLowerCase();
    const statusFilterValue = statusFilter.value;
    const typeFilterValue = typeFilter.value;
    const apiFilterValue = apiFilter.value;
    
    const filteredCases = testCases.filter(testCase => {
        const matchesSearch = testCase.name.toLowerCase().includes(searchTerm) || 
                             testCase.description.toLowerCase().includes(searchTerm);
        
        const matchesStatus = !statusFilterValue || testCase.status === statusFilterValue;
        
        const matchesType = !typeFilterValue || testCase.type === typeFilterValue;
        
        const matchesApi = !apiFilterValue || `${testCase.api.method} ${testCase.api.path}` === apiFilterValue;
        
        return matchesSearch && matchesStatus && matchesType && matchesApi;
    });
    
    // 临时替换testCases数组并重新渲染
    const originalCases = testCases;
    testCases = filteredCases;
    
    const viewMode = listView.checked ? 'list' : 'grid';
    renderTestCasesList(viewMode);
    
    // 恢复原始数组
    testCases = originalCases;
}

// 加载测试用例
function loadTestCases() {
    // 模拟加载测试用例
    if (apiDocData) {
        extractApiEndpoints(apiDocData)
            .then(endpoints => {
                testCases = generateMockTestCases(endpoints, scenarios, relations);
                
                // 更新统计信息
                updateTestCasesStats();
                
                // 渲染测试用例列表
                renderTestCasesList('list');
                
                // 填充API筛选器
                populateApiFilter();
            })
            .catch(error => {
                console.error('加载测试用例失败:', error);
                testCases = [];
                updateTestCasesStats();
                renderTestCasesList('list');
                populateApiFilter();
            });
    } else {
        testCases = [];
        updateTestCasesStats();
        renderTestCasesList('list');
        populateApiFilter();
    }
}

// 更新测试用例统计信息
function updateTestCasesStats() {
    const totalCases = testCases.length;
    const passedCases = testCases.filter(tc => tc.status === 'passed').length;
    const failedCases = testCases.filter(tc => tc.status === 'failed').length;
    const passRate = totalCases > 0 ? ((passedCases / totalCases) * 100).toFixed(1) : 0;
    
    // 获取元素并检查存在性
    const totalCasesEl = document.getElementById('totalCases');
    const passedCasesEl = document.getElementById('passedCases');
    const failedCasesEl = document.getElementById('failedCases');
    const passRateEl = document.getElementById('passRate');
    
    if (totalCasesEl) {
        totalCasesEl.textContent = totalCases;
    } else {
        console.warn('Element with ID "totalCases" not found');
    }
    
    if (passedCasesEl) {
        passedCasesEl.textContent = passedCases;
    } else {
        console.warn('Element with ID "passedCases" not found');
    }
    
    if (failedCasesEl) {
        failedCasesEl.textContent = failedCases;
    } else {
        console.warn('Element with ID "failedCases" not found');
    }
    
    if (passRateEl) {
        passRateEl.textContent = passRate + '%';
    } else {
        console.warn('Element with ID "passRate" not found');
    }
}

// 渲染测试用例列表
function renderTestCasesList(viewMode) {
    const container = document.getElementById('testCasesListContainer');
    if (!container) {
        console.warn('Element with ID "testCasesListContainer" not found');
        return;
    }
    
    container.innerHTML = '';
    
    if (viewMode === 'list') {
        renderTestCasesAsList(container);
    } else {
        renderTestCasesAsGrid(container);
    }
}

// 渲染测试用例为列表
function renderTestCasesAsList(container) {
    const table = document.createElement('table');
    table.className = 'table table-striped';
    
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    const headers = ['测试用例', 'API', '类型', '状态', '操作'];
    headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText;
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    const tbody = document.createElement('tbody');
    
    testCases.forEach(testCase => {
        const row = document.createElement('tr');
        
        // 测试用例名称
        const nameCell = document.createElement('td');
        nameCell.textContent = testCase.name;
        row.appendChild(nameCell);
        
        // API
        const apiCell = document.createElement('td');
        const apiBadge = document.createElement('span');
        apiBadge.className = `api-badge method-${testCase.api.method.toLowerCase()}`;
        apiBadge.textContent = `${testCase.api.method} ${testCase.api.path}`;
        apiCell.appendChild(apiBadge);
        row.appendChild(apiCell);
        
        // 类型
        const typeCell = document.createElement('td');
        const typeBadge = document.createElement('span');
        typeBadge.className = 'badge bg-secondary';
        typeBadge.textContent = getTestCaseTypeLabel(testCase.type);
        typeCell.appendChild(typeBadge);
        row.appendChild(typeCell);
        
        // 状态
        const statusCell = document.createElement('td');
        const statusBadge = document.createElement('span');
        statusBadge.className = `badge bg-${testCase.status === 'passed' ? 'success' : testCase.status === 'failed' ? 'danger' : 'secondary'}`;
        statusBadge.textContent = testCase.status === 'passed' ? '通过' : testCase.status === 'failed' ? '失败' : '未运行';
        statusCell.appendChild(statusBadge);
        row.appendChild(statusCell);
        
        // 操作
        const actionsCell = document.createElement('td');
        const runBtn = document.createElement('button');
        runBtn.className = 'btn btn-sm btn-outline-primary me-1';
        runBtn.innerHTML = '<i class="fas fa-play"></i>';
        runBtn.title = '运行测试';
        runBtn.addEventListener('click', () => runTestCase(testCase.id));
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-secondary me-1';
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.title = '编辑测试';
        editBtn.addEventListener('click', () => editTestCase(testCase.id));
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.title = '删除测试';
        deleteBtn.addEventListener('click', () => deleteTestCase(testCase.id));
        
        actionsCell.appendChild(runBtn);
        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(deleteBtn);
        row.appendChild(actionsCell);
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    container.appendChild(table);
}

// 渲染测试用例为网格
function renderTestCasesAsGrid(container) {
    const row = document.createElement('div');
    row.className = 'row';
    
    testCases.forEach(testCase => {
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        
        const card = document.createElement('div');
        card.className = 'card h-100';
        
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        const cardTitle = document.createElement('h6');
        cardTitle.className = 'card-title';
        cardTitle.textContent = testCase.name;
        
        const apiBadge = document.createElement('span');
        apiBadge.className = `api-badge method-${testCase.api.method.toLowerCase()}`;
        apiBadge.textContent = `${testCase.api.method} ${testCase.api.path}`;
        
        const typeBadge = document.createElement('span');
        typeBadge.className = 'badge bg-secondary ms-1';
        typeBadge.textContent = getTestCaseTypeLabel(testCase.type);
        
        const statusBadge = document.createElement('span');
        statusBadge.className = `badge bg-${testCase.status === 'passed' ? 'success' : testCase.status === 'failed' ? 'danger' : 'secondary'} ms-1`;
        statusBadge.textContent = testCase.status === 'passed' ? '通过' : testCase.status === 'failed' ? '失败' : '未运行';
        
        const cardActions = document.createElement('div');
        cardActions.className = 'mt-2';
        
        const runBtn = document.createElement('button');
        runBtn.className = 'btn btn-sm btn-outline-primary me-1';
        runBtn.innerHTML = '<i class="fas fa-play"></i>';
        runBtn.title = '运行测试';
        runBtn.addEventListener('click', () => runTestCase(testCase.id));
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-secondary me-1';
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.title = '编辑测试';
        editBtn.addEventListener('click', () => editTestCase(testCase.id));
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.title = '删除测试';
        deleteBtn.addEventListener('click', () => deleteTestCase(testCase.id));
        
        cardActions.appendChild(runBtn);
        cardActions.appendChild(editBtn);
        cardActions.appendChild(deleteBtn);
        
        cardBody.appendChild(cardTitle);
        cardBody.appendChild(apiBadge);
        cardBody.appendChild(typeBadge);
        cardBody.appendChild(statusBadge);
        cardBody.appendChild(cardActions);
        
        card.appendChild(cardBody);
        col.appendChild(card);
        row.appendChild(col);
    });
    
    container.appendChild(row);
}

// 填充API筛选器
function populateApiFilter() {
    const apiFilter = document.getElementById('apiFilter');
    if (!apiFilter) {
        console.warn('Element with ID "apiFilter" not found');
        return;
    }
    
    apiFilter.innerHTML = '<option value="">所有API</option>';
    
    const uniqueApis = [...new Set(testCases.map(tc => `${tc.api.method} ${tc.api.path}`))];
    
    uniqueApis.forEach(api => {
        const option = document.createElement('option');
        option.value = api;
        option.textContent = api;
        apiFilter.appendChild(option);
    });
}

// 获取测试用例类型标签
function getTestCaseTypeLabel(type) {
    const typeLabels = {
        'functional': '功能测试',
        'integration': '集成测试',
        'performance': '性能测试',
        'security': '安全测试',
        'regression': '回归测试',
        'smoke': '冒烟测试',
        'acceptance': '验收测试'
    };
    return typeLabels[type] || type;
}

// 生成模拟测试用例
function generateMockTestCases(endpoints, scenarios, relations) {
    const testCases = [];
    
    // 为每个API端点生成基本测试用例
    endpoints.forEach((endpoint, index) => {
        // 正向测试用例
        testCases.push({
            id: `tc-${endpoint.method}-${endpoint.path.replace(/[^a-zA-Z0-9]/g, '-')}-positive`,
            name: `${endpoint.method.toUpperCase()} ${endpoint.path} - 正向测试`,
            description: `验证${endpoint.method.toUpperCase()} ${endpoint.path}接口在正常参数下的响应`,
            api: {
                method: endpoint.method,
                path: endpoint.path
            },
            type: 'functional',
            status: 'pending',
            tags: ['positive', 'functional'],
            preconditions: [],
            steps: [
                `发送${endpoint.method.toUpperCase()}请求到${endpoint.path}`,
                '验证响应状态码为200',
                '验证响应数据格式正确'
            ],
            expectedResult: '接口返回正确的响应数据'
        });
        
        // 负向测试用例
        testCases.push({
            id: `tc-${endpoint.method}-${endpoint.path.replace(/[^a-zA-Z0-9]/g, '-')}-negative`,
            name: `${endpoint.method.toUpperCase()} ${endpoint.path} - 负向测试`,
            description: `验证${endpoint.method.toUpperCase()} ${endpoint.path}接口在异常参数下的响应`,
            api: {
                method: endpoint.method,
                path: endpoint.path
            },
            type: 'functional',
            status: 'pending',
            tags: ['negative', 'functional'],
            preconditions: [],
            steps: [
                `发送${endpoint.method.toUpperCase()}请求到${endpoint.path}，使用无效参数`,
                '验证响应状态码为400或500',
                '验证错误消息格式正确'
            ],
            expectedResult: '接口返回适当的错误响应'
        });
    });
    
    return testCases;
}

// 查看文档详情
async function viewDocument(taskId) {
    try {
        console.log('查看文档:', taskId);
        
        // 显示加载状态
        showLoading();
        
        // 使用直接拼接URL的方式，避免undefined问题
        const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
        const apiUrl = baseUrl + '/api/docs/' + taskId;
        
        // 获取文档详情
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            throw new Error(`获取文档详情失败: ${response.status}`);
        }
        
        const documentData = await response.json();
        console.log('文档详情:', documentData);
        
        // 填充文档信息
        document.getElementById('docDetailId').textContent = documentData.task_id || taskId;
        document.getElementById('docDetailName').textContent = documentData.filename || '未知文档';
        document.getElementById('docDetailCreatedAt').textContent = formatDateTime(documentData.created_at);
        document.getElementById('docDetailApiCount').textContent = documentData.api_count || 0;
        
        // 填充API端点列表
        const endpointsList = document.getElementById('docEndpointsList');
        endpointsList.innerHTML = '';
        
        if (documentData.api_data && documentData.api_data.paths) {
            const paths = documentData.api_data.paths;
            Object.keys(paths).forEach(path => {
                Object.keys(paths[path]).forEach(method => {
                    const endpoint = document.createElement('div');
                    endpoint.className = 'list-group-item list-group-item-action';
                    endpoint.innerHTML = `
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">
                                <span class="badge bg-${getMethodColor(method)}">${method.toUpperCase()}</span>
                                ${path}
                            </h6>
                        </div>
                        <small>${paths[path][method].summary || '无描述'}</small>
                    `;
                    endpointsList.appendChild(endpoint);
                });
            });
        } else {
            endpointsList.innerHTML = '<div class="list-group-item">暂无API端点</div>';
        }
        
        // 显示OpenAPI规范
        const openApiSpecEditor = document.getElementById('openApiSpecEditor');
        
        // 如果已经存在CodeMirror实例，先销毁它
        if (openApiSpecEditor.CodeMirror) {
            openApiSpecEditor.CodeMirror.toTextArea();
        }
        
        // 创建CodeMirror实例
        let editor;
        try {
            editor = CodeMirror.fromTextArea(openApiSpecEditor, {
                lineNumbers: true,
                mode: {name: "javascript", json: true},
                theme: 'default',
                readOnly: true,
                lineWrapping: true,
                autoCloseBrackets: true,
                matchBrackets: true
            });
            console.log('OpenAPI编辑器初始化完成', editor);
        } catch (error) {
            console.error('OpenAPI编辑器初始化失败:', error);
            // 尝试使用简单模式
            try {
                editor = CodeMirror.fromTextArea(openApiSpecEditor, {
                    lineNumbers: true,
                    mode: 'text/plain',
                    theme: 'default',
                    readOnly: true,
                    lineWrapping: true
                });
                console.log('OpenAPI编辑器使用简单模式初始化完成', editor);
            } catch (fallbackError) {
                console.error('OpenAPI编辑器简单模式初始化也失败:', fallbackError);
                // 如果还是失败，直接使用textarea
                editor = null;
            }
        }
        
        // 设置编辑器内容
        editor.setValue(JSON.stringify(documentData.api_data || {}, null, 2));
        
        // 保存编辑器实例引用
        openApiSpecEditor.CodeMirror = editor;
        
        // 初始化关联关系编辑器
        const relationSpecEditor = document.getElementById('relationSpecEditor');
        if (relationSpecEditor) {
            // 如果已经存在CodeMirror实例，先销毁它
            if (relationSpecEditor.CodeMirror) {
                relationSpecEditor.CodeMirror.toTextArea();
            }
            
            // 创建关联关系编辑器实例
            let relationEditor;
            try {
                relationEditor = CodeMirror.fromTextArea(relationSpecEditor, {
                    lineNumbers: true,
                    mode: {name: "javascript", json: true},
                    theme: 'default',
                    readOnly: true,
                    lineWrapping: true,
                    autoCloseBrackets: true,
                    matchBrackets: true
                });
                console.log('关联关系编辑器初始化完成', relationEditor);
            } catch (error) {
                console.error('关联关系编辑器初始化失败:', error);
                // 尝试使用简单模式
                try {
                    relationEditor = CodeMirror.fromTextArea(relationSpecEditor, {
                        lineNumbers: true,
                        mode: 'text/plain',
                        theme: 'default',
                        readOnly: true,
                        lineWrapping: true
                    });
                    console.log('关联关系编辑器使用简单模式初始化完成', relationEditor);
                } catch (fallbackError) {
                    console.error('关联关系编辑器简单模式初始化也失败:', fallbackError);
                    // 如果还是失败，直接使用textarea
                    relationEditor = null;
                }
            }
            
            // 设置编辑器内容
            if (relationEditor) {
                relationEditor.setValue(JSON.stringify(documentData.relation_data || {}, null, 2));
            } else {
                relationSpecEditor.value = JSON.stringify(documentData.relation_data || {}, null, 2);
            }
            
            // 保存编辑器实例引用
            relationSpecEditor.CodeMirror = relationEditor;
        }
        
        // 初始化业务场景编辑器
        const sceneSpecEditor = document.getElementById('sceneSpecEditor');
        if (sceneSpecEditor) {
            // 如果已经存在CodeMirror实例，先销毁它
            if (sceneSpecEditor.CodeMirror) {
                sceneSpecEditor.CodeMirror.toTextArea();
            }
            
            // 创建业务场景编辑器实例
            let sceneEditor;
            try {
                sceneEditor = CodeMirror.fromTextArea(sceneSpecEditor, {
                    lineNumbers: true,
                    mode: {name: "javascript", json: true},
                    theme: 'default',
                    readOnly: true,
                    lineWrapping: true,
                    autoCloseBrackets: true,
                    matchBrackets: true
                });
                console.log('业务场景编辑器初始化完成', sceneEditor);
            } catch (error) {
                console.error('业务场景编辑器初始化失败:', error);
                // 尝试使用简单模式
                try {
                    sceneEditor = CodeMirror.fromTextArea(sceneSpecEditor, {
                        lineNumbers: true,
                        mode: 'text/plain',
                        theme: 'default',
                        readOnly: true,
                        lineWrapping: true
                    });
                    console.log('业务场景编辑器使用简单模式初始化完成', sceneEditor);
                } catch (fallbackError) {
                    console.error('业务场景编辑器简单模式初始化也失败:', fallbackError);
                    // 如果还是失败，直接使用textarea
                    sceneEditor = null;
                }
            }
            
            // 设置编辑器内容
            if (sceneEditor) {
                sceneEditor.setValue(JSON.stringify(documentData.scene_data || {}, null, 2));
            } else {
                sceneSpecEditor.value = JSON.stringify(documentData.scene_data || {}, null, 2);
            }
            
            // 保存编辑器实例引用
            sceneSpecEditor.CodeMirror = sceneEditor;
        }
        
        // 显示关联关系数据
        if (documentData.relation_data) {
            displayRelationData(documentData.relation_data);
        }
        
        // 显示业务场景数据
        if (documentData.scene_data) {
            displaySceneData(documentData.scene_data);
        }
        
        // 设置生成测试用例按钮的事件
        const generateTestCasesBtn = document.getElementById('generateTestCasesBtn');
        generateTestCasesBtn.onclick = function() {
            generateTestCasesFromDoc(taskId);
            // 关闭当前模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('documentDetailsModal'));
            modal.hide();
        };
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('documentDetailsModal'));
        modal.show();
        
    } catch (error) {
        console.error('查看文档失败:', error);
        showNotification('查看文档失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 显示关联关系数据
function displayRelationData(relationData) {
    const relationContent = document.getElementById('relationContent');
    if (!relationContent) {
        console.error('找不到关联关系容器元素');
        return;
    }
    
    // 清空容器
    relationContent.innerHTML = '';
    
    // 创建关联关系总览卡片
    const overviewCard = document.createElement('div');
    overviewCard.className = 'card mb-3';
    
    const overviewCardBody = document.createElement('div');
    overviewCardBody.className = 'card-body';
    
    const overviewTitle = document.createElement('h6');
    overviewTitle.className = 'card-title';
    overviewTitle.textContent = '关联关系总览';
    
    const overviewText = document.createElement('p');
    overviewText.className = 'card-text';
    overviewText.textContent = relationData.description || '暂无描述';
    
    const statsRow = document.createElement('div');
    statsRow.className = 'row';
    
    const totalApisCol = document.createElement('div');
    totalApisCol.className = 'col-md-4';
    totalApisCol.innerHTML = `
        <div class="card text-center">
            <div class="card-body">
                <h5 class="card-title">${relationData.total_apis || 0}</h5>
                <p class="card-text">总API数量</p>
            </div>
        </div>
    `;
    
    statsRow.appendChild(totalApisCol);
    overviewCardBody.appendChild(overviewTitle);
    overviewCardBody.appendChild(overviewText);
    overviewCardBody.appendChild(statsRow);
    overviewCard.appendChild(overviewCardBody);
    relationContent.appendChild(overviewCard);
    
    // 创建关联关系详情
    if (relationData.relations && relationData.relations.length > 0) {
        const relationsTitle = document.createElement('h6');
        relationsTitle.className = 'mt-4 mb-3';
        relationsTitle.textContent = 'API关联关系详情';
        relationContent.appendChild(relationsTitle);
        
        const relationsAccordion = document.createElement('div');
        relationsAccordion.className = 'accordion';
        relationsAccordion.id = 'relationsAccordion';
        
        relationData.relations.forEach((relation, index) => {
            const relationItem = document.createElement('div');
            relationItem.className = 'accordion-item';
            
            const relationHeader = document.createElement('h2');
            relationHeader.className = 'accordion-header';
            relationHeader.id = `relationHeader${index}`;
            
            const relationButton = document.createElement('button');
            relationButton.className = 'accordion-button collapsed';
            relationButton.type = 'button';
            relationButton.setAttribute('data-bs-toggle', 'collapse');
            relationButton.setAttribute('data-bs-target', `#relationCollapse${index}`);
            relationButton.setAttribute('aria-expanded', 'false');
            relationButton.setAttribute('aria-controls', `relationCollapse${index}`);
            relationButton.textContent = `${relation.api_name || relation.path || '未知API'}`;
            
            relationHeader.appendChild(relationButton);
            relationItem.appendChild(relationHeader);
            
            const relationCollapse = document.createElement('div');
            relationCollapse.className = 'accordion-collapse collapse';
            relationCollapse.id = `relationCollapse${index}`;
            relationCollapse.setAttribute('aria-labelledby', `relationHeader${index}`);
            relationCollapse.setAttribute('data-bs-parent', '#relationsAccordion');
            
            const relationBody = document.createElement('div');
            relationBody.className = 'accordion-body';
            
            // API路径
            const apiPath = document.createElement('p');
            apiPath.innerHTML = `<strong>API路径:</strong> ${relation.path || '未知'}`;
            relationBody.appendChild(apiPath);
            
            // 依赖API
            if (relation.dependent_apis && relation.dependent_apis.length > 0) {
                const dependentApisTitle = document.createElement('h6');
                dependentApisTitle.textContent = '依赖API:';
                relationBody.appendChild(dependentApisTitle);
                
                const dependentApisList = document.createElement('ul');
                relation.dependent_apis.forEach(api => {
                    const apiItem = document.createElement('li');
                    apiItem.textContent = api;
                    dependentApisList.appendChild(apiItem);
                });
                relationBody.appendChild(dependentApisList);
            }
            
            // 依赖原因
            if (relation.dependency_reason) {
                const dependencyReason = document.createElement('p');
                dependencyReason.innerHTML = `<strong>依赖原因:</strong> ${relation.dependency_reason}`;
                relationBody.appendChild(dependencyReason);
            }
            
            // 数据流转
            if (relation.data_flow) {
                const dataFlow = document.createElement('p');
                dataFlow.innerHTML = `<strong>数据流转:</strong> ${relation.data_flow}`;
                relationBody.appendChild(dataFlow);
            }
            
            // 权限关系
            if (relation.permission_relation) {
                const permissionRelation = document.createElement('p');
                permissionRelation.innerHTML = `<strong>权限关系:</strong> ${relation.permission_relation}`;
                relationBody.appendChild(permissionRelation);
            }
            
            relationCollapse.appendChild(relationBody);
            relationItem.appendChild(relationCollapse);
            relationsAccordion.appendChild(relationItem);
        });
        
        relationContent.appendChild(relationsAccordion);
    }
    
    // 关键关联场景
    if (relationData.key_relation_scenarios && relationData.key_relation_scenarios.length > 0) {
        const scenariosTitle = document.createElement('h6');
        scenariosTitle.className = 'mt-4 mb-3';
        scenariosTitle.textContent = '关键关联场景';
        relationContent.appendChild(scenariosTitle);
        
        relationData.key_relation_scenarios.forEach(scenario => {
            const scenarioCard = document.createElement('div');
            scenarioCard.className = 'card mb-2';
            
            const scenarioCardBody = document.createElement('div');
            scenarioCardBody.className = 'card-body';
            
            const scenarioName = document.createElement('h6');
            scenarioName.className = 'card-title';
            scenarioName.textContent = scenario.scenario_name || '未知场景';
            
            const scenarioDescription = document.createElement('p');
            scenarioDescription.className = 'card-text';
            scenarioDescription.textContent = scenario.description || '暂无描述';
            
            // API调用序列
            if (scenario.api_call_sequence && scenario.api_call_sequence.length > 0) {
                const apiCallTitle = document.createElement('h6');
                apiCallTitle.textContent = 'API调用序列:';
                scenarioCardBody.appendChild(apiCallTitle);
                
                const apiCallList = document.createElement('ol');
                scenario.api_call_sequence.forEach(api => {
                    const apiItem = document.createElement('li');
                    apiItem.textContent = api;
                    apiCallList.appendChild(apiItem);
                });
                scenarioCardBody.appendChild(apiCallList);
            }
            
            scenarioCardBody.appendChild(scenarioName);
            scenarioCardBody.appendChild(scenarioDescription);
            scenarioCard.appendChild(scenarioCardBody);
            relationContent.appendChild(scenarioCard);
        });
    }
}

// 显示业务场景数据
function displaySceneData(sceneData) {
    const sceneContent = document.getElementById('sceneContent');
    if (!sceneContent) {
        console.error('找不到业务场景容器元素');
        return;
    }
    
    // 清空容器
    sceneContent.innerHTML = '';
    
    // 创建业务场景总览卡片
    const overviewCard = document.createElement('div');
    overviewCard.className = 'card mb-3';
    
    const overviewCardBody = document.createElement('div');
    overviewCardBody.className = 'card-body';
    
    const overviewTitle = document.createElement('h6');
    overviewTitle.className = 'card-title';
    overviewTitle.textContent = '业务场景总览';
    
    const overviewText = document.createElement('p');
    overviewText.className = 'card-text';
    overviewText.textContent = sceneData.description || '暂无描述';
    
    overviewCardBody.appendChild(overviewTitle);
    overviewCardBody.appendChild(overviewText);
    overviewCard.appendChild(overviewCardBody);
    sceneContent.appendChild(overviewCard);
    
    // 创建业务场景详情
    if (sceneData.scenes && sceneData.scenes.length > 0) {
        const scenesTitle = document.createElement('h6');
        scenesTitle.className = 'mt-4 mb-3';
        scenesTitle.textContent = '业务场景详情';
        sceneContent.appendChild(scenesTitle);
        
        const scenesAccordion = document.createElement('div');
        scenesAccordion.className = 'accordion';
        scenesAccordion.id = 'scenesAccordion';
        
        sceneData.scenes.forEach((scene, index) => {
            const sceneItem = document.createElement('div');
            sceneItem.className = 'accordion-item';
            
            const sceneHeader = document.createElement('h2');
            sceneHeader.className = 'accordion-header';
            sceneHeader.id = `sceneHeader${index}`;
            
            // 优先级标签
            let priorityBadge = '';
            if (scene.priority) {
                let badgeColor = 'secondary';
                if (scene.priority === 'P0') badgeColor = 'danger';
                else if (scene.priority === 'P1') badgeColor = 'warning';
                else if (scene.priority === 'P2') badgeColor = 'info';
                
                priorityBadge = `<span class="badge bg-${badgeColor} me-2">${scene.priority}</span>`;
            }
            
            const sceneButton = document.createElement('button');
            sceneButton.className = 'accordion-button collapsed';
            sceneButton.type = 'button';
            sceneButton.setAttribute('data-bs-toggle', 'collapse');
            sceneButton.setAttribute('data-bs-target', `#sceneCollapse${index}`);
            sceneButton.setAttribute('aria-expanded', 'false');
            sceneButton.setAttribute('aria-controls', `sceneCollapse${index}`);
            sceneButton.innerHTML = `${priorityBadge}${scene.scene_name || '未知场景'}`;
            
            sceneHeader.appendChild(sceneButton);
            sceneItem.appendChild(sceneHeader);
            
            const sceneCollapse = document.createElement('div');
            sceneCollapse.className = 'accordion-collapse collapse';
            sceneCollapse.id = `sceneCollapse${index}`;
            sceneCollapse.setAttribute('aria-labelledby', `sceneHeader${index}`);
            sceneCollapse.setAttribute('data-bs-parent', '#scenesAccordion');
            
            const sceneBody = document.createElement('div');
            sceneBody.className = 'accordion-body';
            
            // 场景描述
            if (scene.scene_description) {
                const sceneDescription = document.createElement('p');
                sceneDescription.innerHTML = `<strong>场景描述:</strong> ${scene.scene_description}`;
                sceneBody.appendChild(sceneDescription);
            }
            
            // 相关API
            if (scene.related_apis && scene.related_apis.length > 0) {
                const relatedApisTitle = document.createElement('h6');
                relatedApisTitle.textContent = '相关API:';
                sceneBody.appendChild(relatedApisTitle);
                
                const relatedApisList = document.createElement('div');
                scene.related_apis.forEach(api => {
                    const apiBadge = document.createElement('span');
                    apiBadge.className = `badge bg-${getMethodColor(api.method)} me-1 mb-1`;
                    apiBadge.textContent = `${api.method} ${api.path}`;
                    relatedApisList.appendChild(apiBadge);
                });
                sceneBody.appendChild(relatedApisList);
            }
            
            // API调用组合
            if (scene.api_call_combo && scene.api_call_combo.length > 0) {
                const apiCallTitle = document.createElement('h6');
                apiCallTitle.textContent = 'API调用组合:';
                sceneBody.appendChild(apiCallTitle);
                
                const apiCallList = document.createElement('ol');
                scene.api_call_combo.forEach(api => {
                    const apiItem = document.createElement('li');
                    apiItem.textContent = api;
                    apiCallList.appendChild(apiItem);
                });
                sceneBody.appendChild(apiCallList);
            }
            
            // 测试重点
            if (scene.test_focus && scene.test_focus.length > 0) {
                const testFocusTitle = document.createElement('h6');
                testFocusTitle.textContent = '测试重点:';
                sceneBody.appendChild(testFocusTitle);
                
                const testFocusList = document.createElement('ul');
                scene.test_focus.forEach(focus => {
                    const focusItem = document.createElement('li');
                    focusItem.textContent = focus;
                    testFocusList.appendChild(focusItem);
                });
                sceneBody.appendChild(testFocusList);
            }
            
            // 异常场景
            if (scene.exception_scenarios && scene.exception_scenarios.length > 0) {
                const exceptionTitle = document.createElement('h6');
                exceptionTitle.textContent = '异常场景:';
                sceneBody.appendChild(exceptionTitle);
                
                const exceptionList = document.createElement('ul');
                scene.exception_scenarios.forEach(exception => {
                    const exceptionItem = document.createElement('li');
                    exceptionItem.textContent = exception;
                    exceptionList.appendChild(exceptionItem);
                });
                sceneBody.appendChild(exceptionList);
            }
            
            sceneCollapse.appendChild(sceneBody);
            sceneItem.appendChild(sceneCollapse);
            scenesAccordion.appendChild(sceneItem);
        });
        
        sceneContent.appendChild(scenesAccordion);
    }
}
function getMethodColor(method) {
    const colors = {
        'get': 'success',
        'post': 'primary',
        'put': 'warning',
        'delete': 'danger',
        'patch': 'info',
        'head': 'secondary',
        'options': 'secondary'
    };
    return colors[method.toLowerCase()] || 'secondary';
}

// 从文档生成测试用例
async function generateTestCasesFromDoc(taskId) {
    try {
        showLoading();
        
        // 使用直接拼接URL的方式，避免undefined问题
        const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
        const apiUrl = baseUrl + '/api/test-cases/generate';
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task_id: taskId
            })
        });
        
        if (!response.ok) {
            throw new Error(`生成测试用例失败: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('测试用例生成结果:', result);
        
        if (result.success) {
            showNotification(`成功生成 ${result.data.test_cases_count || 0} 个测试用例`, 'success');
            
            // 刷新文档列表
            loadUploadedDocs();
        } else {
            showNotification('生成测试用例失败: ' + (result.message || '未知错误'), 'error');
        }
        
    } catch (error) {
        console.error('生成测试用例失败:', error);
        showNotification('生成测试用例失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 删除文档
function deleteDocument(taskId, docName) {
    if (!confirm(`确定要删除文档 "${docName}" 吗？`)) {
        return;
    }
    
    // 使用直接拼接URL的方式，避免undefined问题
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const apiUrl = baseUrl + '/api/docs/' + taskId;
    
    // 发送删除请求
    fetch(apiUrl, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('删除文档失败');
        }
        return response.json();
    })
    .then(data => {
        showNotification(`文档 "${docName}" 删除成功`, 'success');
        
        // 重新加载文档列表
        loadUploadedDocs();
    })
    .catch(error => {
        console.error('删除文档失败:', error);
        showNotification('删除文档失败: ' + error.message, 'error');
    });
}

// 设置拖拽上传
function setupDragAndDrop(containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn(`拖拽容器 ${containerId} 不存在`);
        return;
    }
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        container.addEventListener(eventName, function() {
            container.classList.add('dragover');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, function() {
            container.classList.remove('dragover');
        }, false);
    });
    
    container.addEventListener('drop', function(e) {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleSmartFile(files[0]);
        }
    }, false);
}




// 运行所有测试用例
function runAllCases() {
    showLoading('正在运行所有测试用例...');
    
    // 模拟运行测试用例
    setTimeout(() => {
        testCases.forEach(testCase => {
            // 随机设置测试结果
            testCase.status = Math.random() > 0.2 ? 'passed' : 'failed';
        });
        
        // 更新统计信息
        updateTestCasesStats();
        
        // 重新渲染测试用例列表
        const listViewEl = document.getElementById('listView');
        if (listViewEl) {
            const viewMode = listViewEl.checked ? 'list' : 'grid';
            renderTestCasesList(viewMode);
        }
        
        hideLoading();
        showNotification('所有测试用例运行完成', 'success');
    }, 3000);
}

// 运行单个测试用例
function runTestCase(testCaseId) {
    const testCase = testCases.find(tc => tc.id === testCaseId);
    if (!testCase) return;
    
    showLoading(`正在运行测试用例: ${testCase.name}`);
    
    // 模拟运行测试用例
    setTimeout(() => {
        // 随机设置测试结果
        testCase.status = Math.random() > 0.2 ? 'passed' : 'failed';
        
        // 更新统计信息
        updateTestCasesStats();
        
        // 重新渲染测试用例列表
        const listViewEl = document.getElementById('listView');
        if (listViewEl) {
            const viewMode = listViewEl.checked ? 'list' : 'grid';
            renderTestCasesList(viewMode);
        }
        
        hideLoading();
        showNotification(`测试用例 "${testCase.name}" 运行完成`, 'success');
    }, 1500);
}

// 编辑测试用例
function editTestCase(testCaseId) {
    const testCase = testCases.find(tc => tc.id === testCaseId);
    if (!testCase) return;
    
    showNotification(`编辑测试用例: ${testCase.name}`, 'info');
    // 这里可以打开一个模态框来编辑测试用例
}

// 删除测试用例
function deleteTestCase(testCaseId) {
    const testCase = testCases.find(tc => tc.id === testCaseId);
    if (!testCase) return;
    
    if (confirm(`确定要删除测试用例 "${testCase.name}" 吗？`)) {
        testCases = testCases.filter(tc => tc.id !== testCaseId);
        
        // 更新统计信息
        updateTestCasesStats();
        
        // 重新渲染测试用例列表
        const listViewEl = document.getElementById('listView');
        if (listViewEl) {
            const viewMode = listViewEl.checked ? 'list' : 'grid';
            renderTestCasesList(viewMode);
        }
        
        showNotification(`测试用例 "${testCase.name}" 已删除`, 'success');
    }
}

// 运行所有测试 (智能测试标签页)
function runAllTests() {
    showLoading('正在运行所有测试...');
    
    // 模拟运行测试
    setTimeout(() => {
        testCases.forEach(testCase => {
            // 随机设置测试结果
            testCase.status = Math.random() > 0.2 ? 'passed' : 'failed';
        });
        
        // 更新测试用例显示
        displayTestCases(testCases);
        
        hideLoading();
        showNotification('所有测试运行完成', 'success');
    }, 3000);
}

// 导出测试用例
function exportTestCases() {
    if (!testCases || testCases.length === 0) {
        showNotification('没有可导出的测试用例', 'error');
        return;
    }
    
    // 创建测试用例数据
    const exportData = {
        testCases: testCases,
        exportDate: new Date().toISOString(),
        apiDoc: {
            title: apiDocData?.info?.title || '未知',
            version: apiDocData?.info?.version || '未知'
        }
    };
    
    // 转换为JSON字符串
    const jsonString = JSON.stringify(exportData, null, 2);
    
    // 创建下载链接
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-cases-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification('测试用例导出成功', 'success');
}

// 保存配置
function saveConfiguration() {
    const configuration = {
        apiDocData,
        testCases,
        scenarios,
        relations
    };
    
    localStorage.setItem('testCenterConfig', JSON.stringify(configuration));
    showNotification('配置保存成功', 'success');
}

// 重置配置
function resetConfiguration() {
    if (confirm('确定要重置所有配置吗？这将清除所有数据。')) {
        localStorage.removeItem('testCenterConfig');
        
        // 重置全局变量
        apiDocData = null;
        testCases = [];
        scenarios = [];
        relations = [];
        selectedApis = new Set();
        
        // 重置UI
        removeSmartFile();
        goToStep(1);
        
        showNotification('配置已重置', 'success');
    }
}

// 完成流程
function finishProcess() {
    if (confirm('确定要完成测试生成流程吗？')) {
        // 保存配置
        saveConfiguration();
        
        // 切换到测试用例标签页
        const testCasesTab = document.getElementById('test-cases-tab');
        if (testCasesTab) {
            testCasesTab.click();
            
            // 重新加载测试用例
            loadTestCases();
        } else {
            console.warn('测试用例标签页不存在');
        }
        
        showNotification('测试生成流程已完成', 'success');
    }
}

// 显示添加场景模态框
function showAddSceneModal() {
    const addSceneModal = document.getElementById('addSceneModal');
    if (!addSceneModal) {
        console.warn('添加场景模态框不存在');
        return;
    }
    
    const modal = new bootstrap.Modal(addSceneModal);
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            // 填充API复选框
            const sceneApis = document.getElementById('sceneApis');
            if (!sceneApis) {
                console.warn('场景API容器不存在');
                return;
            }
            
            sceneApis.innerHTML = '';
            
            endpoints.forEach(endpoint => {
                const div = document.createElement('div');
                div.className = 'form-check';
                
                const input = document.createElement('input');
                input.className = 'form-check-input';
                input.type = 'checkbox';
                input.value = `${endpoint.method}:${endpoint.path}`;
                input.id = `api-${endpoint.method}-${endpoint.path.replace(/[^a-zA-Z0-9]/g, '-')}`;
                
                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = input.id;
                label.textContent = `${endpoint.method} ${endpoint.path}`;
                
                div.appendChild(input);
                div.appendChild(label);
                sceneApis.appendChild(div);
            });
            
            modal.show();
        })
        .catch(error => {
            showNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 保存场景
function saveScene() {
    const sceneNameEl = document.getElementById('sceneName');
    const sceneDescriptionEl = document.getElementById('sceneDescription');
    
    if (!sceneNameEl || !sceneDescriptionEl) {
        console.warn('场景表单元素不存在');
        return;
    }
    
    const sceneName = sceneNameEl.value.trim();
    const sceneDescription = sceneDescriptionEl.value.trim();
    
    if (!sceneName) {
        showNotification('请输入场景名称', 'error');
        return;
    }
    
    // 获取选中的API
    const selectedApiElements = document.querySelectorAll('#sceneApis input:checked');
    if (selectedApiElements.length === 0) {
        showNotification('请选择至少一个API', 'error');
        return;
    }
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            const selectedApis = Array.from(selectedApiElements).map(input => {
                const [method, path] = input.value.split(':');
                return endpoints.find(endpoint => endpoint.method === method && endpoint.path === path);
            });
            
            // 创建新场景
            const newScene = {
                id: `scene-${Date.now()}`,
                name: sceneName,
                description: sceneDescription,
                apis: selectedApis
            };
            
            scenarios.push(newScene);
            
            // 更新场景列表显示
            displayScenariosList(scenarios);
            
            // 关闭模态框
            const addSceneModal = document.getElementById('addSceneModal');
            if (addSceneModal) {
                const modal = bootstrap.Modal.getInstance(addSceneModal);
                if (modal) {
                    modal.hide();
                }
            }
            
            // 清空表单
            sceneNameEl.value = '';
            sceneDescriptionEl.value = '';
            
            showNotification('场景添加成功', 'success');
        })
        .catch(error => {
            showNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 显示添加依赖关系模态框
function showAddRelationModal() {
    const addRelationModal = document.getElementById('addRelationModal');
    if (!addRelationModal) {
        console.warn('添加依赖关系模态框不存在');
        return;
    }
    
    const modal = new bootstrap.Modal(addRelationModal);
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            // 填充源API和目标API下拉框
            const relationSource = document.getElementById('relationSource');
            const relationTarget = document.getElementById('relationTarget');
            
            if (!relationSource || !relationTarget) {
                console.warn('依赖关系表单元素不存在');
                return;
            }
            
            relationSource.innerHTML = '';
            relationTarget.innerHTML = '';
            
            endpoints.forEach(endpoint => {
                const option1 = document.createElement('option');
                option1.value = `${endpoint.method}:${endpoint.path}`;
                option1.textContent = `${endpoint.method} ${endpoint.path}`;
                relationSource.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = `${endpoint.method}:${endpoint.path}`;
                option2.textContent = `${endpoint.method} ${endpoint.path}`;
                relationTarget.appendChild(option2);
            });
            
            modal.show();
        })
        .catch(error => {
            showNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 渲染已上传文档列表
function renderUploadedDocsList(docs) {
    const docsListContainer = document.getElementById('uploadedDocsList');
    if (!docsListContainer) {
        console.warn('已上传文档列表容器不存在');
        return;
    }
    
    docsListContainer.innerHTML = '';
    
    if (docs.length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'text-center text-muted py-4';
        emptyMessage.innerHTML = '<i class="fas fa-file-upload fa-3x mb-3"></i><p>暂无已上传的文档</p>';
        docsListContainer.appendChild(emptyMessage);
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'table table-hover';
    
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    const headers = ['文件名', '上传时间', '文件大小', '操作'];
    headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText;
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    const tbody = document.createElement('tbody');
    
    docs.forEach(doc => {
        const row = document.createElement('tr');
        
        // 文件名
        const nameCell = document.createElement('td');
        const nameLink = document.createElement('a');
        nameLink.href = '#';
        nameLink.textContent = doc.filename || doc.name || '未知文件';
        nameLink.addEventListener('click', (e) => {
            e.preventDefault();
            // 可以添加查看文档详情的逻辑
            showNotification(`查看文档: ${doc.filename || doc.name}`, 'info');
        });
        nameCell.appendChild(nameLink);
        row.appendChild(nameCell);
        
        // 上传时间
        const timeCell = document.createElement('td');
        timeCell.textContent = formatDateTime(doc.upload_time || doc.createdAt || new Date());
        row.appendChild(timeCell);
        
        // 文件大小
        const sizeCell = document.createElement('td');
        sizeCell.textContent = formatFileSize(doc.file_size || doc.size || 0);
        row.appendChild(sizeCell);
        
        // 操作
        const actionsCell = document.createElement('td');
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.title = '删除文档';
        deleteBtn.addEventListener('click', () => {
            if (confirm(`确定要删除文档 "${doc.filename || doc.name}" 吗？`)) {
                deleteUploadedDoc(doc.id || doc._id);
            }
        });
        
        actionsCell.appendChild(deleteBtn);
        row.appendChild(actionsCell);
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    docsListContainer.appendChild(table);
}

// 删除已上传文档
function deleteUploadedDoc(docId) {
    if (!docId) {
        showNotification('文档ID无效', 'error');
        return;
    }
    
    showLoading('正在删除文档...');
    
    // 使用直接拼接URL的方式，避免undefined问题
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const deleteUrl = baseUrl + '/api/docs/' + docId;
    
    fetch(deleteUrl, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        showNotification('文档删除成功', 'success');
        
        // 重新加载文档列表
        loadUploadedDocs();
    })
    .catch(error => {
        hideLoading();
        showNotification('文档删除失败: ' + error.message, 'error');
        console.error('文档删除失败:', error);
    });
}

// 显示上传进度
function showUploadProgress() {
    const progressElement = document.getElementById('uploadProgress');
    if (progressElement) {
        progressElement.style.display = 'block';
    }
}

// 隐藏上传进度
function hideUploadProgress() {
    const progressElement = document.getElementById('uploadProgress');
    if (progressElement) {
        progressElement.style.display = 'none';
    }
}

// 显示加载遮罩
function showLoading(message = '正在处理，请稍候...') {
    try {
        const loadingMessage = document.getElementById('loadingMessage');
        const loadingOverlay = document.getElementById('loadingOverlay');
        
        if (loadingMessage) {
            loadingMessage.textContent = message;
        } else {
            console.warn('加载消息元素不存在');
        }
        
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
            console.log('加载遮罩层已显示，消息:', message);
        } else {
            console.warn('加载遮罩元素不存在');
        }
        
        // 添加超时自动隐藏机制，防止卡住
        setTimeout(() => {
            if (loadingOverlay && loadingOverlay.style.display === 'flex') {
                console.warn('加载遮罩层显示超过10秒，自动隐藏');
                hideLoading();
            }
        }, 10000);
    } catch (error) {
        console.error('显示加载遮罩层时出错:', error);
    }
}

// 隐藏加载遮罩
function hideLoading() {
    try {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
            console.log('加载遮罩层已隐藏');
        } else {
            console.warn('加载遮罩元素不存在');
        }
    } catch (error) {
        console.error('隐藏加载遮罩层时出错:', error);
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(notification);
    
    // 自动移除通知
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '未知';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '未知';
    
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}