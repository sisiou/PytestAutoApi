// 智能测试生成页面的JavaScript逻辑

// 全局变量
let currentStep = 1;
let apiDocData = null;
let apiEndpoints = [];
let scenes = [];
let relations = [];
let testCases = [];

// 页面初始化函数
function initSmartTestGenerationPage() {
    initEventListeners();
    initDragAndDrop();
    // 确保第一步处于活动状态
    updateStepIndicator(1);
    console.log('智能测试生成页面初始化完成');
}

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 只有在当前页面是智能测试生成页面时才初始化
    // 并且确保初始化函数只被调用一次
    if (window.location.pathname.includes('smart-test-generation.html') && typeof initSmartTestGenerationPage === 'function') {
        // 延迟初始化，确保DOM完全加载
        setTimeout(initSmartTestGenerationPage, 100);
    }
});

// 初始化事件监听器
function initEventListeners() {
    // 文件上传相关
    document.getElementById('uploadBtn').addEventListener('click', function() {
        document.getElementById('fileInput').click();
    });
    
    document.getElementById('fileInput').addEventListener('change', handleFileSelect);
    
    // URL导入相关
    document.getElementById('fetchUrlBtn').addEventListener('click', fetchApiFromUrl);
    
    // 文本输入相关
    document.getElementById('parseTextBtn').addEventListener('click', parseApiText);
    document.getElementById('clearTextBtn').addEventListener('click', clearApiText);
    
    // 步骤导航
    document.getElementById('analyzeBtn').addEventListener('click', moveToStep2);
    document.getElementById('generateBtn').addEventListener('click', moveToStep3);
    document.getElementById('backToStep1Btn').addEventListener('click', moveToStep1);
    document.getElementById('backToStep2Btn').addEventListener('click', moveToStep2);
    
    // 添加场景和关联
    document.getElementById('addSceneBtn').addEventListener('click', showAddSceneModal);
    document.getElementById('addRelationBtn').addEventListener('click', showAddRelationModal);
    
    // 保存场景和关联
    document.getElementById('saveSceneBtn').addEventListener('click', saveCustomScene);
    document.getElementById('saveRelationBtn').addEventListener('click', saveCustomRelation);
    
    // 测试用例相关
    document.getElementById('searchCases').addEventListener('input', filterTestCases);
    document.getElementById('exportBtn').addEventListener('click', exportTestCases);
    document.getElementById('runTestsBtn').addEventListener('click', runAllTests);
    document.getElementById('runSingleTestBtn').addEventListener('click', runSingleTest);
    
    // 重置和保存
    document.getElementById('resetBtn').addEventListener('click', resetAll);
    document.getElementById('saveBtn').addEventListener('click', saveConfiguration);
    document.getElementById('finishBtn').addEventListener('click', finishProcess);
}

// 初始化拖拽上传
function initDragAndDrop() {
    const uploadContainer = document.getElementById('uploadContainer');
    
    uploadContainer.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadContainer.classList.add('dragover');
    });
    
    uploadContainer.addEventListener('dragleave', function() {
        uploadContainer.classList.remove('dragover');
    });
    
    uploadContainer.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadContainer.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
}

// 处理文件选择
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

// 处理文件
async function handleFile(file) {
    const validTypes = ['application/json', 'text/yaml', 'application/x-yaml', 'text/plain'];
    const validExtensions = ['.json', '.yaml', '.yml'];
    
    // 验证文件类型
    const isValidType = validTypes.includes(file.type) || 
                       validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    
    if (!isValidType) {
        showAlert('请上传有效的OpenAPI文档（JSON或YAML格式）', 'danger');
        return;
    }
    
    // 显示上传进度
    showUploadProgress();
    
    try {
        const content = await readFileContent(file);
        const isYaml = file.name.toLowerCase().endsWith('.yaml') || file.name.toLowerCase().endsWith('.yml');
        
        console.log('文件类型:', isYaml ? 'YAML' : 'JSON');
        console.log('文件内容前100字符:', content.substring(0, 100));
        
        // 解析API文档
        if (isYaml) {
            console.log('开始解析YAML文档...');
            console.log('jsyaml库状态:', typeof jsyaml !== 'undefined' ? '已加载' : '未加载');
            apiDocData = parseYaml(content);
        } else {
            console.log('开始解析JSON文档...');
            apiDocData = JSON.parse(content);
        }
        
        console.log('解析结果:', apiDocData);
        
        // 验证OpenAPI版本
        if (!apiDocData.openapi || !apiDocData.openapi.startsWith('3.0.')) {
            throw new Error('仅支持OpenAPI 3.0.x版本');
        }
        
        // 提取API端点
        extractApiEndpoints();
        
        // 显示文件信息
        displayFileInfo(file.name, file.size);
        
        // 启用分析按钮
        document.getElementById('analyzeBtn').disabled = false;
        document.getElementById('saveBtn').disabled = false;
        
        showAlert('API文档上传成功！', 'success');
    } catch (error) {
        // 提供更详细的错误信息
        let errorMessage = '解析API文档失败';
        
        console.error('完整错误对象:', error);
        console.error('错误消息:', error.message);
        console.error('错误堆栈:', error.stack);
        
        if (error.message.includes('Unexpected token')) {
            errorMessage = 'JSON格式错误：请检查文件中的JSON语法是否正确';
        } else if (error.message.includes('YAML') || error.message.includes('yaml')) {
            errorMessage = `YAML格式错误：${error.message}`;
        } else if (error.message.includes('OpenAPI')) {
            errorMessage = `OpenAPI版本不支持：${error.message}`;
        } else if (error.message.includes('network')) {
            errorMessage = '网络错误：请检查网络连接或URL是否正确';
        } else {
            errorMessage = `解析API文档失败: ${error.message}`;
        }
        
        showAlert(errorMessage, 'danger');
        console.error('API文档解析错误:', error);
    } finally {
        hideUploadProgress();
    }
}

// 读取文件内容
function readFileContent(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

// 解析YAML（使用js-yaml库）
function parseYaml(yamlText) {
    try {
        // 检查是否已加载js-yaml库
        if (typeof jsyaml === 'undefined' && typeof YAML === 'undefined') {
            throw new Error('YAML解析库未加载，请确保已引入js-yaml库');
        }
        
        // 使用js-yaml库解析YAML
        // 尝试不同的全局变量名
        if (typeof jsyaml !== 'undefined') {
            return jsyaml.load(yamlText);
        } else if (typeof YAML !== 'undefined') {
            return YAML.parse(yamlText);
        } else {
            throw new Error('无法找到YAML解析函数');
        }
    } catch (error) {
        throw new Error(`YAML解析失败: ${error.message}`);
    }
}

// 提取API端点
function extractApiEndpoints() {
    apiEndpoints = [];
    
    if (!apiDocData.paths) return;
    
    Object.keys(apiDocData.paths).forEach(path => {
        const pathItem = apiDocData.paths[path];
        
        ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace'].forEach(method => {
            if (pathItem[method]) {
                apiEndpoints.push({
                    path,
                    method: method.toUpperCase(),
                    operationId: pathItem[method].operationId || `${method}_${path.replace(/\//g, '_')}`,
                    summary: pathItem[method].summary || pathItem[method].description || `${method} ${path}`,
                    tags: pathItem[method].tags || [],
                    parameters: pathItem[method].parameters || [],
                    requestBody: pathItem[method].requestBody,
                    responses: pathItem[method].responses || {}
                });
            }
        });
    });
    
    console.log('提取的API端点:', apiEndpoints);
}

// 显示文件信息
function displayFileInfo(fileName, fileSize) {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = `
        <div class="alert alert-success">
            <div class="d-flex align-items-center">
                <i class="fas fa-file-alt me-3 fs-3"></i>
                <div>
                    <h6 class="mb-1">${fileName}</h6>
                    <small class="text-muted">大小: ${formatFileSize(fileSize)} | API端点: ${apiEndpoints.length}个</small>
                </div>
            </div>
        </div>
    `;
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 显示上传进度
function showUploadProgress() {
    const uploadContainer = document.getElementById('uploadContainer');
    uploadContainer.classList.add('uploading');
    
    const uploadProgress = document.getElementById('uploadProgress');
    uploadProgress.style.display = 'block';
    
    // 模拟上传进度
    let progress = 0;
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    
    const interval = setInterval(() => {
        progress += 5;
        progressBar.style.width = `${progress}%`;
        progressPercent.textContent = `${progress}%`;
        
        if (progress >= 100) {
            clearInterval(interval);
        }
    }, 100);
}

// 隐藏上传进度
function hideUploadProgress() {
    const uploadContainer = document.getElementById('uploadContainer');
    uploadContainer.classList.remove('uploading');
    
    const uploadProgress = document.getElementById('uploadProgress');
    uploadProgress.style.display = 'none';
}

// 从URL获取API文档
async function fetchApiFromUrl() {
    const url = document.getElementById('apiUrl').value.trim();
    if (!url) {
        showAlert('请输入API文档URL', 'warning');
        return;
    }
    
    showLoading('获取API文档', '正在从URL获取API文档...');
    
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`获取失败: ${response.status} ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        let content = await response.text();
        
        // 根据内容类型解析
        if (contentType && contentType.includes('application/json')) {
            apiDocData = JSON.parse(content);
        } else {
            // 尝试解析为YAML
            apiDocData = parseYaml(content);
        }
        
        // 验证OpenAPI版本
        if (!apiDocData.openapi || !apiDocData.openapi.startsWith('3.0.')) {
            throw new Error('仅支持OpenAPI 3.0.x版本');
        }
        
        // 提取API端点
        extractApiEndpoints();
        
        // 显示结果
        const urlResult = document.getElementById('urlResult');
        urlResult.innerHTML = `
            <div class="alert alert-success">
                <h6>API文档获取成功！</h6>
                <small class="text-muted">API端点: ${apiEndpoints.length}个</small>
            </div>
        `;
        
        // 启用分析按钮
        document.getElementById('analyzeBtn').disabled = false;
        document.getElementById('saveBtn').disabled = false;
        
        showAlert('API文档获取成功！', 'success');
    } catch (error) {
        // 提供更详细的错误信息
        let errorMessage = '获取API文档失败';
        
        if (error.message.includes('Failed to fetch')) {
            errorMessage = '网络错误：无法连接到指定的URL，请检查网络连接和URL是否正确';
        } else if (error.message.includes('404')) {
            errorMessage = 'URL错误：指定的API文档不存在（404）';
        } else if (error.message.includes('403')) {
            errorMessage = '权限错误：无权访问指定的API文档（403）';
        } else if (error.message.includes('500')) {
            errorMessage = '服务器错误：API文档服务器内部错误（500）';
        } else if (error.message.includes('JSON')) {
            errorMessage = 'JSON格式错误：返回的内容不是有效的JSON格式';
        } else if (error.message.includes('YAML')) {
            errorMessage = `YAML格式错误：${error.message}`;
        } else if (error.message.includes('OpenAPI')) {
            errorMessage = `OpenAPI版本不支持：${error.message}`;
        } else {
            errorMessage = `获取API文档失败: ${error.message}`;
        }
        
        showAlert(errorMessage, 'danger');
        console.error('获取API文档错误:', error);
    } finally {
        hideLoading();
    }
}

// 清空文本输入
function clearApiText() {
    document.getElementById('apiText').value = '';
    document.getElementById('textResult').innerHTML = '';
    
    // 重置状态
    apiDocData = null;
    apiEndpoints = [];
    
    // 禁用分析按钮
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('saveBtn').disabled = true;
    
    showAlert('已清空输入内容', 'info');
}

// 解析文本输入的API文档
function parseApiText() {
    const text = document.getElementById('apiText').value.trim();
    if (!text) {
        showAlert('请输入API文档内容', 'warning');
        return;
    }
    
    try {
        // 尝试解析为JSON
        try {
            apiDocData = JSON.parse(text);
        } catch (e) {
            // 尝试解析为YAML
            apiDocData = parseYaml(text);
        }
        
        // 验证OpenAPI版本
        if (!apiDocData.openapi || !apiDocData.openapi.startsWith('3.0.')) {
            throw new Error('仅支持OpenAPI 3.0.x版本');
        }
        
        // 提取API端点
        extractApiEndpoints();
        
        // 显示结果
        const textResult = document.getElementById('textResult');
        textResult.innerHTML = `
            <div class="alert alert-success">
                <h6>API文档解析成功！</h6>
                <small class="text-muted">API端点: ${apiEndpoints.length}个</small>
            </div>
        `;
        
        // 启用分析按钮
        document.getElementById('analyzeBtn').disabled = false;
        document.getElementById('saveBtn').disabled = false;
        
        showAlert('API文档解析成功！', 'success');
    } catch (error) {
        // 提供更详细的错误信息
        let errorMessage = '解析API文档失败';
        
        if (error.message.includes('JSON')) {
            errorMessage = 'JSON格式错误：请检查JSON语法是否正确，确保括号、引号和逗号都正确使用';
        } else if (error.message.includes('YAML')) {
            errorMessage = `YAML格式错误：${error.message}`;
        } else if (error.message.includes('OpenAPI')) {
            errorMessage = `OpenAPI版本不支持：${error.message}。当前仅支持OpenAPI 3.0.x版本`;
        } else {
            errorMessage = `解析API文档失败: ${error.message}`;
        }
        
        showAlert(errorMessage, 'danger');
        console.error('API文档解析错误:', error);
    }
}

// 移动到步骤2
async function moveToStep2() {
    if (!apiDocData) {
        showAlert('请先上传或输入API文档', 'warning');
        return;
    }
    
    showLoading('分析场景与关联关系', '正在分析API场景和关联关系...');
    
    try {
        // 调用后端API分析场景
        const useLLMForScenes = document.getElementById('useLLMForScenes').checked;
        const sceneResponse = await API.post('/test-scenes/generate', {
            openapi_spec: apiDocData,
            use_llm: useLLMForScenes
        });
        
        if (sceneResponse.success) {
            scenes = sceneResponse.data.scenes || [];
            displayScenes();
        } else {
            throw new Error(sceneResponse.message || '场景分析失败');
        }
        
        // 调用后端API分析关联关系
        const useLLMForRelations = document.getElementById('useLLMForRelations').checked;
        const relationResponse = await API.post('/test-relation/generate', {
            openapi_spec: apiDocData,
            use_llm: useLLMForRelations
        });
        
        if (relationResponse.success) {
            relations = relationResponse.data.relations || [];
            displayRelations();
        } else {
            throw new Error(relationResponse.message || '关联关系分析失败');
        }
        
        // 更新步骤指示器
        updateStepIndicator(2);
        
        // 显示步骤2内容
        document.getElementById('step1Content').style.display = 'none';
        document.getElementById('step2Content').style.display = 'block';
        
        showAlert('场景与关联关系分析完成！', 'success');
    } catch (error) {
        showAlert(`分析失败: ${error.message}`, 'danger');
        console.error('场景与关联关系分析错误:', error);
    } finally {
        hideLoading();
    }
}

// 显示场景列表
function displayScenes() {
    const scenesList = document.getElementById('scenesList');
    
    if (scenes.length === 0) {
        scenesList.innerHTML = '<p class="text-muted">暂无场景数据</p>';
        return;
    }
    
    scenesList.innerHTML = scenes.map(scene => `
        <div class="card scene-card">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title">${scene.scene_name || scene.name || '未命名场景'}</h5>
                        <span class="badge bg-primary">${scene.type || 'API测试'}</span>
                        ${scene.confidence ? `<span class="badge bg-info">置信度: ${scene.confidence}</span>` : ''}
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item edit-scene" href="#" data-scene-id="${scene.scene_id || scene.id}"><i class="fas fa-edit me-2"></i>编辑</a></li>
                            <li><a class="dropdown-item delete-scene" href="#" data-scene-id="${scene.scene_id || scene.id}"><i class="fas fa-trash me-2"></i>删除</a></li>
                        </ul>
                    </div>
                </div>
                <p class="card-text">${scene.description || '暂无描述'}</p>
                <div class="mt-2">
                    <small class="text-muted">相关API:</small>
                    <div>
                        ${(scene.api_endpoints || scene.apis || []).map(api => 
                            `<span class="badge api-badge method-${api.method?.toLowerCase() || 'get'}">${api.method || 'GET'} ${api.path || api.endpoint || '/'}</span>`
                        ).join('')}
                    </div>
                </div>
                ${scene.test_points && scene.test_points.length > 0 ? `
                <div class="mt-2">
                    <small class="text-muted">测试点:</small>
                    <ul class="mb-0">
                        ${scene.test_points.map(point => `<li>${point}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // 添加场景编辑和删除事件监听器
    document.querySelectorAll('.edit-scene').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const sceneId = this.getAttribute('data-scene-id');
            editScene(sceneId);
        });
    });
    
    document.querySelectorAll('.delete-scene').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const sceneId = this.getAttribute('data-scene-id');
            deleteScene(sceneId);
        });
    });
}

// 显示关联关系列表
function displayRelations() {
    const relationsList = document.getElementById('relationsList');
    
    if (relations.length === 0) {
        relationsList.innerHTML = '<p class="text-muted">暂无关联关系数据</p>';
        return;
    }
    
    relationsList.innerHTML = relations.map(relation => `
        <div class="card relation-card">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title">${relation.source_api.method} ${relation.source_api.path} → ${relation.target_api.method} ${relation.target_api.path}</h5>
                        <span class="badge bg-primary">${relation.type}</span>
                        ${relation.confidence ? `<span class="badge bg-info">置信度: ${relation.confidence}</span>` : ''}
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item edit-relation" href="#" data-relation-id="${relation.id}"><i class="fas fa-edit me-2"></i>编辑</a></li>
                            <li><a class="dropdown-item delete-relation" href="#" data-relation-id="${relation.id}"><i class="fas fa-trash me-2"></i>删除</a></li>
                        </ul>
                    </div>
                </div>
                <p class="card-text">${relation.description}</p>
                ${relation.semantic_relations ? `
                    <div class="mt-2">
                        <small class="text-muted">语义关联:</small>
                        <p>${relation.semantic_relations}</p>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // 添加关联关系编辑和删除事件监听器
    document.querySelectorAll('.edit-relation').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const relationId = this.getAttribute('data-relation-id');
            editRelation(relationId);
        });
    });
    
    document.querySelectorAll('.delete-relation').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const relationId = this.getAttribute('data-relation-id');
            deleteRelation(relationId);
        });
    });
}

// 移动到步骤3
async function moveToStep3() {
    showLoading('生成测试用例', '正在根据场景和关联关系生成测试用例...');
    
    try {
        // 调用后端API生成测试用例
        const response = await API.post('/test-cases/generate', {
            openapi_spec: apiDocData,
            scenes: scenes,
            relations: relations
        });
        
        if (response.success) {
            testCases = response.data.test_cases || [];
            displayTestCases();
            
            // 更新统计信息
            updateTestCasesStats();
            
            // 更新步骤指示器
            updateStepIndicator(3);
            
            // 显示步骤3内容
            document.getElementById('step2Content').style.display = 'none';
            document.getElementById('step3Content').style.display = 'block';
            
            showAlert('测试用例生成完成！', 'success');
        } else {
            throw new Error(response.message || '测试用例生成失败');
        }
    } catch (error) {
        // 提供更详细的错误信息
        let errorMessage = '生成测试用例失败';
        
        if (error.message.includes('API文档解析失败')) {
            errorMessage = 'API文档解析失败：请检查API文档格式是否正确，确保是有效的OpenAPI 3.0.x规范';
        } else if (error.message.includes('场景') || error.message.includes('关联关系')) {
            errorMessage = '场景或关联关系分析失败：请确保已正确配置场景和关联关系';
        } else if (error.message.includes('网络') || error.message.includes('连接')) {
            errorMessage = '网络连接错误：请检查网络连接并重试';
        } else if (error.message.includes('500')) {
            errorMessage = '服务器内部错误：请稍后重试或联系管理员';
        } else if (error.message.includes('400')) {
            errorMessage = '请求参数错误：请检查输入参数是否正确';
        } else if (error.message.includes('404')) {
            errorMessage = '接口不存在：请检查API服务是否正常运行';
        } else {
            errorMessage = `生成测试用例失败: ${error.message}`;
        }
        
        showAlert(errorMessage, 'danger');
        console.error('测试用例生成错误:', error);
    } finally {
        hideLoading();
    }
}

// 显示测试用例列表
function displayTestCases() {
    const testCasesList = document.getElementById('testCasesList');
    
    if (testCases.length === 0) {
        testCasesList.innerHTML = '<p class="text-muted">暂无测试用例数据</p>';
        return;
    }
    
    testCasesList.innerHTML = testCases.map(testCase => `
        <div class="card test-case-card">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title">${testCase.name}</h5>
                        <span class="badge bg-primary">${testCase.method}</span>
                        <span class="badge bg-secondary">${testCase.path}</span>
                        ${testCase.status ? `<span class="badge bg-info">${testCase.status}</span>` : ''}
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item view-test-case" href="#" data-test-id="${testCase.id}"><i class="fas fa-eye me-2"></i>查看详情</a></li>
                            <li><a class="dropdown-item run-test-case" href="#" data-test-id="${testCase.id}"><i class="fas fa-play me-2"></i>运行测试</a></li>
                            <li><a class="dropdown-item edit-test-case" href="#" data-test-id="${testCase.id}"><i class="fas fa-edit me-2"></i>编辑</a></li>
                            <li><a class="dropdown-item delete-test-case" href="#" data-test-id="${testCase.id}"><i class="fas fa-trash me-2"></i>删除</a></li>
                        </ul>
                    </div>
                </div>
                <p class="card-text">${testCase.description}</p>
                <div class="mt-2">
                    <small class="text-muted">相关场景:</small>
                    <div>
                        ${(testCase.scenes || []).map(scene => 
                            `<span class="badge bg-light text-dark">${scene}</span>`
                        ).join('')}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    // 添加测试用例操作事件监听器
    document.querySelectorAll('.view-test-case').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const testId = this.getAttribute('data-test-id');
            viewTestCaseDetail(testId);
        });
    });
    
    document.querySelectorAll('.run-test-case').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const testId = this.getAttribute('data-test-id');
            runTestCase(testId);
        });
    });
    
    document.querySelectorAll('.edit-test-case').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const testId = this.getAttribute('data-test-id');
            editTestCase(testId);
        });
    });
    
    document.querySelectorAll('.delete-test-case').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const testId = this.getAttribute('data-test-id');
            deleteTestCase(testId);
        });
    });
}

// 更新测试用例统计信息
function updateTestCasesStats() {
    document.getElementById('generatedCasesCount').textContent = testCases.length;
    
    // 计算覆盖的API数量
    const coveredApis = new Set();
    testCases.forEach(testCase => {
        coveredApis.add(`${testCase.method}:${testCase.path}`);
    });
    document.getElementById('coveredApisCount').textContent = coveredApis.size;
    
    // 计算覆盖的场景数量
    const coveredScenes = new Set();
    testCases.forEach(testCase => {
        (testCase.scenes || []).forEach(scene => {
            coveredScenes.add(scene);
        });
    });
    document.getElementById('coveredScenesCount').textContent = coveredScenes.size;
}

// 过滤测试用例
function filterTestCases() {
    const searchTerm = document.getElementById('searchCases').value.toLowerCase();
    const filteredTestCases = testCases.filter(testCase => 
        testCase.name.toLowerCase().includes(searchTerm) ||
        testCase.description.toLowerCase().includes(searchTerm) ||
        testCase.path.toLowerCase().includes(searchTerm) ||
        testCase.method.toLowerCase().includes(searchTerm)
    );
    
    // 临时保存原始测试用例列表
    const originalTestCases = testCases;
    
    // 设置过滤后的测试用例列表
    testCases = filteredTestCases;
    
    // 重新显示测试用例
    displayTestCases();
    
    // 恢复原始测试用例列表
    testCases = originalTestCases;
}

// 显示添加场景模态框
function showAddSceneModal() {
    // 填充API选择器
    const sceneApisContainer = document.getElementById('sceneApisContainer');
    sceneApisContainer.innerHTML = apiEndpoints.map(api => `
        <div class="form-check">
            <input class="form-check-input" type="checkbox" value="${api.operationId}" id="api_${api.operationId}">
            <label class="form-check-label" for="api_${api.operationId}">
                <span class="badge api-badge method-${api.method.toLowerCase()}">${api.method} ${api.path}</span>
                ${api.summary}
            </label>
        </div>
    `).join('');
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('addSceneModal'));
    modal.show();
}

// 保存自定义场景
function saveCustomScene() {
    const name = document.getElementById('sceneName').value.trim();
    const type = document.getElementById('sceneType').value;
    const description = document.getElementById('sceneDescription').value.trim();
    
    if (!name || !type || !description) {
        showAlert('请填写完整的场景信息', 'warning');
        return;
    }
    
    // 获取选中的API
    const selectedApis = [];
    document.querySelectorAll('#sceneApisContainer input:checked').forEach(checkbox => {
        const operationId = checkbox.value;
        const api = apiEndpoints.find(a => a.operationId === operationId);
        if (api) {
            selectedApis.push({
                operationId: api.operationId,
                method: api.method,
                path: api.path,
                summary: api.summary
            });
        }
    });
    
    // 创建新场景
    const newScene = {
        id: `custom_scene_${Date.now()}`,
        name,
        type,
        description,
        apis: selectedApis,
        is_custom: true
    };
    
    // 添加到场景列表
    scenes.push(newScene);
    
    // 重新显示场景列表
    displayScenes();
    
    // 关闭模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('addSceneModal'));
    modal.hide();
    
    // 重置表单
    document.getElementById('addSceneForm').reset();
    
    showAlert('自定义场景添加成功！', 'success');
}

// 显示添加关联关系模态框
function showAddRelationModal() {
    // 填充源API和目标API选择器
    const relationSource = document.getElementById('relationSource');
    const relationTarget = document.getElementById('relationTarget');
    
    const apiOptions = apiEndpoints.map(api => 
        `<option value="${api.operationId}">${api.method} ${api.path} - ${api.summary}</option>`
    ).join('');
    
    relationSource.innerHTML = apiOptions;
    relationTarget.innerHTML = apiOptions;
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('addRelationModal'));
    modal.show();
}

// 保存自定义关联关系
function saveCustomRelation() {
    const sourceOperationId = document.getElementById('relationSource').value;
    const targetOperationId = document.getElementById('relationTarget').value;
    const type = document.getElementById('relationType').value;
    const description = document.getElementById('relationDescription').value.trim();
    const confidence = parseFloat(document.getElementById('relationConfidence').value);
    
    if (!sourceOperationId || !targetOperationId || !type || !description) {
        showAlert('请填写完整的关联关系信息', 'warning');
        return;
    }
    
    // 查找源API和目标API
    const sourceApi = apiEndpoints.find(api => api.operationId === sourceOperationId);
    const targetApi = apiEndpoints.find(api => api.operationId === targetOperationId);
    
    if (!sourceApi || !targetApi) {
        showAlert('选择的API不存在', 'danger');
        return;
    }
    
    // 创建新关联关系
    const newRelation = {
        id: `custom_relation_${Date.now()}`,
        source_api: {
            operationId: sourceApi.operationId,
            method: sourceApi.method,
            path: sourceApi.path
        },
        target_api: {
            operationId: targetApi.operationId,
            method: targetApi.method,
            path: targetApi.path
        },
        type,
        description,
        confidence,
        is_custom: true
    };
    
    // 添加到关联关系列表
    relations.push(newRelation);
    
    // 重新显示关联关系列表
    displayRelations();
    
    // 关闭模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('addRelationModal'));
    modal.hide();
    
    // 重置表单
    document.getElementById('addRelationForm').reset();
    
    showAlert('自定义关联关系添加成功！', 'success');
}

// 查看测试用例详情
function viewTestCaseDetail(testId) {
    const testCase = testCases.find(tc => tc.id === testId);
    if (!testCase) {
        showAlert('测试用例不存在', 'warning');
        return;
    }
    
    // 生成测试用例详情HTML
    const testCaseDetail = document.getElementById('testCaseDetail');
    testCaseDetail.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h5>基本信息</h5>
                <table class="table table-borderless">
                    <tr>
                        <td><strong>名称:</strong></td>
                        <td>${testCase.name}</td>
                    </tr>
                    <tr>
                        <td><strong>方法:</strong></td>
                        <td><span class="badge api-badge method-${testCase.method.toLowerCase()}">${testCase.method}</span></td>
                    </tr>
                    <tr>
                        <td><strong>路径:</strong></td>
                        <td>${testCase.path}</td>
                    </tr>
                    <tr>
                        <td><strong>描述:</strong></td>
                        <td>${testCase.description}</td>
                    </tr>
                    <tr>
                        <td><strong>状态:</strong></td>
                        <td>${testCase.status ? `<span class="badge bg-info">${testCase.status}</span>` : '无'}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h5>关联信息</h5>
                <table class="table table-borderless">
                    <tr>
                        <td><strong>相关场景:</strong></td>
                        <td>
                            ${(testCase.scenes || []).map(scene => 
                                `<span class="badge bg-light text-dark">${scene}</span>`
                            ).join(' ')}
                        </td>
                    </tr>
                    <tr>
                        <td><strong>关联关系:</strong></td>
                        <td>
                            ${(testCase.relations || []).map(relation => 
                                `<span class="badge bg-light text-dark">${relation}</span>`
                            ).join(' ')}
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="mt-4">
            <h5>请求详情</h5>
            <div class="code-container">
                <pre><code class="language-json">${JSON.stringify(testCase.request, null, 2)}</code></pre>
            </div>
        </div>
        
        <div class="mt-4">
            <h5>预期响应</h5>
            <div class="code-container">
                <pre><code class="language-json">${JSON.stringify(testCase.expected_response, null, 2)}</code></pre>
            </div>
        </div>
    `;
    
    // 重新初始化代码高亮
    Prism.highlightAll();
    
    // 设置当前测试用例ID，用于运行单个测试
    document.getElementById('runSingleTestBtn').setAttribute('data-test-id', testId);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('testCaseDetailModal'));
    modal.show();
}

// 运行单个测试
async function runSingleTest() {
    const testId = document.getElementById('runSingleTestBtn').getAttribute('data-test-id');
    if (!testId) {
        showAlert('无法获取测试用例ID', 'warning');
        return;
    }
    
    await runTestCase(testId);
}

// 运行测试用例
async function runTestCase(testId) {
    showLoading('运行测试用例', `正在运行测试用例 ${testId}...`);
    
    try {
        const response = await API.post(`/test-cases/${testId}/run`);
        
        if (response.success) {
            showAlert('测试用例执行成功！', 'success');
            
            // 更新测试用例状态
            const testCase = testCases.find(tc => tc.id === testId);
            if (testCase && response.data.results && response.data.results[testId]) {
                testCase.status = response.data.results[testId].status;
                testCase.result = response.data.results[testId];
                
                // 重新显示测试用例列表
                displayTestCases();
            }
        } else {
            throw new Error(response.message || '测试用例执行失败');
        }
    } catch (error) {
        showAlert(`测试用例执行失败: ${error.message}`, 'danger');
        console.error('测试用例执行错误:', error);
    } finally {
        hideLoading();
    }
}

// 运行所有测试
async function runAllTests() {
    if (testCases.length === 0) {
        showAlert('没有可运行的测试用例', 'warning');
        return;
    }
    
    showLoading('运行所有测试', '正在运行所有测试用例...');
    
    try {
        const testIds = testCases.map(tc => tc.id);
        const response = await API.post(`/test-cases/${testIds[0]}/run`);
        
        if (response.success) {
            showAlert('所有测试用例执行完成！', 'success');
            
            // 更新测试用例状态
            if (response.data.results) {
                Object.keys(response.data.results).forEach(testId => {
                    const testCase = testCases.find(tc => tc.id === testId);
                    if (testCase) {
                        testCase.status = response.data.results[testId].status;
                        testCase.result = response.data.results[testId];
                    }
                });
                
                // 重新显示测试用例列表
                displayTestCases();
            }
        } else {
            throw new Error(response.message || '测试用例执行失败');
        }
    } catch (error) {
        showAlert(`测试用例执行失败: ${error.message}`, 'danger');
        console.error('测试用例执行错误:', error);
    } finally {
        hideLoading();
    }
}

// 导出测试用例
function exportTestCases() {
    if (testCases.length === 0) {
        showAlert('没有可导出的测试用例', 'warning');
        return;
    }
    
    // 创建导出数据
    const exportData = {
        generated_at: new Date().toISOString(),
        api_info: {
            title: apiDocData.info?.title || 'API',
            version: apiDocData.info?.version || '1.0.0'
        },
        scenes: scenes,
        relations: relations,
        test_cases: testCases
    };
    
    // 创建下载链接
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `test-cases-${new Date().toISOString().slice(0,10)}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    showAlert('测试用例导出成功！', 'success');
}

// 编辑场景
function editScene(sceneId) {
    const scene = scenes.find(s => s.id === sceneId);
    if (!scene) {
        showAlert('场景不存在', 'warning');
        return;
    }
    
    // 填充表单
    document.getElementById('sceneName').value = scene.name;
    document.getElementById('sceneType').value = scene.type;
    document.getElementById('sceneDescription').value = scene.description;
    
    // 填充API选择器
    const sceneApisContainer = document.getElementById('sceneApisContainer');
    sceneApisContainer.innerHTML = apiEndpoints.map(api => {
        const isChecked = scene.apis && scene.apis.some(sApi => sApi.operationId === api.operationId);
        return `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${api.operationId}" id="api_${api.operationId}" ${isChecked ? 'checked' : ''}>
                <label class="form-check-label" for="api_${api.operationId}">
                    <span class="badge api-badge method-${api.method.toLowerCase()}">${api.method} ${api.path}</span>
                    ${api.summary}
                </label>
            </div>
        `;
    }).join('');
    
    // 修改保存按钮行为
    const saveBtn = document.getElementById('saveSceneBtn');
    saveBtn.textContent = '更新';
    saveBtn.setAttribute('data-scene-id', sceneId);
    saveBtn.removeEventListener('click', saveCustomScene);
    saveBtn.addEventListener('click', updateScene);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('addSceneModal'));
    modal.show();
}

// 更新场景
function updateScene() {
    const sceneId = document.getElementById('saveSceneBtn').getAttribute('data-scene-id');
    const name = document.getElementById('sceneName').value.trim();
    const type = document.getElementById('sceneType').value;
    const description = document.getElementById('sceneDescription').value.trim();
    
    if (!name || !type || !description) {
        showAlert('请填写完整的场景信息', 'warning');
        return;
    }
    
    // 获取选中的API
    const selectedApis = [];
    document.querySelectorAll('#sceneApisContainer input:checked').forEach(checkbox => {
        const operationId = checkbox.value;
        const api = apiEndpoints.find(a => a.operationId === operationId);
        if (api) {
            selectedApis.push({
                operationId: api.operationId,
                method: api.method,
                path: api.path,
                summary: api.summary
            });
        }
    });
    
    // 查找并更新场景
    const sceneIndex = scenes.findIndex(s => s.id === sceneId);
    if (sceneIndex !== -1) {
        scenes[sceneIndex] = {
            ...scenes[sceneIndex],
            name,
            type,
            description,
            apis: selectedApis
        };
        
        // 重新显示场景列表
        displayScenes();
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('addSceneModal'));
        modal.hide();
        
        // 重置表单和按钮
        document.getElementById('addSceneForm').reset();
        const saveBtn = document.getElementById('saveSceneBtn');
        saveBtn.textContent = '保存';
        saveBtn.removeAttribute('data-scene-id');
        saveBtn.removeEventListener('click', updateScene);
        saveBtn.addEventListener('click', saveCustomScene);
        
        showAlert('场景更新成功！', 'success');
    } else {
        showAlert('场景不存在', 'danger');
    }
}

// 删除场景
function deleteScene(sceneId) {
    if (!confirm('确定要删除此场景吗？')) {
        return;
    }
    
    const sceneIndex = scenes.findIndex(s => s.id === sceneId);
    if (sceneIndex !== -1) {
        scenes.splice(sceneIndex, 1);
        displayScenes();
        showAlert('场景删除成功！', 'success');
    } else {
        showAlert('场景不存在', 'danger');
    }
}

// 编辑关联关系
function editRelation(relationId) {
    const relation = relations.find(r => r.id === relationId);
    if (!relation) {
        showAlert('关联关系不存在', 'warning');
        return;
    }
    
    // 填充表单
    document.getElementById('relationSource').value = relation.source_api.operationId;
    document.getElementById('relationTarget').value = relation.target_api.operationId;
    document.getElementById('relationType').value = relation.type;
    document.getElementById('relationDescription').value = relation.description;
    document.getElementById('relationConfidence').value = relation.confidence || 0.8;
    
    // 修改保存按钮行为
    const saveBtn = document.getElementById('saveRelationBtn');
    saveBtn.textContent = '更新';
    saveBtn.setAttribute('data-relation-id', relationId);
    saveBtn.removeEventListener('click', saveCustomRelation);
    saveBtn.addEventListener('click', updateRelation);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('addRelationModal'));
    modal.show();
}

// 更新关联关系
function updateRelation() {
    const relationId = document.getElementById('saveRelationBtn').getAttribute('data-relation-id');
    const sourceOperationId = document.getElementById('relationSource').value;
    const targetOperationId = document.getElementById('relationTarget').value;
    const type = document.getElementById('relationType').value;
    const description = document.getElementById('relationDescription').value.trim();
    const confidence = parseFloat(document.getElementById('relationConfidence').value);
    
    if (!sourceOperationId || !targetOperationId || !type || !description) {
        showAlert('请填写完整的关联关系信息', 'warning');
        return;
    }
    
    // 查找源API和目标API
    const sourceApi = apiEndpoints.find(api => api.operationId === sourceOperationId);
    const targetApi = apiEndpoints.find(api => api.operationId === targetOperationId);
    
    if (!sourceApi || !targetApi) {
        showAlert('选择的API不存在', 'danger');
        return;
    }
    
    // 查找并更新关联关系
    const relationIndex = relations.findIndex(r => r.id === relationId);
    if (relationIndex !== -1) {
        relations[relationIndex] = {
            ...relations[relationIndex],
            source_api: {
                operationId: sourceApi.operationId,
                method: sourceApi.method,
                path: sourceApi.path
            },
            target_api: {
                operationId: targetApi.operationId,
                method: targetApi.method,
                path: targetApi.path
            },
            type,
            description,
            confidence
        };
        
        // 重新显示关联关系列表
        displayRelations();
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('addRelationModal'));
        modal.hide();
        
        // 重置表单和按钮
        document.getElementById('addRelationForm').reset();
        const saveBtn = document.getElementById('saveRelationBtn');
        saveBtn.textContent = '保存';
        saveBtn.removeAttribute('data-relation-id');
        saveBtn.removeEventListener('click', updateRelation);
        saveBtn.addEventListener('click', saveCustomRelation);
        
        showAlert('关联关系更新成功！', 'success');
    } else {
        showAlert('关联关系不存在', 'danger');
    }
}

// 删除关联关系
function deleteRelation(relationId) {
    if (!confirm('确定要删除此关联关系吗？')) {
        return;
    }
    
    const relationIndex = relations.findIndex(r => r.id === relationId);
    if (relationIndex !== -1) {
        relations.splice(relationIndex, 1);
        displayRelations();
        showAlert('关联关系删除成功！', 'success');
    } else {
        showAlert('关联关系不存在', 'danger');
    }
}

// 编辑测试用例
function editTestCase(testId) {
    // 这里可以实现测试用例编辑功能
    showAlert('测试用例编辑功能尚未实现', 'info');
}

// 删除测试用例
function deleteTestCase(testId) {
    if (!confirm('确定要删除此测试用例吗？')) {
        return;
    }
    
    const testCaseIndex = testCases.findIndex(tc => tc.id === testId);
    if (testCaseIndex !== -1) {
        testCases.splice(testCaseIndex, 1);
        displayTestCases();
        updateTestCasesStats();
        showAlert('测试用例删除成功！', 'success');
    } else {
        showAlert('测试用例不存在', 'danger');
    }
}

// 移动到步骤1
function moveToStep1() {
    updateStepIndicator(1);
    document.getElementById('step2Content').style.display = 'none';
    document.getElementById('step3Content').style.display = 'none';
    document.getElementById('step1Content').style.display = 'block';
}

// 更新步骤指示器
function updateStepIndicator(step) {
    currentStep = step;
    
    // 重置所有步骤
    document.querySelectorAll('.step').forEach(stepEl => {
        stepEl.classList.remove('active', 'completed');
    });
    
    // 设置当前步骤及之前步骤为完成状态
    for (let i = 1; i <= step; i++) {
        const stepEl = document.getElementById(`step${i}`);
        if (i < step) {
            stepEl.classList.add('completed');
        } else {
            stepEl.classList.add('active');
        }
    }
}

// 重置所有
function resetAll() {
    if (!confirm('确定要重置所有数据吗？此操作不可恢复。')) {
        return;
    }
    
    // 重置全局变量
    currentStep = 1;
    apiDocData = null;
    apiEndpoints = [];
    scenes = [];
    relations = [];
    testCases = [];
    
    // 重置UI
    updateStepIndicator(1);
    document.getElementById('step1Content').style.display = 'block';
    document.getElementById('step2Content').style.display = 'none';
    document.getElementById('step3Content').style.display = 'none';
    
    // 重置文件上传
    document.getElementById('fileList').innerHTML = '';
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('saveBtn').disabled = true;
    
    // 重置场景和关联列表
    document.getElementById('scenesList').innerHTML = '';
    document.getElementById('relationsList').innerHTML = '';
    
    // 重置测试用例列表
    document.getElementById('testCasesList').innerHTML = '';
    document.getElementById('generatedCasesCount').textContent = '0';
    document.getElementById('coveredApisCount').textContent = '0';
    document.getElementById('coveredScenesCount').textContent = '0';
    
    showAlert('已重置所有数据', 'info');
}

// 保存配置
async function saveConfiguration() {
    if (!apiDocData) {
        showAlert('没有可保存的配置', 'warning');
        return;
    }
    
    showLoading('保存配置', '正在保存配置...');
    
    try {
        const configData = {
            api_doc: apiDocData,
            scenes: scenes,
            relations: relations
        };
        
        const response = await API.post('/config/save', configData);
        
        if (response.success) {
            showAlert('配置保存成功！', 'success');
        } else {
            throw new Error(response.message || '配置保存失败');
        }
    } catch (error) {
        showAlert(`配置保存失败: ${error.message}`, 'danger');
        console.error('配置保存错误:', error);
    } finally {
        hideLoading();
    }
}

// 完成流程
function finishProcess() {
    if (!confirm('确定要完成智能测试生成流程吗？')) {
        return;
    }
    
    // 跳转到测试用例页面
    window.location.href = 'test-cases.html';
}

// 显示加载遮罩
function showLoading(title, message) {
    document.getElementById('loadingTitle').textContent = title;
    document.getElementById('loadingMessage').textContent = message;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

// 隐藏加载遮罩
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// 显示提示消息
function showAlert(message, type) {
    // 创建提示元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 添加到页面顶部
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 3000);
}