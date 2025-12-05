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

// 初始化测试中心
function initTestCenter() {
    // 初始化智能测试生成功能
    initSmartTestTab();
    
    // 初始化测试用例功能
    initTestCasesTab();
    
    // 加载已保存的数据
    loadSavedData();
}



// 初始化智能测试标签页
function initSmartTestTab() {
    // 文件上传按钮
    document.getElementById('smartUploadBtn').addEventListener('click', function() {
        document.getElementById('smartFileInput').click();
    });
    
    // 文件选择
    document.getElementById('smartFileInput').addEventListener('change', handleSmartFileSelect);
    
    // URL获取按钮
    document.getElementById('smartFetchUrlBtn').addEventListener('click', fetchSmartApiFromUrl);
    
    // 移除文件按钮
    document.getElementById('smartRemoveFileBtn').addEventListener('click', removeSmartFile);
    
    // 分析按钮
    document.getElementById('smartAnalyzeBtn').addEventListener('click', analyzeSmartApiDoc);
    
    // 文本输入监听
    document.getElementById('apiTextInput').addEventListener('input', function() {
        const parseBtn = document.getElementById('parseTextBtn');
        parseBtn.disabled = this.value.trim() === '';
    });
    
    // 解析文本按钮
    document.getElementById('parseTextBtn').addEventListener('click', parseApiText);
    
    // 步骤导航按钮
    document.getElementById('backToStep1Btn').addEventListener('click', function() {
        goToStep(1);
    });
    
    document.getElementById('backToStep2Btn').addEventListener('click', function() {
        goToStep(2);
    });
    
    document.getElementById('generateBtn').addEventListener('click', generateTestCases);
    
    // 添加场景按钮
    document.getElementById('addSceneBtn').addEventListener('click', showAddSceneModal);
    
    // 添加依赖关系按钮
    document.getElementById('addRelationBtn').addEventListener('click', showAddRelationModal);
    
    // 保存场景按钮
    document.getElementById('saveSceneBtn').addEventListener('click', saveScene);
    
    // 保存依赖关系按钮
    document.getElementById('saveRelationBtn').addEventListener('click', saveRelation);
    
    // 导出按钮
    document.getElementById('exportBtn').addEventListener('click', exportTestCases);
    
    // 运行测试按钮
    document.getElementById('runTestsBtn').addEventListener('click', runAllTests);
    
    // 保存配置按钮
    document.getElementById('saveBtn').addEventListener('click', saveConfiguration);
    
    // 重置按钮
    document.getElementById('resetBtn').addEventListener('click', resetConfiguration);
    
    // 完成按钮
    document.getElementById('finishBtn').addEventListener('click', finishProcess);
    
    // 拖拽上传
    setupDragAndDrop('smartUploadContainer');
}

// 初始化测试用例标签页
function initTestCasesTab() {
    // 运行所有测试按钮
    document.getElementById('runAllCasesBtn').addEventListener('click', runAllCases);
    
    // 生成测试用例按钮
    document.getElementById('generateCasesBtn').addEventListener('click', function() {
        // 切换到智能测试生成标签页
        document.getElementById('smart-test-tab').click();
    });
    
    // 搜索输入
    document.getElementById('searchCasesInput').addEventListener('input', filterTestCases);
    
    // 筛选器
    document.getElementById('statusFilter').addEventListener('change', filterTestCases);
    document.getElementById('typeFilter').addEventListener('change', filterTestCases);
    document.getElementById('apiFilter').addEventListener('change', filterTestCases);
    
    // 视图模式切换
    document.getElementById('listView').addEventListener('change', function() {
        if (this.checked) {
            renderTestCasesList('list');
        }
    });
    
    document.getElementById('gridView').addEventListener('change', function() {
        if (this.checked) {
            renderTestCasesList('grid');
        }
    });
    
    // 加载测试用例
    loadTestCases();
}

// 设置拖拽上传
function setupDragAndDrop(containerId) {
    const container = document.getElementById(containerId);
    
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

















// 处理文件选择 (智能测试标签页)
function handleSmartFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleSmartFile(file);
    }
}

// 处理文件 (智能测试标签页)
function handleSmartFile(file) {
    // 验证文件类型
    const validTypes = ['application/json', 'text/yaml', 'application/x-yaml', 'text/plain'];
    const validExtensions = ['.json', '.yaml', '.yml'];
    
    const isValidType = validTypes.includes(file.type) || 
                       validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    
    if (!isValidType) {
        showNotification('请上传JSON或YAML格式的API文档', 'error');
        return;
    }
    
    // 显示上传进度
    showUploadProgress();
    
    // 读取文件
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const content = e.target.result;
            parseSmartApiDocContent(content, file.name, file.size);
        } catch (error) {
            showNotification('文件解析失败: ' + error.message, 'error');
            hideUploadProgress();
        }
    };
    
    reader.onerror = function() {
        showNotification('文件读取失败', 'error');
        hideUploadProgress();
    };
    
    reader.readAsText(file);
}

// 从URL获取API文档 (智能测试标签页)
function fetchSmartApiFromUrl() {
    const url = document.getElementById('smartApiUrl').value.trim();
    if (!url) {
        showNotification('请输入API文档URL', 'error');
        return;
    }
    
    showUploadProgress();
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(content => {
            const fileName = url.split('/').pop() || 'api-doc';
            parseSmartApiDocContent(content, fileName, content.length);
        })
        .catch(error => {
            showNotification('获取API文档失败: ' + error.message, 'error');
            hideUploadProgress();
        });
}

// 解析API文档内容 (智能测试标签页)
function parseSmartApiDocContent(content, fileName, fileSize) {
    try {
        // 尝试解析为JSON
        let apiDoc;
        try {
            apiDoc = JSON.parse(content);
        } catch (e) {
            // 如果不是JSON，尝试解析为YAML
            apiDoc = jsyaml.load(content);
        }
        
        // 验证是否为有效的OpenAPI文档
        if (!apiDoc.openapi) {
            throw new Error('不是有效的OpenAPI 3.0.0文档');
        }
        
        // 保存API文档数据
        apiDocData = apiDoc;
        
        // 显示文件信息
        showSmartFileInfo(fileName, fileSize, apiDoc);
        
        hideUploadProgress();
        showNotification('API文档上传成功', 'success');
    } catch (error) {
        showNotification('API文档解析失败: ' + error.message, 'error');
        hideUploadProgress();
    }
}

// 显示文件信息 (智能测试标签页)
function showSmartFileInfo(fileName, fileSize, apiDoc) {
    document.getElementById('smartFileName').textContent = fileName;
    document.getElementById('smartFileSize').textContent = formatFileSize(fileSize);
    document.getElementById('smartApiVersion').textContent = apiDoc.openapi || '未知';
    document.getElementById('smartApiTitle').textContent = apiDoc.info?.title || '未知';
    document.getElementById('smartFileInfo').style.display = 'block';
}

// 移除文件 (智能测试标签页)
function removeSmartFile() {
    apiDocData = null;
    document.getElementById('smartFileInfo').style.display = 'none';
    document.getElementById('smartFileInput').value = '';
    document.getElementById('smartApiUrl').value = '';
    document.getElementById('apiTextInput').value = '';
    document.getElementById('parseTextBtn').disabled = true;
}

// 解析API文本 (智能测试标签页)
function parseApiText() {
    const content = document.getElementById('apiTextInput').value.trim();
    if (!content) {
        showNotification('请输入API文档内容', 'error');
        return;
    }
    
    try {
        // 尝试解析为JSON
        let apiDoc;
        try {
            apiDoc = JSON.parse(content);
        } catch (e) {
            // 如果不是JSON，尝试解析为YAML
            apiDoc = jsyaml.load(content);
        }
        
        // 验证是否为有效的OpenAPI文档
        if (!apiDoc.openapi) {
            throw new Error('不是有效的OpenAPI 3.0.0文档');
        }
        
        // 保存API文档数据
        apiDocData = apiDoc;
        
        // 显示文件信息
        showSmartFileInfo('文本输入', content.length, apiDoc);
        
        showNotification('API文档解析成功', 'success');
    } catch (error) {
        showNotification('API文档解析失败: ' + error.message, 'error');
    }
}

// 分析API文档 (智能测试标签页)
function analyzeSmartApiDoc() {
    if (!apiDocData) {
        showNotification('请先上传API文档', 'error');
        return;
    }
    
    showLoading('正在分析API文档...');
    
    // 提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            // 生成场景和依赖关系
            generateScenariosAndRelations(endpoints)
                .then(data => {
                    scenarios = data.scenarios;
                    relations = data.relations;
                    
                    // 显示步骤2内容
                    displayStep2Content(endpoints, scenarios, relations);
                    
                    hideLoading();
                    showNotification('API文档分析完成', 'success');
                    
                    // 进入步骤2
                    goToStep(2);
                })
                .catch(error => {
                    hideLoading();
                    showNotification('API文档分析失败: ' + error.message, 'error');
                });
        })
        .catch(error => {
            hideLoading();
            showNotification('API文档分析失败: ' + error.message, 'error');
        });
}

// 显示步骤2内容
function displayStep2Content(endpoints, scenarios, relations) {
    // 显示API列表
    displayApiList(endpoints);
    
    // 显示场景列表
    displayScenariosList(scenarios);
    
    // 显示依赖关系列表
    displayRelationsList(relations);
}

// 显示API列表
function displayApiList(endpoints) {
    const apiList = document.getElementById('apiList');
    apiList.innerHTML = '';
    
    endpoints.forEach(endpoint => {
        const apiItem = document.createElement('div');
        apiItem.className = 'card mb-2';
        
        const apiCardBody = document.createElement('div');
        apiCardBody.className = 'card-body p-2';
        
        const apiTitle = document.createElement('div');
        apiTitle.className = 'd-flex justify-content-between align-items-center';
        
        const methodBadge = document.createElement('span');
        methodBadge.className = `method-badge method-${endpoint.method.toLowerCase()}`;
        methodBadge.textContent = endpoint.method;
        
        const apiPath = document.createElement('span');
        apiPath.className = 'fw-bold';
        apiPath.textContent = endpoint.path;
        
        apiTitle.appendChild(methodBadge);
        apiTitle.appendChild(apiPath);
        
        const apiDescription = document.createElement('div');
        apiDescription.className = 'small text-muted mt-1';
        apiDescription.textContent = endpoint.summary || endpoint.description || '无描述';
        
        apiCardBody.appendChild(apiTitle);
        apiCardBody.appendChild(apiDescription);
        apiItem.appendChild(apiCardBody);
        apiList.appendChild(apiItem);
    });
}

// 显示场景列表
function displayScenariosList(scenarios) {
    const scenesList = document.getElementById('scenesList');
    scenesList.innerHTML = '';
    
    scenarios.forEach(scene => {
        const sceneCard = document.createElement('div');
        sceneCard.className = 'card scene-card';
        
        const sceneCardBody = document.createElement('div');
        sceneCardBody.className = 'card-body';
        
        const sceneTitle = document.createElement('h6');
        sceneTitle.className = 'card-title';
        sceneTitle.textContent = scene.name;
        
        const sceneDescription = document.createElement('p');
        sceneDescription.className = 'card-text small';
        sceneDescription.textContent = scene.description;
        
        const sceneApis = document.createElement('div');
        sceneApis.className = 'mt-2';
        
        scene.apis.forEach(api => {
            const apiBadge = document.createElement('span');
            apiBadge.className = `api-badge method-${api.method.toLowerCase()}`;
            apiBadge.textContent = `${api.method} ${api.path}`;
            sceneApis.appendChild(apiBadge);
        });
        
        sceneCardBody.appendChild(sceneTitle);
        sceneCardBody.appendChild(sceneDescription);
        sceneCardBody.appendChild(sceneApis);
        sceneCard.appendChild(sceneCardBody);
        scenesList.appendChild(sceneCard);
    });
}

// 显示依赖关系列表
function displayRelationsList(relations) {
    const relationsList = document.getElementById('relationsList');
    relationsList.innerHTML = '';
    
    relations.forEach(relation => {
        const relationCard = document.createElement('div');
        relationCard.className = 'card relation-card';
        
        const relationCardBody = document.createElement('div');
        relationCardBody.className = 'card-body';
        
        const relationTitle = document.createElement('h6');
        relationTitle.className = 'card-title';
        
        const sourceApi = `${relation.source.method} ${relation.source.path}`;
        const targetApi = `${relation.target.method} ${relation.target.path}`;
        
        relationTitle.textContent = `${sourceApi} → ${targetApi}`;
        
        const relationDescription = document.createElement('p');
        relationDescription.className = 'card-text small';
        relationDescription.textContent = relation.description;
        
        const relationType = document.createElement('span');
        relationType.className = 'badge bg-primary';
        relationType.textContent = getRelationTypeLabel(relation.type);
        
        relationCardBody.appendChild(relationTitle);
        relationCardBody.appendChild(relationDescription);
        relationCardBody.appendChild(relationType);
        relationCard.appendChild(relationCardBody);
        relationsList.appendChild(relationCard);
    });
}

// 生成测试用例
function generateTestCases() {
    showLoading('正在生成测试用例...');
    
    // 模拟生成测试用例
    setTimeout(() => {
        // 首先提取API端点
        extractApiEndpoints(apiDocData)
            .then(endpoints => {
                testCases = generateMockTestCases(endpoints, scenarios, relations);
                
                // 显示测试用例
                displayTestCases(testCases);
                
                hideLoading();
                showNotification('测试用例生成完成', 'success');
                
                // 进入步骤3
                goToStep(3);
            })
            .catch(error => {
                hideLoading();
                showNotification('测试用例生成失败: ' + error.message, 'error');
            });
    }, 2000);
}

// 显示测试用例
function displayTestCases(testCases) {
    const testCasesList = document.getElementById('testCasesList');
    testCasesList.innerHTML = '';
    
    testCases.forEach(testCase => {
        const testCaseCard = document.createElement('div');
        testCaseCard.className = 'card test-case-card';
        
        const testCaseCardBody = document.createElement('div');
        testCaseCardBody.className = 'card-body';
        
        const testCaseTitle = document.createElement('h6');
        testCaseTitle.className = 'card-title';
        testCaseTitle.textContent = testCase.name;
        
        const testCaseDescription = document.createElement('p');
        testCaseDescription.className = 'card-text small';
        testCaseDescription.textContent = testCase.description;
        
        const testCaseType = document.createElement('span');
        testCaseType.className = 'badge bg-secondary';
        testCaseType.textContent = getTestCaseTypeLabel(testCase.type);
        
        const testCaseApi = document.createElement('span');
        testCaseApi.className = `api-badge method-${testCase.api.method.toLowerCase()} ms-2`;
        testCaseApi.textContent = `${testCase.api.method} ${testCase.api.path}`;
        
        testCaseCardBody.appendChild(testCaseTitle);
        testCaseCardBody.appendChild(testCaseDescription);
        testCaseCardBody.appendChild(testCaseType);
        testCaseCardBody.appendChild(testCaseApi);
        testCaseCard.appendChild(testCaseCardBody);
        testCasesList.appendChild(testCaseCard);
    });
}

// 加载测试用例 (测试用例标签页)
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
    
    document.getElementById('totalCases').textContent = totalCases;
    document.getElementById('passedCases').textContent = passedCases;
    document.getElementById('failedCases').textContent = failedCases;
    document.getElementById('passRate').textContent = passRate + '%';
}

// 渲染测试用例列表
function renderTestCasesList(viewMode) {
    const container = document.getElementById('testCasesListContainer');
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
    apiFilter.innerHTML = '<option value="">所有API</option>';
    
    const uniqueApis = [...new Set(testCases.map(tc => `${tc.api.method} ${tc.api.path}`))];
    
    uniqueApis.forEach(api => {
        const option = document.createElement('option');
        option.value = api;
        option.textContent = api;
        apiFilter.appendChild(option);
    });
}

// 筛选测试用例
function filterTestCases() {
    const searchTerm = document.getElementById('searchCasesInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const typeFilter = document.getElementById('typeFilter').value;
    const apiFilter = document.getElementById('apiFilter').value;
    
    const filteredCases = testCases.filter(testCase => {
        const matchesSearch = testCase.name.toLowerCase().includes(searchTerm) || 
                             testCase.description.toLowerCase().includes(searchTerm);
        
        const matchesStatus = !statusFilter || testCase.status === statusFilter;
        
        const matchesType = !typeFilter || testCase.type === typeFilter;
        
        const matchesApi = !apiFilter || `${testCase.api.method} ${testCase.api.path}` === apiFilter;
        
        return matchesSearch && matchesStatus && matchesType && matchesApi;
    });
    
    // 临时替换testCases数组并重新渲染
    const originalCases = testCases;
    testCases = filteredCases;
    
    const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
    renderTestCasesList(viewMode);
    
    // 恢复原始数组
    testCases = originalCases;
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
        const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
        renderTestCasesList(viewMode);
        
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
        const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
        renderTestCasesList(viewMode);
        
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
        const viewMode = document.getElementById('listView').checked ? 'list' : 'grid';
        renderTestCasesList(viewMode);
        
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
        document.getElementById('test-cases-tab').click();
        
        // 重新加载测试用例
        loadTestCases();
        
        showNotification('测试生成流程已完成', 'success');
    }
}

// 显示添加场景模态框
function showAddSceneModal() {
    const modal = new bootstrap.Modal(document.getElementById('addSceneModal'));
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            // 填充API复选框
            const sceneApis = document.getElementById('sceneApis');
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
    const sceneName = document.getElementById('sceneName').value.trim();
    const sceneDescription = document.getElementById('sceneDescription').value.trim();
    
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
            const modal = bootstrap.Modal.getInstance(document.getElementById('addSceneModal'));
            modal.hide();
            
            // 清空表单
            document.getElementById('sceneName').value = '';
            document.getElementById('sceneDescription').value = '';
            
            showNotification('场景添加成功', 'success');
        })
        .catch(error => {
            showNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 显示添加依赖关系模态框
function showAddRelationModal() {
    const modal = new bootstrap.Modal(document.getElementById('addRelationModal'));
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            // 填充源API和目标API下拉框
            const relationSource = document.getElementById('relationSource');
            const relationTarget = document.getElementById('relationTarget');
            
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

// 保存依赖关系
function saveRelation() {
    const sourceValue = document.getElementById('relationSource').value;
    const targetValue = document.getElementById('relationTarget').value;
    const relationType = document.getElementById('relationType').value;
    const relationDescription = document.getElementById('relationDescription').value.trim();
    
    if (!sourceValue || !targetValue) {
        showNotification('请选择源API和目标API', 'error');
        return;
    }
    
    if (sourceValue === targetValue) {
        showNotification('源API和目标API不能相同', 'error');
        return;
    }
    
    const [sourceMethod, sourcePath] = sourceValue.split(':');
    const [targetMethod, targetPath] = targetValue.split(':');
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            const sourceApi = endpoints.find(endpoint => endpoint.method === sourceMethod && endpoint.path === sourcePath);
            const targetApi = endpoints.find(endpoint => endpoint.method === targetMethod && endpoint.path === targetPath);
            
            // 创建新依赖关系
            const newRelation = {
                id: `relation-${Date.now()}`,
                source: sourceApi,
                target: targetApi,
                type: relationType,
                description: relationDescription || `${sourceMethod} ${sourcePath} 依赖于 ${targetMethod} ${targetPath}`
            };
            
            relations.push(newRelation);
            
            // 更新依赖关系列表显示
            displayRelationsList(relations);
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('addRelationModal'));
            modal.hide();
            
            // 清空表单
            document.getElementById('relationDescription').value = '';
            
            showNotification('依赖关系添加成功', 'success');
        })
        .catch(error => {
            showNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 切换到指定步骤
function goToStep(step) {
    // 隐藏所有步骤内容
    document.querySelectorAll('.step-content').forEach(content => {
        content.style.display = 'none';
    });
    
    // 更新步骤指示器
    document.querySelectorAll('.step').forEach((stepElement, index) => {
        stepElement.classList.remove('active', 'completed');
        if (index + 1 < step) {
            stepElement.classList.add('completed');
        } else if (index + 1 === step) {
            stepElement.classList.add('active');
        }
    });
    
    // 显示当前步骤内容
    document.getElementById(`step${step}Content`).style.display = 'block';
    
    currentStep = step;
}

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
                document.getElementById('analyzeBtn').disabled = false;
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

// 提取API端点
async function extractApiEndpoints(apiDoc) {
    const endpoints = [];
    const paths = apiDoc.paths || {};
    
    for (const path in paths) {
        const pathItem = paths[path];
        
        for (const method in pathItem) {
            if (['get', 'post', 'put', 'delete', 'patch', 'head', 'options'].includes(method)) {
                const operation = pathItem[method];
                
                endpoints.push({
                    method: method.toUpperCase(),
                    path,
                    operationId: operation.operationId,
                    summary: operation.summary,
                    description: operation.description,
                    parameters: operation.parameters || [],
                    requestBody: operation.requestBody,
                    responses: operation.responses || {}
                });
            }
        }
    }
    
    return endpoints;
}

// 生成场景和依赖关系
async function generateScenariosAndRelations(endpoints) {
    // 模拟生成场景
    const scenarios = [
        {
            id: 'scene-1',
            name: '用户认证场景',
            description: '包括用户登录、注册和获取用户信息的API',
            apis: endpoints.filter(e => e.path.includes('/auth') || e.path.includes('/user'))
        },
        {
            id: 'scene-2',
            name: '数据管理场景',
            description: '包括创建、读取、更新和删除数据的API',
            apis: endpoints.filter(e => ['POST', 'GET', 'PUT', 'DELETE'].includes(e.method))
        }
    ];
    
    // 模拟生成依赖关系
    const relations = [];
    
    // 查找认证相关的API
    const authApis = endpoints.filter(e => e.path.includes('/auth') || e.path.includes('/login'));
    
    // 为其他API创建对认证API的依赖
    endpoints.forEach(endpoint => {
        if (!endpoint.path.includes('/auth') && authApis.length > 0) {
            relations.push({
                id: `relation-${endpoint.method}-${endpoint.path}`,
                source: endpoint,
                target: authApis[0],
                type: 'auth',
                description: `${endpoint.method} ${endpoint.path} 需要先进行认证`
            });
        }
    });
    
    return { scenarios, relations };
}

// 生成模拟测试用例
function generateMockTestCases(endpoints, scenarios, relations) {
    const testCases = [];
    
    // 为每个API端点生成基础测试用例
    endpoints.forEach(endpoint => {
        // 基础测试
        testCases.push({
            id: `test-${endpoint.method}-${endpoint.path}-basic`,
            name: `基础测试 - ${endpoint.method} ${endpoint.path}`,
            description: `测试${endpoint.method} ${endpoint.path}的基本功能`,
            type: 'basic',
            api: endpoint,
            status: 'passed'
        });
        
        // 边界值测试
        testCases.push({
            id: `test-${endpoint.method}-${endpoint.path}-boundary`,
            name: `边界值测试 - ${endpoint.method} ${endpoint.path}`,
            description: `测试${endpoint.method} ${endpoint.path}的边界值情况`,
            type: 'boundary',
            api: endpoint,
            status: Math.random() > 0.2 ? 'passed' : 'failed'
        });
        
        // 异常测试
        testCases.push({
            id: `test-${endpoint.method}-${endpoint.path}-exception`,
            name: `异常测试 - ${endpoint.method} ${endpoint.path}`,
            description: `测试${endpoint.method} ${endpoint.path}的异常处理`,
            type: 'exception',
            api: endpoint,
            status: Math.random() > 0.3 ? 'passed' : 'failed'
        });
    });
    
    // 为每个场景生成场景测试用例
    scenarios.forEach(scene => {
        testCases.push({
            id: `test-scene-${scene.id}`,
            name: `场景测试 - ${scene.name}`,
            description: `测试${scene.name}的完整流程`,
            type: 'scenario',
            api: scene.apis[0] || endpoints[0], // 使用场景的第一个API作为代表
            status: Math.random() > 0.4 ? 'passed' : 'failed'
        });
    });
    
    return testCases;
}

// 获取关系类型标签
function getRelationTypeLabel(type) {
    const labels = {
        'data': '数据依赖',
        'sequence': '顺序依赖',
        'auth': '认证依赖'
    };
    
    return labels[type] || type;
}

// 获取测试用例类型标签
function getTestCaseTypeLabel(type) {
    const labels = {
        'basic': '基础测试',
        'scenario': '场景测试',
        'boundary': '边界值测试',
        'exception': '异常测试'
    };
    
    return labels[type] || type;
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
    document.getElementById('loadingMessage').textContent = message;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

// 隐藏加载遮罩
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
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