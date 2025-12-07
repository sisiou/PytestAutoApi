// 文档上传页面JavaScript

// 全局变量
let uploadedFiles = [];
let currentFile = null;
let parsedApiData = null;

// 初始化函数
document.addEventListener('DOMContentLoaded', function() {
    console.log('文档上传页面初始化');
    
    // 初始化事件监听器
    initEventListeners();
    
    // 加载已上传的文件列表
    loadUploadedFiles();
});

// 初始化事件监听器
function initEventListeners() {
    const uploadContainer = document.getElementById('uploadContainer');
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const backToUploadBtn = document.getElementById('backToUploadBtn');
    const generateTestsBtn = document.getElementById('generateTestsBtn');
    
    // 新增：直接输入OpenAPI文档相关元素
    const apiTextInput = document.getElementById('apiTextInput');
    const clearTextBtn = document.getElementById('clearTextBtn');
    const parseTextBtn = document.getElementById('parseTextBtn');
    const apiUrlInput = document.getElementById('apiUrlInput');
    const fetchUrlBtn = document.getElementById('fetchUrlBtn');
    
    // 点击选择文件按钮
    if (selectFileBtn) {
        selectFileBtn.addEventListener('click', function() {
            fileInput.click();
        });
    }
    
    // 点击上传区域
    if (uploadContainer) {
        uploadContainer.addEventListener('click', function() {
            fileInput.click();
        });
    }
    
    // 文件选择变化
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
            }
        });
    }
    
    // 新增：清空文本输入
    if (clearTextBtn) {
        clearTextBtn.addEventListener('click', function() {
            if (apiTextInput) {
                apiTextInput.value = '';
            }
        });
    }
    
    // 新增：解析文本输入的API文档
    if (parseTextBtn) {
        parseTextBtn.addEventListener('click', function() {
            if (apiTextInput && apiTextInput.value.trim()) {
                handleTextInput(apiTextInput.value.trim());
            } else {
                Notification.warning('请输入OpenAPI 3.0.0文档内容');
            }
        });
    }
    
    // 新增：从URL获取API文档
    if (fetchUrlBtn) {
        fetchUrlBtn.addEventListener('click', function() {
            if (apiUrlInput && apiUrlInput.value.trim()) {
                handleUrlInput(apiUrlInput.value.trim());
            } else {
                Notification.warning('请输入有效的API文档URL');
            }
        });
    }
    
    // 拖拽事件
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
    
    // 返回上传按钮
    if (backToUploadBtn) {
        backToUploadBtn.addEventListener('click', function() {
            showUploadSection();
        });
    }
    
    // 生成测试用例按钮
    if (generateTestsBtn) {
        generateTestsBtn.addEventListener('click', function() {
            generateTestCases();
        });
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
        Notification.error('不支持的文件类型，请上传 OpenAPI 3.0.0 JSON 或 YAML 格式的文件');
        return;
    }
    
    // 验证文件大小 (10MB)
    if (file.size > 10 * 1024 * 1024) {
        Notification.error('文件大小不能超过 10MB');
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
            
            // 刷新API列表
function refreshApiList() {
    console.log('刷新API列表');
    
    // 发送请求到后端获取最新的API列表
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
        console.log('API列表刷新成功:', data);
        
        if (data.success) {
            // 更新API列表显示
            updateApiListDisplay(data.apis);
        } else {
            Notification.error('刷新API列表失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('刷新API列表失败:', error);
        Notification.error('刷新API列表时发生错误');
    });
}
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
    
    Notification.error(message);
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
    showProcessingStatus();
    
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.PARSE) + `/${fileId}`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('解析文档失败');
        }
        return response.json();
    })
    .then(data => {
        console.log('文档解析结果:', data);
        
        if (!data.success) {
            throw new Error(data.message || '文档解析失败');
        }
        
        // 保存解析结果
        parsedApiData = data;
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示解析结果
        showParseResults(data);
        
        Notification.success('文档解析成功');
    })
    .catch(error => {
        console.error('解析文档失败:', error);
        hideProcessingStatus();
        Notification.error(error.message);
    });
}

// 显示解析结果
function showParseResults(data) {
    // 隐藏上传区域
    const uploadContainer = document.getElementById('uploadContainer').parentElement.parentElement;
    uploadContainer.style.display = 'none';
    
    // 显示结果区域
    const resultContainer = document.getElementById('resultContainer');
    resultContainer.style.display = 'block';
    
    // 更新API摘要
    updateApiSummary(data);
    
    // 更新API端点
    updateApiEndpoints(data.endpoints || []);
    
    // 更新数据模型
    updateApiModels(data.models || {});
}

// 更新API摘要
function updateApiSummary(data) {
    const apiSummary = document.getElementById('apiSummary');
    
    if (!apiSummary) return;
    
    apiSummary.innerHTML = `
        <div class="row">
            <div class="col-md-3">
                <div class="text-center">
                    <h3>${data.info?.title || 'API文档'}</h3>
                    <p class="text-muted">${data.info?.version || '未知版本'}</p>
                </div>
            </div>
            <div class="col-md-9">
                <p>${data.info?.description || '无描述'}</p>
                <div class="row mt-3">
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>${data.endpoints?.length || 0}</h5>
                            <p class="text-muted">API端点</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>${Object.keys(data.models || {}).length}</h5>
                            <p class="text-muted">数据模型</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>${getEndpointCountByMethod(data.endpoints || [], 'GET')}</h5>
                            <p class="text-muted">GET请求</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>${getEndpointCountByMethod(data.endpoints || [], 'POST')}</h5>
                            <p class="text-muted">POST请求</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 更新API端点
function updateApiEndpoints(endpoints) {
    const apiEndpoints = document.getElementById('apiEndpoints');
    
    if (!apiEndpoints) return;
    
    if (endpoints.length === 0) {
        apiEndpoints.innerHTML = '<p class="text-muted">无API端点</p>';
        return;
    }
    
    const endpointsHtml = endpoints.map(endpoint => {
        const methodClass = `method-${endpoint.method.toLowerCase()}`;
        return `
            <div class="mb-2">
                <span class="method-badge ${methodClass}">${endpoint.method}</span>
                <span class="api-endpoint">${endpoint.path}</span>
                <div class="text-muted small">${endpoint.summary || '无描述'}</div>
            </div>
        `;
    }).join('');
    
    apiEndpoints.innerHTML = endpointsHtml;
}

// 更新数据模型
function updateApiModels(models) {
    const apiModels = document.getElementById('apiModels');
    
    if (!apiModels) return;
    
    const modelNames = Object.keys(models);
    
    if (modelNames.length === 0) {
        apiModels.innerHTML = '<p class="text-muted">无数据模型</p>';
        return;
    }
    
    const modelsHtml = modelNames.map(name => {
        return `
            <div class="mb-2">
                <div class="fw-bold">${name}</div>
                <div class="text-muted small">${models[name].description || '无描述'}</div>
            </div>
        `;
    }).join('');
    
    apiModels.innerHTML = modelsHtml;
}

// 获取指定方法的端点数量
function getEndpointCountByMethod(endpoints, method) {
    return endpoints.filter(endpoint => endpoint.method === method).length;
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
    const fileListSection = document.getElementById('fileListSection');
    const fileList = document.getElementById('fileList');
    
    if (!fileList || !fileListSection) return;
    
    if (uploadedFiles.length === 0) {
        fileListSection.style.display = 'none';
        return;
    }
    
    fileListSection.style.display = 'block';
    
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
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('${file.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        // 添加测试按钮
        addTestButtons(fileItem, file.id);
        
        fileList.appendChild(fileItem);
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

// 显示上传区域
function showUploadSection() {
    const uploadContainer = document.getElementById('uploadContainer').parentElement.parentElement;
    const resultContainer = document.getElementById('resultContainer');
    
    if (uploadContainer) {
        uploadContainer.style.display = 'block';
    }
    
    if (resultContainer) {
        resultContainer.style.display = 'none';
    }
}

// 生成测试用例
async function generateTestCases(fileId) {
    try {
        showProcessingStatus();
        
        const response = await fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.GENERATE_TEST_CASES) + `/${fileId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('生成测试用例失败');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || '生成测试用例失败');
        }
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示成功消息
        Notification.success('测试用例生成成功');
        
        // 跳转到测试用例页面
        window.location.href = 'test-cases.html';
        
    } catch (error) {
        console.error('生成测试用例失败:', error);
        hideProcessingStatus();
        Notification.error(error.message);
    }
}

// 执行测试
async function executeTests(fileId) {
    try {
        showProcessingStatus();
        
        const response = await fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.EXECUTE_TESTS) + `/${fileId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('执行测试失败');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || '执行测试失败');
        }
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示成功消息
        Notification.success('测试执行成功');
        
        // 跳转到测试结果页面
        window.location.href = 'test-results.html';
        
    } catch (error) {
        console.error('执行测试失败:', error);
        hideProcessingStatus();
        Notification.error(error.message);
    }
}

// 分析结果
async function analyzeResults(fileId) {
    try {
        showProcessingStatus();
        
        const response = await fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.ANALYZE_RESULTS) + `/${fileId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('分析结果失败');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || '分析结果失败');
        }
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示成功消息
        Notification.success('结果分析成功');
        
        // 跳转到分析结果页面
        window.location.href = 'analysis-results.html';
        
    } catch (error) {
        console.error('分析结果失败:', error);
        hideProcessingStatus();
        Notification.error(error.message);
    }
}

// 执行测试结果
async function analyzeTestResults(fileId) {
    try {
        showProcessingStatus();
        
        const response = await fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.ANALYZE_RESULTS) + `/${fileId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('分析测试结果失败');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || '分析测试结果失败');
        }
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示成功消息
        Notification.success('测试结果分析成功');
        
        // 跳转到分析结果页面
        window.location.href = 'analysis-results.html';
        
    } catch (error) {
        console.error('分析测试结果失败:', error);
        hideProcessingStatus();
        Notification.error(error.message);
    }
}

// 执行完整工作流程
async function executeFullWorkflow(fileId) {
    try {
        showProcessingStatus();
        
        const response = await fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.FULL_WORKFLOW) + `/${fileId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('执行完整工作流程失败');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || '执行完整工作流程失败');
        }
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示成功消息
        Notification.success('完整工作流程执行成功');
        
        // 跳转到测试结果页面
        window.location.href = 'test-results.html';
        
    } catch (error) {
        console.error('执行完整工作流程失败:', error);
        hideProcessingStatus();
        Notification.error(error.message);
    }
}

// 查看文件详情
function viewFileDetails(fileId) {
    // 跳转到测试中心页面
    window.location.href = `test-center.html?fileId=${fileId}`;
}

// 添加测试按钮到文件列表
function addTestButtons(fileItem, fileId) {
    // 创建测试按钮容器
    const testButtonsContainer = document.createElement('div');
    testButtonsContainer.className = 'mt-2 d-flex flex-wrap gap-1';
    
    // 生成测试用例按钮
    const generateBtn = document.createElement('button');
    generateBtn.className = 'btn btn-sm btn-outline-primary';
    generateBtn.innerHTML = '<i class="fas fa-vial me-1"></i>生成测试用例';
    generateBtn.onclick = () => generateTestCases(fileId);
    
    // 执行测试按钮
    const executeBtn = document.createElement('button');
    executeBtn.className = 'btn btn-sm btn-outline-success';
    executeBtn.innerHTML = '<i class="fas fa-play me-1"></i>执行测试';
    executeBtn.onclick = () => executeTests(fileId);
    
    // 分析结果按钮
    const analyzeBtn = document.createElement('button');
    analyzeBtn.className = 'btn btn-sm btn-outline-info';
    analyzeBtn.innerHTML = '<i class="fas fa-chart-bar me-1"></i>分析结果';
    analyzeBtn.onclick = () => analyzeTestResults(fileId);
    
    // 完整工作流程按钮
    const workflowBtn = document.createElement('button');
    workflowBtn.className = 'btn btn-sm btn-outline-warning';
    workflowBtn.innerHTML = '<i class="fas fa-magic me-1"></i>完整流程';
    workflowBtn.onclick = () => executeFullWorkflow(fileId);
    
    // 添加按钮到容器
    testButtonsContainer.appendChild(generateBtn);
    testButtonsContainer.appendChild(executeBtn);
    testButtonsContainer.appendChild(analyzeBtn);
    testButtonsContainer.appendChild(workflowBtn);
    
    // 将按钮容器添加到文件项
    fileItem.appendChild(testButtonsContainer);
}

// 删除文件
function deleteFile(fileId) {
    if (!confirm('确定要删除这个文件吗？')) {
        return;
    }
    
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.DELETE) + `/${fileId}`, {
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
        
        Notification.success('文件删除成功');
    })
    .catch(error => {
        console.error('删除失败:', error);
        Notification.error(error.message);
    });
}

// 加载已上传的文件列表
function loadUploadedFiles() {
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.UPLOADED_LIST), {
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
        
        if (data && data.documents && data.documents.length > 0) {
            // 将后端返回的文档格式转换为前端期望的格式
            uploadedFiles = data.documents.map(doc => ({
                id: doc.file_id,
                name: doc.filename,
                size: doc.size,
                uploadTime: doc.upload_time,
                status: doc.status
            }));
            updateFileListDisplay();
        }
    })
    .catch(error => {
        console.error('加载文件列表失败:', error);
    });
}

// 生成测试用例
function generateTestCases() {
    if (!parsedApiData) {
        Notification.error('没有可用的API数据');
        return;
    }
    
    // 保存解析结果到本地存储
    localStorage.setItem('parsedApiData', JSON.stringify(parsedApiData));
    
    // 跳转到测试用例页面
    window.location.href = 'test-cases.html?source=upload';
}

// 新增：处理文本输入的OpenAPI文档
function handleTextInput(textContent) {
    console.log('处理文本输入的OpenAPI文档');
    
    try {
        // 显示处理状态
        showProcessingStatus();
        
        // 尝试解析为JSON或YAML
        let apiDoc;
        try {
            // 先尝试解析为JSON
            apiDoc = JSON.parse(textContent);
        } catch (jsonError) {
            // JSON解析失败，尝试解析为YAML
            try {
                if (typeof jsyaml !== 'undefined') {
                    apiDoc = jsyaml.load(textContent);
                } else if (typeof YAML !== 'undefined') {
                    apiDoc = YAML.parse(textContent);
                } else {
                    throw new Error('YAML解析库未加载');
                }
            } catch (yamlError) {
                throw new Error('文档格式错误：无法解析为有效的JSON或YAML格式');
            }
        }
        
        // 验证OpenAPI版本
        if (!apiDoc.openapi || !apiDoc.openapi.startsWith('3.0.')) {
            throw new Error('仅支持OpenAPI 3.0.x版本的文档');
        }
        
        // 模拟文件上传响应
        const mockFileData = {
            success: true,
            file_id: 'text_input_' + Date.now(),
            filename: '直接输入的API文档',
            message: '文档解析成功'
        };
        
        // 延迟一下，让用户看到处理状态
        setTimeout(() => {
            hideProcessingStatus();
            
            // 保存解析结果
            parsedApiData = apiDoc;
            
            // 显示解析结果
            showParseResults(apiDoc);
            
            // 通知成功
            Notification.success('OpenAPI文档解析成功');
            
            // 显示文本解析结果
            const textParseResult = document.getElementById('textParseResult');
            if (textParseResult) {
                textParseResult.innerHTML = `
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        成功解析OpenAPI 3.0.0文档：${apiDoc.info?.title || '未知API'}
                    </div>
                `;
                
                // 3秒后清除提示
                setTimeout(() => {
                    textParseResult.innerHTML = '';
                }, 3000);
            }
        }, 1000);
        
    } catch (error) {
        console.error('解析文本输入失败:', error);
        hideProcessingStatus();
        
        // 显示错误信息
        const textParseResult = document.getElementById('textParseResult');
        if (textParseResult) {
            textParseResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${error.message}
                </div>
            `;
        }
        
        Notification.error(error.message);
    }
}

// 新增：处理URL输入的OpenAPI文档
function handleUrlInput(url) {
    console.log('从URL获取OpenAPI文档:', url);
    
    // 验证URL格式
    try {
        new URL(url);
    } catch (e) {
        Notification.error('请输入有效的URL地址');
        return;
    }
    
    // 检查是否是飞书开放平台文档URL
    if (url.includes('open.feishu.cn/document/')) {
        handleFeishuUrl(url);
        return;
    }
    
    // 显示处理状态
    showProcessingStatus();
    
    // 显示URL获取结果
    const urlFetchResult = document.getElementById('urlFetchResult');
    if (urlFetchResult) {
        urlFetchResult.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-spinner fa-spin me-2"></i>
                正在从URL获取API文档...
            </div>
        `;
    }
    
    // 从URL获取文档
    fetch(url)
    .then(response => {
        if (!response.ok) {
            throw new Error(`获取文档失败: ${response.status} ${response.statusText}`);
        }
        
        // 检查Content-Type，如果是JSON或YAML，直接处理
        const contentType = response.headers.get('Content-Type') || '';
        if (contentType.includes('application/json') || 
            contentType.includes('application/yaml') || 
            contentType.includes('application/x-yaml') ||
            contentType.includes('text/yaml') ||
            contentType.includes('text/x-yaml')) {
            // 如果是直接指向OpenAPI文档的URL，直接返回文本内容
            return response.text();
        } else {
            // 如果是HTML页面，尝试从中提取OpenAPI文档
            return response.text().then(html => {
                // 尝试从HTML中提取JSON或YAML内容
                const jsonMatch = html.match(/<script[^>]*type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/i);
                if (jsonMatch) {
                    return jsonMatch[1];
                }
                
                const yamlMatch = html.match(/<pre[^>]*class=["']language-yaml["'][^>]*>([\s\S]*?)<\/pre>/i) ||
                                 html.match(/<code[^>]*class=["']language-yaml["'][^>]*>([\s\S]*?)<\/code>/i);
                if (yamlMatch) {
                    return yamlMatch[1];
                }
                
                // 如果没有找到嵌入的OpenAPI文档，返回整个HTML文本
                // 让后续解析逻辑处理
                return html;
            });
        }
    })
    .then(textContent => {
        // 尝试解析为JSON或YAML
        let apiDoc;
        try {
            // 先尝试解析为JSON
            apiDoc = JSON.parse(textContent);
        } catch (jsonError) {
            // JSON解析失败，尝试解析为YAML
            try {
                if (typeof jsyaml !== 'undefined') {
                    apiDoc = jsyaml.load(textContent);
                } else if (typeof YAML !== 'undefined') {
                    apiDoc = YAML.parse(textContent);
                } else {
                    throw new Error('YAML解析库未加载');
                }
            } catch (yamlError) {
                throw new Error('文档格式错误：无法解析为有效的JSON或YAML格式');
            }
        }
        
        // 验证OpenAPI版本
        if (!apiDoc.openapi || !apiDoc.openapi.startsWith('3.0.')) {
            throw new Error('仅支持OpenAPI 3.0.x版本的文档');
        }
        
        // 模拟文件上传响应
        const mockFileData = {
            success: true,
            file_id: 'url_input_' + Date.now(),
            filename: '从URL获取的API文档',
            message: '文档解析成功'
        };
        
        // 保存解析结果
        parsedApiData = apiDoc;
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示解析结果
        showParseResults(apiDoc);
        
        // 通知成功
        Notification.success('从URL获取并解析OpenAPI文档成功');
        
        // 显示URL获取结果
        if (urlFetchResult) {
            urlFetchResult.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    成功获取并解析OpenAPI 3.0.0文档：${apiDoc.info?.title || '未知API'}
                </div>
            `;
            
            // 3秒后清除提示
            setTimeout(() => {
                urlFetchResult.innerHTML = '';
            }, 3000);
        }
    })
    .catch(error => {
        console.error('从URL获取文档失败:', error);
        hideProcessingStatus();
        
        // 显示错误信息
        if (urlFetchResult) {
            urlFetchResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${error.message}
                </div>
            `;
        }
        
        Notification.error(error.message);
    });
}

// 新增：处理飞书开放平台文档URL
function handleFeishuUrl(url) {
    console.log('处理飞书开放平台文档URL:', url);
    
    // 显示处理状态
    showProcessingStatus();
    
    // 显示URL获取结果
    const urlFetchResult = document.getElementById('urlFetchResult');
    if (urlFetchResult) {
        urlFetchResult.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-spinner fa-spin me-2"></i>
                正在获取飞书开放平台API文档...
            </div>
        `;
    }
    
    // 调用后端API处理飞书URL
    fetch(ApiConfig.buildUrl(ApiConfig.API_CONFIG.ENDPOINTS.DOCS.FETCH_FEISHU), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`获取飞书文档失败: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('飞书文档获取成功:', data);
        
        if (!data.success) {
            throw new Error(data.message || '获取飞书文档失败');
        }
        
        // 直接使用后端返回的OpenAPI格式数据
        const apiDoc = data.openapi_data || data.apiDoc;
        
        // 验证OpenAPI版本
        if (!apiDoc.openapi || !apiDoc.openapi.startsWith('3.0.')) {
            throw new Error('后端返回的不是有效的OpenAPI 3.0.x格式文档');
        }
        
        // 保存解析结果
        parsedApiData = apiDoc;
        
        // 隐藏处理状态
        hideProcessingStatus();
        
        // 显示解析结果
        showParseResults(apiDoc);
        
        // 处理关联关系数据
        if (data.relation_data && data.relation_data.relation_info) {
            console.log('接口关联关系生成成功:', data.relation_data);
            // 可以在这里添加处理关联关系的UI逻辑
            Notification.success('接口关联关系生成成功');
        }
        
        // 处理业务场景数据
        if (data.scene_data && data.scene_data.business_scenes) {
            console.log('业务场景生成成功:', data.scene_data);
            // 可以在这里添加处理业务场景的UI逻辑
            Notification.success('业务场景生成成功');
        }
        
        // 通知成功
        Notification.success('成功获取并解析飞书开放平台API文档');
        
        // 显示URL获取结果
        if (urlFetchResult) {
            let resultMessage = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    成功获取并解析飞书开放平台API文档：${apiDoc.info?.title || '未知API'}
            `;
            
            // 添加关联关系和业务场景的生成状态
            if (data.relation_data && data.relation_data.relation_info) {
                resultMessage += `<br><small class="text-success">✓ 接口关联关系已生成</small>`;
            }
            
            if (data.scene_data && data.scene_data.business_scenes) {
                resultMessage += `<br><small class="text-success">✓ 业务场景已生成</small>`;
            }
            
            resultMessage += '</div>';
            
            urlFetchResult.innerHTML = resultMessage;
            
            // 5秒后清除提示
            setTimeout(() => {
                urlFetchResult.innerHTML = '';
            }, 5000);
        }
    })
    .catch(error => {
        console.error('从飞书URL获取文档失败:', error);
        hideProcessingStatus();
        
        // 显示错误信息
        if (urlFetchResult) {
            urlFetchResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${error.message}
                </div>
            `;
        }
        
        Notification.error(error.message);
    });
}