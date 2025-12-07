// API测试工作流程页面JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 全局变量
    let currentStep = 1;
    let apiData = [];
    let selectedApis = [];
    let testCases = [];
    let testResults = [];
    
    // DOM元素 - 更新为与test-center.html匹配的ID
    const steps = document.querySelectorAll('.step');
    const stepContents = document.querySelectorAll('.step-content');
    const prevStepBtn = document.getElementById('backToStep1Btn') || document.getElementById('backToStep2Btn');
    const nextStepBtn = document.getElementById('generateBtn') || document.getElementById('finishBtn');
    const fileInput = document.getElementById('smartFileInput');
    const uploadContainer = document.getElementById('smartUploadContainer');
    const apiListContainer = document.getElementById('apiList');
    const sceneListContainer = document.getElementById('scenesList');
    const relationListContainer = document.getElementById('relationsList');
    const testCaseListContainer = document.getElementById('testCasesList');
    const testResultContainer = document.getElementById('testResultContainer');
    const generateTestCasesBtn = document.getElementById('generateBtn');
    const runTestsBtn = document.getElementById('runTestsBtn');
    
    // 初始化
    init();
    
    function init() {
        // 初始化步骤指示器
        updateStepIndicator();
        
        // 绑定事件
        bindEvents();
        
        // 显示第一步
        showStep(1);
    }
    
    function bindEvents() {
        // 步骤导航按钮
        if (prevStepBtn) {
            prevStepBtn.addEventListener('click', goToPrevStep);
        }
        
        if (nextStepBtn) {
            nextStepBtn.addEventListener('click', goToNextStep);
        }
        
        // 文件上传
        if (fileInput) {
            fileInput.addEventListener('change', handleFileSelect);
        }
        
        // 拖拽上传
        if (uploadContainer) {
            uploadContainer.addEventListener('dragover', handleDragOver);
            uploadContainer.addEventListener('dragleave', handleDragLeave);
            uploadContainer.addEventListener('drop', handleFileDrop);
        }
        
        // 生成测试用例按钮
        if (generateTestCasesBtn) {
            generateTestCasesBtn.addEventListener('click', generateTestCases);
        }
        
        // 运行测试按钮
        if (runTestsBtn) {
            runTestsBtn.addEventListener('click', runTests);
        }
    }
    
    // 步骤导航功能
    function showStep(stepNumber) {
        // 隐藏所有步骤内容
        stepContents.forEach(content => {
            content.style.display = 'none';
        });
        
        // 显示当前步骤内容 - 更新为与test-center.html匹配的ID
        const stepContent = document.getElementById(`step${stepNumber}Content`);
        if (stepContent) {
            stepContent.style.display = 'block';
        }
        
        // 更新步骤指示器
        updateStepIndicator();
        
        // 更新导航按钮状态
        updateNavigationButtons();
        
        // 根据步骤执行特定操作
        switch(stepNumber) {
            case 2:
                if (apiData.length > 0) {
                    displayApiList();
                    analyzeScenarios();
                    analyzeRelations();
                }
                break;
            case 3:
                if (selectedApis.length > 0) {
                    displayTestCases();
                }
                break;
            case 4:
                if (testCases.length > 0) {
                    displayTestResults();
                }
                break;
        }
    }
    
    function goToPrevStep() {
        if (currentStep > 1) {
            currentStep--;
            showStep(currentStep);
        }
    }
    
    function goToNextStep() {
        if (currentStep < 4) {
            // 验证当前步骤是否完成
            if (validateCurrentStep()) {
                currentStep++;
                showStep(currentStep);
            }
        }
    }
    
    function validateCurrentStep() {
        switch(currentStep) {
            case 1:
                return apiData.length > 0;
            case 2:
                return selectedApis.length > 0;
            case 3:
                return testCases.length > 0;
            default:
                return true;
        }
    }
    
    function updateStepIndicator() {
        steps.forEach((step, index) => {
            const stepNumber = index + 1;
            
            // 移除所有状态类
            step.classList.remove('active', 'completed');
            
            // 添加适当的状态类
            if (stepNumber === currentStep) {
                step.classList.add('active');
            } else if (stepNumber < currentStep) {
                step.classList.add('completed');
            }
        });
    }
    
    function updateNavigationButtons() {
        // 更新上一步按钮
        if (prevStepBtn) {
            prevStepBtn.style.display = currentStep === 1 ? 'none' : 'inline-block';
        }
        
        // 更新下一步按钮
        if (nextStepBtn) {
            if (currentStep === 3) {
                nextStepBtn.innerHTML = '<i class="fas fa-check me-2"></i>完成';
                nextStepBtn.onclick = function() {
                    alert('API测试工作流程已完成！');
                };
            } else {
                nextStepBtn.innerHTML = '<i class="fas fa-arrow-right me-2"></i>下一步';
                nextStepBtn.onclick = goToNextStep;
            }
        }
    }
    
    // 文件上传功能
    function handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            processFile(file);
        }
    }
    
    function handleDragOver(event) {
        event.preventDefault();
        uploadContainer.classList.add('dragover');
    }
    
    function handleDragLeave(event) {
        event.preventDefault();
        uploadContainer.classList.remove('dragover');
    }
    
    function handleFileDrop(event) {
        event.preventDefault();
        uploadContainer.classList.remove('dragover');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            processFile(files[0]);
        }
    }
    
    function processFile(file) {
        // 显示上传中状态
        uploadContainer.classList.add('uploading');
        uploadContainer.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">正在解析文件...</p>
        `;
        
        const reader = new FileReader();
        
        reader.onload = function(e) {
            try {
                const content = e.target.result;
                
                // 根据文件类型解析内容
                if (file.name.endsWith('.json')) {
                    apiData = parseOpenApiJson(content);
                } else if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
                    apiData = parseOpenApiYaml(content);
                } else {
                    throw new Error('不支持的文件格式');
                }
                
                // 显示上传成功状态
                uploadContainer.classList.remove('uploading');
                uploadContainer.classList.add('success');
                uploadContainer.innerHTML = `
                    <div class="text-success">
                        <i class="bi bi-check-circle-fill fs-1"></i>
                        <h4>文件上传成功</h4>
                        <p>已成功解析 ${apiData.length} 个API接口</p>
                        <button class="btn btn-outline-primary mt-2" onclick="resetFileUpload()">重新上传</button>
                    </div>
                `;
                
                // 启用下一步按钮
                updateNavigationButtons();
                
            } catch (error) {
                // 显示上传失败状态
                uploadContainer.classList.remove('uploading');
                uploadContainer.classList.add('error');
                uploadContainer.innerHTML = `
                    <div class="text-danger">
                        <i class="bi bi-exclamation-triangle-fill fs-1"></i>
                        <h4>文件解析失败</h4>
                        <p>${error.message}</p>
                        <button class="btn btn-outline-danger mt-2" onclick="resetFileUpload()">重新上传</button>
                    </div>
                `;
            }
        };
        
        reader.readAsText(file);
    }
    
    function resetFileUpload() {
        uploadContainer.classList.remove('uploading', 'success', 'error');
        uploadContainer.innerHTML = `
            <i class="bi bi-cloud-upload fs-1 text-primary"></i>
            <h4>拖放API文档到此处</h4>
            <p class="text-muted">支持OpenAPI 3.0格式的JSON和YAML文件</p>
            <button class="btn btn-primary mt-2">选择文件</button>
            <input type="file" id="apiFileInput" accept=".json,.yaml,.yml" style="display: none;">
        `;
        
        // 重新绑定文件选择事件
        const newFileInput = document.getElementById('apiFileInput');
        newFileInput.addEventListener('change', handleFileSelect);
        
        // 清空API数据
        apiData = [];
        selectedApis = [];
        testCases = [];
        testResults = [];
        
        // 重置到第一步
        currentStep = 1;
        showStep(currentStep);
    }
    
    // 解析OpenAPI文档
    function parseOpenApiJson(content) {
        try {
            const openApiDoc = JSON.parse(content);
            return extractApiInfo(openApiDoc);
        } catch (error) {
            throw new Error('JSON格式错误: ' + error.message);
        }
    }
    
    function parseOpenApiYaml(content) {
        try {
            // 如果js-yaml库已加载
            if (typeof jsyaml !== 'undefined') {
                const openApiDoc = jsyaml.load(content);
                return extractApiInfo(openApiDoc);
            } else {
                throw new Error('js-yaml库未加载');
            }
        } catch (error) {
            throw new Error('YAML格式错误: ' + error.message);
        }
    }
    
    function extractApiInfo(openApiDoc) {
        const apis = [];
        
        if (!openApiDoc.paths) {
            return apis;
        }
        
        for (const [path, pathItem] of Object.entries(openApiDoc.paths)) {
            for (const [method, operation] of Object.entries(pathItem)) {
                // 跳过非HTTP方法
                if (!['get', 'post', 'put', 'delete', 'patch'].includes(method.toLowerCase())) {
                    continue;
                }
                
                const api = {
                    path: path,
                    method: method.toUpperCase(),
                    summary: operation.summary || operation.description || `${method.toUpperCase()} ${path}`,
                    description: operation.description || '',
                    parameters: operation.parameters || [],
                    requestBody: operation.requestBody || null,
                    responses: operation.responses || {},
                    tags: operation.tags || []
                };
                
                apis.push(api);
            }
        }
        
        return apis;
    }
    
    // 显示API列表
    function displayApiList() {
        if (!apiList) return;
        
        apiList.innerHTML = '';
        
        apiData.forEach((api, index) => {
            const methodClass = `method-${api.method.toLowerCase()}`;
            const isSelected = selectedApis.some(selected => selected.path === api.path && selected.method === api.method);
            
            const apiItem = document.createElement('div');
            apiItem.className = `api-item ${isSelected ? 'selected' : ''}`;
            apiItem.dataset.index = index;
            apiItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="api-method ${methodClass}">${api.method}</span>
                        <span class="api-path">${api.path}</span>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input api-checkbox" type="checkbox" 
                               data-index="${index}" ${isSelected ? 'checked' : ''}>
                    </div>
                </div>
                <div class="api-summary">${api.summary}</div>
            `;
            
            apiList.appendChild(apiItem);
        });
        
        // 绑定API选择事件
        const apiCheckboxes = apiList.querySelectorAll('.api-checkbox');
        apiCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const index = parseInt(this.dataset.index);
                const api = apiData[index];
                
                if (this.checked) {
                    // 添加到选中列表
                    if (!selectedApis.some(selected => selected.path === api.path && selected.method === api.method)) {
                        selectedApis.push(api);
                    }
                } else {
                    // 从选中列表移除
                    selectedApis = selectedApis.filter(selected => 
                        !(selected.path === api.path && selected.method === api.method)
                    );
                }
                
                // 更新UI
                const apiItem = this.closest('.api-item');
                if (this.checked) {
                    apiItem.classList.add('selected');
                } else {
                    apiItem.classList.remove('selected');
                }
                
                // 更新导航按钮状态
                updateNavigationButtons();
            });
        });
    }
    
    // 分析测试场景
    function analyzeScenarios() {
        if (!sceneListContainer) return;
        
        if (selectedApis.length === 0) {
            sceneListContainer.innerHTML = '<p class="text-muted">请先选择API接口</p>';
            return;
        }
        
        // 基于API数据生成测试场景
        const scenarios = [
            {
                name: "正常流程测试",
                description: "测试API在正常输入下的响应",
                apis: selectedApis.filter(api => !api.path.includes('/error'))
            },
            {
                name: "异常处理测试",
                description: "测试API的错误处理机制",
                apis: selectedApis.filter(api => api.method === 'POST' || api.method === 'PUT')
            },
            {
                name: "边界值测试",
                description: "测试API在边界条件下的表现",
                apis: selectedApis.filter(api => api.parameters && api.parameters.some(p => p.type === 'number'))
            },
            {
                name: "性能测试",
                description: "测试API的响应时间和并发处理能力",
                apis: selectedApis.filter(api => api.method === 'GET')
            }
        ];
        
        // 显示场景
        sceneListContainer.innerHTML = '';
        
        scenarios.forEach((scenario, index) => {
            const scenarioItem = document.createElement('div');
            scenarioItem.className = 'card mb-2';
            scenarioItem.innerHTML = `
                <div class="card-body">
                    <h6 class="card-title">${scenario.name}</h6>
                    <p class="card-text text-muted small">${scenario.description}</p>
                    <p class="card-text"><small>包含 ${scenario.apis.length} 个API</small></p>
                </div>
            `;
            
            sceneListContainer.appendChild(scenarioItem);
        });
        
        // 添加场景按钮
        const addScenarioBtn = document.createElement('button');
        addScenarioBtn.className = 'btn btn-sm btn-outline-primary mt-2';
        addScenarioBtn.innerHTML = '<i class="fas fa-plus me-1"></i>添加场景';
        addScenarioBtn.setAttribute('data-bs-toggle', 'modal');
        addScenarioBtn.setAttribute('data-bs-target', '#addScenarioModal');
        
        sceneListContainer.appendChild(addScenarioBtn);
    }
    
    // 分析API依赖关系
    function analyzeRelations() {
        if (!relationListContainer) return;
        
        if (selectedApis.length === 0) {
            relationListContainer.innerHTML = '<p class="text-muted">请先选择API接口</p>';
            return;
        }
        
        // 基于API数据生成依赖关系
        const relations = [
            {
                from: "用户登录",
                to: "获取用户信息",
                type: "数据依赖",
                description: "需要先登录获取token才能获取用户信息"
            },
            {
                from: "创建订单",
                to: "支付订单",
                type: "流程依赖",
                description: "需要先创建订单才能进行支付"
            },
            {
                from: "上传文件",
                to: "处理文件",
                type: "资源依赖",
                description: "需要先上传文件才能进行处理"
            }
        ];
        
        // 显示依赖关系
        relationListContainer.innerHTML = '';
        
        relations.forEach((relation, index) => {
            const relationItem = document.createElement('div');
            relationItem.className = 'card mb-2';
            relationItem.innerHTML = `
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title mb-1">${relation.from} → ${relation.to}</h6>
                            <p class="card-text text-muted small">${relation.description}</p>
                        </div>
                        <span class="badge bg-info">${relation.type}</span>
                    </div>
                </div>
            `;
            
            relationListContainer.appendChild(relationItem);
        });
        
        // 添加关系按钮
        const addRelationBtn = document.createElement('button');
        addRelationBtn.className = 'btn btn-sm btn-outline-primary mt-2';
        addRelationBtn.innerHTML = '<i class="fas fa-plus me-1"></i>添加关系';
        addRelationBtn.setAttribute('data-bs-toggle', 'modal');
        addRelationBtn.setAttribute('data-bs-target', '#addRelationModal');
        
        relationListContainer.appendChild(addRelationBtn);
    }
    
    // 生成测试用例
    function generateTestCases() {
        if (selectedApis.length === 0) {
            alert('请先选择API接口');
            return;
        }
        
        // 显示加载状态
        generateTestCasesBtn.disabled = true;
        generateTestCasesBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            生成中...
        `;
        
        // 模拟异步生成测试用例
        setTimeout(() => {
            testCases = [];
            
            selectedApis.forEach(api => {
                // 为每个API生成多种测试用例
                const basicCase = {
                    id: `basic-${api.method}-${api.path.replace(/\//g, '-')}`,
                    title: `${api.method} ${api.path} - 基本测试`,
                    description: '验证API基本功能',
                    api: api,
                    type: 'basic',
                    status: 'pending',
                    request: {
                        method: api.method,
                        url: `${API_CONFIG.baseURL}${api.path}`,
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        // 简化的请求体
                        body: api.method !== 'GET' ? {} : undefined
                    },
                    expectedResponse: {
                        status: 200,
                        body: {}
                    }
                };
                
                const boundaryCase = {
                    id: `boundary-${api.method}-${api.path.replace(/\//g, '-')}`,
                    title: `${api.method} ${api.path} - 边界测试`,
                    description: '验证API边界条件处理',
                    api: api,
                    type: 'boundary',
                    status: 'pending',
                    request: {
                        method: api.method,
                        url: `${API_CONFIG.baseURL}${api.path}`,
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        // 边界测试请求体
                        body: api.method !== 'GET' ? { size: 10000 } : undefined
                    },
                    expectedResponse: {
                        status: api.method === 'POST' ? 201 : 200,
                        body: {}
                    }
                };
                
                testCases.push(basicCase, boundaryCase);
            });
            
            // 恢复按钮状态
            generateTestCasesBtn.disabled = false;
            generateTestCasesBtn.innerHTML = '生成测试用例';
            
            // 显示成功消息
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success alert-dismissible fade show';
            alertDiv.innerHTML = `
                成功生成 ${testCases.length} 个测试用例！
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            const container = document.getElementById('step3');
            container.insertBefore(alertDiv, container.firstChild);
            
            // 3秒后自动关闭提示
            setTimeout(() => {
                alertDiv.remove();
            }, 3000);
            
            // 更新导航按钮状态
            updateNavigationButtons();
            
            // 显示测试用例
            displayTestCases();
            
        }, 1500);
    }
    
    // 显示测试用例
    function displayTestCases() {
        if (!testCasesList) return;
        
        if (testCases.length === 0) {
            testCasesList.innerHTML = '<p class="text-muted">没有测试用例，请先生成测试用例</p>';
            return;
        }
        
        let html = '';
        
        testCases.forEach(testCase => {
            const statusClass = `status-${testCase.status}`;
            const typeClass = `type-${testCase.type}`;
            
            html += `
                <div class="test-case-card ${testCase.status}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="test-case-title">${testCase.title}</div>
                            <div class="test-case-description">${testCase.description}</div>
                            <div class="test-case-api">
                                <span class="api-method method-${testCase.api.method.toLowerCase()}">${testCase.api.method}</span>
                                <span class="api-path">${testCase.api.path}</span>
                            </div>
                            <div class="mt-2">
                                <span class="tag ${typeClass}">${getTypeLabel(testCase.type)}</span>
                                <span class="test-case-status ${statusClass}">${getStatusLabel(testCase.status)}</span>
                            </div>
                        </div>
                        <div class="test-case-actions">
                            <button class="btn btn-sm btn-outline-primary view-test-case" data-id="${testCase.id}">
                                查看详情
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        testCasesList.innerHTML = html;
        
        // 绑定查看详情事件
        const viewButtons = document.querySelectorAll('.view-test-case');
        viewButtons.forEach(button => {
            button.addEventListener('click', function() {
                const testCaseId = this.dataset.id;
                const testCase = testCases.find(tc => tc.id === testCaseId);
                if (testCase) {
                    showTestCaseDetails(testCase);
                }
            });
        });
    }
    
    // 显示测试用例详情
    function showTestCaseDetails(testCase) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${testCase.title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <h6>描述</h6>
                            <p>${testCase.description}</p>
                        </div>
                        
                        <div class="mb-3">
                            <h6>请求</h6>
                            <div class="code-container">${JSON.stringify(testCase.request, null, 2)}</div>
                        </div>
                        
                        <div class="mb-3">
                            <h6>期望响应</h6>
                            <div class="code-container">${JSON.stringify(testCase.expectedResponse, null, 2)}</div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-primary run-single-test" data-id="${testCase.id}">运行测试</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // 绑定运行单个测试事件
        const runSingleTestBtn = modal.querySelector('.run-single-test');
        runSingleTestBtn.addEventListener('click', function() {
            const testCaseId = this.dataset.id;
            bsModal.hide();
            runSingleTest(testCaseId);
        });
        
        // 模态框关闭时移除DOM
        modal.addEventListener('hidden.bs.modal', function() {
            document.body.removeChild(modal);
        });
    }
    
    // 运行测试
    function runTests() {
        if (testCases.length === 0) {
            alert('没有可运行的测试用例');
            return;
        }
        
        // 显示加载状态
        runTestsBtn.disabled = true;
        runTestsBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            运行中...
        `;
        
        // 重置测试结果
        testResults = [];
        
        // 模拟异步运行测试
        setTimeout(() => {
            testCases.forEach(testCase => {
                // 随机生成测试结果
                const isSuccess = Math.random() > 0.3; // 70%成功率
                
                const result = {
                    testCaseId: testCase.id,
                    testCaseTitle: testCase.title,
                    status: isSuccess ? 'passed' : 'failed',
                    duration: Math.floor(Math.random() * 1000) + 100, // 100-1100ms
                    request: testCase.request,
                    response: {
                        status: isSuccess ? testCase.expectedResponse.status : (Math.random() > 0.5 ? 400 : 500),
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: isSuccess ? 
                            testCase.expectedResponse.body : 
                            { error: '模拟错误响应' }
                    },
                    error: isSuccess ? null : '模拟测试失败'
                };
                
                testResults.push(result);
                
                // 更新测试用例状态
                testCase.status = result.status;
            });
            
            // 恢复按钮状态
            runTestsBtn.disabled = false;
            runTestsBtn.innerHTML = '运行测试';
            
            // 显示测试结果
            displayTestResults();
            
            // 更新测试用例显示
            displayTestCases();
            
            // 跳转到测试结果步骤
            currentStep = 4;
            showStep(currentStep);
            
        }, 2000);
    }
    
    // 运行单个测试
    function runSingleTest(testCaseId) {
        const testCase = testCases.find(tc => tc.id === testCaseId);
        if (!testCase) return;
        
        // 显示加载状态
        showLoadingOverlay('正在运行测试...');
        
        // 模拟异步运行测试
        setTimeout(() => {
            // 随机生成测试结果
            const isSuccess = Math.random() > 0.3; // 70%成功率
            
            const result = {
                testCaseId: testCase.id,
                testCaseTitle: testCase.title,
                status: isSuccess ? 'passed' : 'failed',
                duration: Math.floor(Math.random() * 1000) + 100, // 100-1100ms
                request: testCase.request,
                response: {
                    status: isSuccess ? testCase.expectedResponse.status : (Math.random() > 0.5 ? 400 : 500),
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: isSuccess ? 
                        testCase.expectedResponse.body : 
                        { error: '模拟错误响应' }
                },
                error: isSuccess ? null : '模拟测试失败'
            };
            
            // 更新或添加测试结果
            const existingIndex = testResults.findIndex(r => r.testCaseId === testCaseId);
            if (existingIndex >= 0) {
                testResults[existingIndex] = result;
            } else {
                testResults.push(result);
            }
            
            // 更新测试用例状态
            testCase.status = result.status;
            
            // 隐藏加载状态
            hideLoadingOverlay();
            
            // 显示测试结果详情
            showTestResultDetails(result);
            
            // 更新测试用例显示
            displayTestCases();
            
        }, 1500);
    }
    
    // 显示测试结果
    function displayTestResults() {
        if (testResults.length === 0) {
            testResultContainer.innerHTML = '<p class="text-muted">没有测试结果</p>';
            return;
        }
        
        // 计算统计信息
        const totalTests = testResults.length;
        const passedTests = testResults.filter(r => r.status === 'passed').length;
        const failedTests = testResults.filter(r => r.status === 'failed').length;
        const passRate = ((passedTests / totalTests) * 100).toFixed(1);
        
        let html = `
            <div class="test-result-header">
                <h5>测试结果概览</h5>
                <div>
                    <span class="badge bg-success me-1">通过: ${passedTests}</span>
                    <span class="badge bg-danger me-1">失败: ${failedTests}</span>
                    <span class="badge bg-primary">总计: ${totalTests}</span>
                    <span class="badge bg-info">通过率: ${passRate}%</span>
                </div>
            </div>
        `;
        
        // 添加测试结果列表
        testResults.forEach(result => {
            const statusClass = result.status === 'passed' ? 'success' : 'danger';
            const statusText = result.status === 'passed' ? '通过' : '失败';
            
            html += `
                <div class="test-result-card mb-3">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">${result.testCaseTitle}</h6>
                            <span class="badge bg-${statusClass}">${statusText}</span>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="test-result-request">
                                        <div class="test-result-title">请求</div>
                                        <div class="test-result-code">${JSON.stringify(result.request, null, 2)}</div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="test-result-response">
                                        <div class="test-result-title">响应</div>
                                        <div class="test-result-code">${JSON.stringify(result.response, null, 2)}</div>
                                    </div>
                                </div>
                            </div>
                            ${result.error ? `
                                <div class="mt-3">
                                    <div class="test-result-title">错误信息</div>
                                    <div class="alert alert-danger">${result.error}</div>
                                </div>
                            ` : ''}
                            <div class="mt-2 text-muted">
                                执行时间: ${result.duration}ms
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        testResultContainer.innerHTML = html;
    }
    
    // 显示测试结果详情
    function showTestResultDetails(result) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${result.testCaseTitle} - 测试结果</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <span class="badge bg-${result.status === 'passed' ? 'success' : 'danger'} me-2">
                                ${result.status === 'passed' ? '通过' : '失败'}
                            </span>
                            <span class="text-muted">执行时间: ${result.duration}ms</span>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <h6>请求</h6>
                                    <div class="code-container">${JSON.stringify(result.request, null, 2)}</div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <h6>响应</h6>
                                    <div class="code-container">${JSON.stringify(result.response, null, 2)}</div>
                                </div>
                            </div>
                        </div>
                        
                        ${result.error ? `
                            <div class="mb-3">
                                <h6>错误信息</h6>
                                <div class="alert alert-danger">${result.error}</div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-primary re-run-test" data-id="${result.testCaseId}">重新运行</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // 绑定重新运行测试事件
        const reRunTestBtn = modal.querySelector('.re-run-test');
        reRunTestBtn.addEventListener('click', function() {
            const testCaseId = this.dataset.id;
            bsModal.hide();
            runSingleTest(testCaseId);
        });
        
        // 模态框关闭时移除DOM
        modal.addEventListener('hidden.bs.modal', function() {
            document.body.removeChild(modal);
        });
    }
    
    // 辅助函数
    function getTypeLabel(type) {
        const labels = {
            'basic': '基本测试',
            'scenario': '场景测试',
            'boundary': '边界测试',
            'exception': '异常测试'
        };
        return labels[type] || type;
    }
    
    function getStatusLabel(status) {
        const labels = {
            'pending': '待运行',
            'running': '运行中',
            'passed': '通过',
            'failed': '失败',
            'skipped': '跳过'
        };
        return labels[status] || status;
    }
    
    function showLoadingOverlay(message = '加载中...') {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5>${message}</h5>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    
    function hideLoadingOverlay() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            document.body.removeChild(overlay);
        }
    }
});