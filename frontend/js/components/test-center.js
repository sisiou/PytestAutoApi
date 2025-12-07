// 测试中心页面JavaScript - 合并API文档、智能测试生成和测试用例功能

// 全局变量 - 检查是否已存在，避免重复声明
if (typeof currentStep === 'undefined') {
    var currentStep = 1;
}
if (typeof apiDocData === 'undefined') {
    var apiDocData = null;
}
if (typeof testCases === 'undefined') {
    var testCases = [];
}
if (typeof scenarios === 'undefined') {
    var scenarios = [];
}
if (typeof relations === 'undefined') {
    var relations = [];
}
if (typeof selectedApis === 'undefined') {
    var selectedApis = new Set();
}

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 注意：不要在这里调用initTestCenter，因为它会在test-center.js中被调用
    // 避免重复初始化
    // 直接调用智能测试功能的初始化
    initSmartTestTab();
    loadSmartTestSavedData();
});

// 初始化测试中心 - 智能测试功能专用
function initSmartTestCenter() {
    // 初始化智能测试生成功能
    initSmartTestTab();
    
    // 注意：不要在这里调用initTestCasesTab，因为它会在test-center.js中被调用
    // 避免重复初始化
    
    // 加载已保存的数据 - 使用专用函数避免冲突
    loadSmartTestSavedData();
}



// 初始化智能测试标签页
function initSmartTestTab() {
    // 文件上传按钮
    const smartUploadBtn = document.getElementById('smartUploadBtn');
    if (smartUploadBtn) {
        smartUploadBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.click();
            }
        });
    }
    
    // 文件选择
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleSmartFileSelect);
    }
    
    // URL获取按钮
    const fetchUrlBtn = document.getElementById('fetchUrlBtn');
    if (fetchUrlBtn) {
        fetchUrlBtn.addEventListener('click', fetchSmartApiFromUrl);
    }
    
    // 飞书URL获取按钮
    const fetchFeishuUrlBtn = document.getElementById('fetchFeishuUrlBtn');
    if (fetchFeishuUrlBtn) {
        fetchFeishuUrlBtn.addEventListener('click', fetchSmartApiFromUrl);
    }
    
    // 移除文件按钮
    const smartRemoveFileBtn = document.getElementById('smartRemoveFileBtn');
    if (smartRemoveFileBtn) {
        smartRemoveFileBtn.addEventListener('click', removeSmartFile);
    }
    
    // 分析按钮
    const analyzeApiBtn = document.getElementById('analyzeApiBtn');
    if (analyzeApiBtn) {
        analyzeApiBtn.addEventListener('click', analyzeSmartApiDoc);
    }
    
    // 生成选中的测试用例按钮
    const generateSelectedTestsBtn = document.getElementById('generateSelectedTestsBtn');
    if (generateSelectedTestsBtn) {
        generateSelectedTestsBtn.addEventListener('click', generateSelectedTests);
    }
    
    // 移除文件按钮
    const removeFileBtn = document.getElementById('removeFileBtn');
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', removeSmartFile);
    }
    
    // 文本输入监听
    const apiTextInput = document.getElementById('apiTextInput');
    if (apiTextInput) {
        apiTextInput.addEventListener('input', function() {
            const parseBtn = document.getElementById('parseTextBtn');
            if (parseBtn) {
                parseBtn.disabled = this.value.trim() === '';
            }
        });
    }
    
    // 解析文本按钮
    const parseTextBtn = document.getElementById('parseTextBtn');
    if (parseTextBtn) {
        parseTextBtn.addEventListener('click', parseApiText);
    }
    
    // 步骤导航按钮
    const backToStep1Btn = document.getElementById('backToStep1Btn');
    if (backToStep1Btn) {
        backToStep1Btn.addEventListener('click', function() {
            goToStep(1);
        });
    }
    
    const backToStep2Btn = document.getElementById('backToStep2Btn');
    if (backToStep2Btn) {
        backToStep2Btn.addEventListener('click', function() {
            goToStep(2);
        });
    }
    
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateTestCases);
    }
    
    // 添加场景按钮
    const addSceneBtn = document.getElementById('addSceneBtn');
    if (addSceneBtn) {
        addSceneBtn.addEventListener('click', showAddSceneModal);
    }
    
    // 添加依赖关系按钮
    const addRelationBtn = document.getElementById('addRelationBtn');
    if (addRelationBtn) {
        addRelationBtn.addEventListener('click', showAddRelationModal);
    }
    
    // 保存场景按钮
    const saveSceneBtn = document.getElementById('saveSceneBtn');
    if (saveSceneBtn) {
        saveSceneBtn.addEventListener('click', saveScene);
    }
    
    // 保存依赖关系按钮
    const saveRelationBtn = document.getElementById('saveRelationBtn');
    if (saveRelationBtn) {
        saveRelationBtn.addEventListener('click', saveRelation);
    }
    
    // 导出按钮
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportTestCases);
    }
    
    // 运行测试按钮
    const runTestsBtn = document.getElementById('runTestsBtn');
    if (runTestsBtn) {
        runTestsBtn.addEventListener('click', runAllTests);
    }
    
    // 保存配置按钮
    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveConfiguration);
    }
    
    // 重置按钮
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetConfiguration);
    }
    
    // 完成按钮
    const finishBtn = document.getElementById('finishBtn');
    if (finishBtn) {
        finishBtn.addEventListener('click', finishProcess);
    }
    
    // 拖拽上传 - 使用正确的容器ID
    setupDragAndDrop('uploadContainer');
}

// 初始化测试用例标签页 - 智能测试功能专用
function initSmartTestCasesTab() {
    // 运行所有测试按钮
    const runAllCasesBtn = document.getElementById('runAllCasesBtn');
    if (runAllCasesBtn) {
        runAllCasesBtn.addEventListener('click', runAllCases);
    }
    
    // 生成测试用例按钮
    const generateCasesBtn = document.getElementById('generateCasesBtn');
    if (generateCasesBtn) {
        generateCasesBtn.addEventListener('click', function() {
            // 切换到智能测试生成标签页
            const smartTestTab = document.getElementById('smart-test-tab');
            if (smartTestTab) {
                smartTestTab.click();
            }
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
    const listViewBtn = document.getElementById('listViewBtn');
    if (listViewBtn) {
        listViewBtn.addEventListener('click', function() {
            // 切换按钮状态
            listViewBtn.classList.add('btn-primary');
            listViewBtn.classList.remove('btn-outline-primary');
            
            const gridViewBtn = document.getElementById('gridViewBtn');
            if (gridViewBtn) {
                gridViewBtn.classList.remove('btn-primary');
                gridViewBtn.classList.add('btn-outline-primary');
            }
            
            // 切换视图显示
            const listView = document.getElementById('listView');
            const gridView = document.getElementById('gridView');
            
            if (listView) listView.classList.remove('d-none');
            if (gridView) gridView.classList.add('d-none');
            
            // 重新渲染测试用例列表
            renderTestCasesList('list');
        });
    }
    
    const gridViewBtn = document.getElementById('gridViewBtn');
    if (gridViewBtn) {
        gridViewBtn.addEventListener('click', function() {
            // 切换按钮状态
            gridViewBtn.classList.add('btn-primary');
            gridViewBtn.classList.remove('btn-outline-primary');
            
            const listViewBtn = document.getElementById('listViewBtn');
            if (listViewBtn) {
                listViewBtn.classList.remove('btn-primary');
                listViewBtn.classList.add('btn-outline-primary');
            }
            
            // 切换视图显示
            const listView = document.getElementById('listView');
            const gridView = document.getElementById('gridView');
            
            if (gridView) gridView.classList.remove('d-none');
            if (listView) listView.classList.add('d-none');
            
            // 重新渲染测试用例列表
            renderTestCasesList('grid');
        });
    }
    
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
        showSmartTestNotification('请上传JSON或YAML格式的API文档', 'error');
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
            showSmartTestNotification('文件解析失败: ' + error.message, 'error');
            hideUploadProgress();
        }
    };
    
    reader.onerror = function() {
        showSmartTestNotification('文件读取失败', 'error');
        hideUploadProgress();
    };
    
    reader.readAsText(file);
}

// 从URL获取API文档 (智能测试标签页)
function fetchSmartApiFromUrl(event) {
    console.log('fetchSmartApiFromUrl called', event);
    
    // 确定是哪个按钮被点击，从而获取对应的输入框
    let urlInput;
    let fetchButton;
    
    if (event && event.target && event.target.id === 'fetchFeishuUrlBtn') {
        // 如果是飞书URL按钮，获取飞书标签页的输入框
        urlInput = document.getElementById('feishuApiUrlInput');
        fetchButton = document.getElementById('fetchFeishuUrlBtn');
        console.log('Using feishuApiUrlInput');
    } else {
        // 默认获取第一个输入框
        urlInput = document.getElementById('apiUrlInput');
        fetchButton = document.getElementById('fetchUrlBtn');
        console.log('Using apiUrlInput');
    }
    
    if (!urlInput) {
        console.error('URL input element not found');
        showSmartTestNotification('找不到URL输入框', 'error');
        return;
    }
    
    const url = urlInput.value.trim();
    if (!url) {
        console.error('URL is empty');
        showSmartTestNotification('请输入API文档URL', 'error');
        return;
    }
    
    console.log('Fetching API document from URL:', url);
    
    // 显示进度条和详细状态
    showUploadProgress();
    updateProgressMessage('正在获取API文档...');
    updateProgressBar(10);
    
    // 显示加载动画
    showLoading('正在获取API文档，请稍候...');
    
    // 禁用获取文档按钮，防止重复点击
    if (fetchButton) {
        fetchButton.disabled = true;
        fetchButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>获取中...';
    }
    
    // 使用直接拼接URL的方式，避免undefined问题
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const fetchUrl = baseUrl + '/api/ai/parse';
    console.log('Fetch URL:', fetchUrl);
    
    // 设置超时时间为2分钟
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 120秒超时（2分钟）
    
    console.log('Starting fetch request...');
    
    fetch(fetchUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url }),
        signal: controller.signal
    })
        .then(response => {
            console.log('Received response:', response);
            clearTimeout(timeoutId);
            updateProgressMessage('正在解析文档内容...');
            updateProgressBar(50);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data);
            updateProgressMessage('正在处理API文档...');
            updateProgressBar(80);
            
            if (!data.success) {
                throw new Error(data.error || '解析失败');
            }
            
            const fileName = url.split('/').pop() || 'api-doc';
            // 使用AI解析返回的OpenAPI数据
            const apiContent = JSON.stringify(data.openapi_data);
            
            updateProgressMessage('正在完成文档解析...');
            updateProgressBar(90);
            
            parseSmartApiDocContent(apiContent, fileName, apiContent.length, true);
            
            // 保存关联关系和业务场景数据到全局变量
            if (data.relation_data) {
                relations = data.relation_data.relation_info ? data.relation_data.relation_info.relations : [];
                console.log('Relations loaded:', relations);
            }
            
            if (data.scene_data) {
                scenarios = data.scene_data.business_scenes ? data.scene_data.business_scenes.scenes : [];
                console.log('Scenarios loaded:', scenarios);
            }
            
            updateProgressBar(100);
            setTimeout(() => {
                hideUploadProgress();
                hideLoading();
                // 恢复按钮状态
                if (fetchButton) {
                    fetchButton.disabled = false;
                    if (fetchButton.id === 'fetchFeishuUrlBtn') {
                        fetchButton.innerHTML = '<i class="fas fa-download me-2"></i>获取文档';
                    } else {
                        fetchButton.innerHTML = '<i class="fas fa-download me-2"></i>获取文档';
                    }
                }
            }, 500);
        })
        .catch(error => {
            console.error('Fetch error:', error);
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                showSmartTestNotification('获取文档超时，请稍后重试', 'error');
            } else {
                showSmartTestNotification('获取API文档失败: ' + error.message, 'error');
            }
            hideUploadProgress();
            hideLoading();
            // 恢复按钮状态
            if (fetchButton) {
                fetchButton.disabled = false;
                if (fetchButton.id === 'fetchFeishuUrlBtn') {
                    fetchButton.innerHTML = '<i class="fas fa-download me-2"></i>获取文档';
                } else {
                    fetchButton.innerHTML = '<i class="fas fa-download me-2"></i>获取文档';
                }
            }
        });
}

// 解析API文档内容 (智能测试标签页)
function parseSmartApiDocContent(content, fileName, fileSize, isFromUrl = false) {
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
        // 根据来源显示不同的成功消息
        if (isFromUrl) {
            showSmartTestNotification('API文档获取成功', 'success');
        } else {
            showSmartTestNotification('API文档上传成功', 'success');
        }
        
        // 启用分析按钮
        const analyzeApiBtn = document.getElementById('analyzeApiBtn');
        if (analyzeApiBtn) {
            analyzeApiBtn.disabled = false;
        }
        
        // 如果是从URL获取的文档，自动触发分析流程
        if (isFromUrl) {
            setTimeout(() => {
                analyzeSmartApiDoc();
            }, 1000);
        }
    } catch (error) {
        showSmartTestNotification('API文档解析失败: ' + error.message, 'error');
        hideUploadProgress();
    }
}

// 显示文件信息 (智能测试标签页)
function showSmartFileInfo(fileName, fileSize, apiDoc) {
    const fileNameEl = document.getElementById('fileName');
    const fileSizeEl = document.getElementById('fileSize');
    const apiVersionEl = document.getElementById('apiVersion');
    const apiTitleEl = document.getElementById('apiTitle');
    const fileInfoEl = document.getElementById('fileInfo');
    
    if (!fileNameEl) {
        console.warn('Element with ID "fileName" not found');
        return;
    }
    
    if (!fileSizeEl) {
        console.warn('Element with ID "fileSize" not found');
        return;
    }
    
    if (!apiVersionEl) {
        console.warn('Element with ID "apiVersion" not found');
        return;
    }
    
    if (!apiTitleEl) {
        console.warn('Element with ID "apiTitle" not found');
        return;
    }
    
    if (!fileInfoEl) {
        console.warn('Element with ID "fileInfo" not found');
        return;
    }
    
    fileNameEl.textContent = fileName;
    fileSizeEl.textContent = formatFileSize(fileSize);
    apiVersionEl.textContent = apiDoc.openapi || '未知';
    apiTitleEl.textContent = apiDoc.info?.title || '未知';
    fileInfoEl.style.display = 'block';
}

// 移除文件 (智能测试标签页)
function removeSmartFile() {
    apiDocData = null;
    
    const fileInfoEl = document.getElementById('fileInfo');
    if (fileInfoEl) {
        fileInfoEl.style.display = 'none';
    } else {
        console.warn('Element with ID "fileInfo" not found');
    }
    
    const fileInputEl = document.getElementById('fileInput');
    if (fileInputEl) {
        fileInputEl.value = '';
    } else {
        console.warn('Element with ID "fileInput" not found');
    }
    
    // 清空所有URL输入框
    const apiUrlInput = document.getElementById('apiUrlInput');
    if (apiUrlInput) {
        apiUrlInput.value = '';
    } else {
        console.warn('Element with ID "apiUrlInput" not found');
    }
    
    const feishuApiUrlInput = document.getElementById('feishuApiUrlInput');
    if (feishuApiUrlInput) {
        feishuApiUrlInput.value = '';
    } else {
        console.warn('Element with ID "feishuApiUrlInput" not found');
    }
    
    const apiTextInput = document.getElementById('apiTextInput');
    if (apiTextInput) {
        apiTextInput.value = '';
    } else {
        console.warn('Element with ID "apiTextInput" not found');
    }
    
    const parseTextBtn = document.getElementById('parseTextBtn');
    if (parseTextBtn) {
        parseTextBtn.disabled = true;
    } else {
        console.warn('Element with ID "parseTextBtn" not found');
    }
    
    // 禁用分析按钮
    const analyzeApiBtn = document.getElementById('analyzeApiBtn');
    if (analyzeApiBtn) {
        analyzeApiBtn.disabled = true;
    }
}

// 解析API文本 (智能测试标签页)
function parseApiText() {
    const apiTextInput = document.getElementById('apiTextInput');
    if (!apiTextInput) {
        console.warn('Element with ID "apiTextInput" not found');
        return;
    }
    
    const content = apiTextInput.value.trim();
    if (!content) {
        showSmartTestNotification('请输入API文档内容', 'error');
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
        
        showSmartTestNotification('API文档解析成功', 'success');
    } catch (error) {
        showSmartTestNotification('API文档解析失败: ' + error.message, 'error');
    }
}

// 分析API文档 (智能测试标签页)
function analyzeSmartApiDoc() {
    if (!apiDocData) {
        showSmartTestNotification('请先上传API文档', 'error');
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
                    
                    // 显示API分析结果
                    displayApiAnalysisResult(endpoints);
                    
                    // 显示场景与关联分析
                    displayScenarioAnalysis(scenarios, relations);
                    
                    // 显示智能测试生成
                    displayTestGeneration();
                    
                    hideLoading();
                    showSmartTestNotification('API文档分析完成', 'success');
                })
                .catch(error => {
                    hideLoading();
                    showSmartTestNotification('API文档分析失败: ' + error.message, 'error');
                });
        })
        .catch(error => {
            hideLoading();
            showSmartTestNotification('API文档分析失败: ' + error.message, 'error');
        });
}

// 显示API分析结果
function displayApiAnalysisResult(endpoints) {
    const apiAnalysisResult = document.getElementById('apiAnalysisResult');
    if (!apiAnalysisResult) {
        console.warn('Element with ID "apiAnalysisResult" not found');
        return;
    }
    
    // 更新统计数据
    const totalEndpoints = document.getElementById('totalEndpoints');
    if (totalEndpoints) {
        totalEndpoints.textContent = endpoints.length;
    }
    
    const totalMethods = document.getElementById('totalMethods');
    if (totalMethods) {
        const methods = new Set(endpoints.map(e => e.method));
        totalMethods.textContent = methods.size;
    }
    
    const totalSchemas = document.getElementById('totalSchemas');
    if (totalSchemas) {
        // 这里应该从API文档中提取schema数量，暂时使用默认值
        totalSchemas.textContent = '0';
    }
    
    const authTypes = document.getElementById('authTypes');
    if (authTypes) {
        // 这里应该从API文档中提取认证类型，暂时使用默认值
        authTypes.textContent = '0';
    }
    
    // 显示端点列表
    const endpointsList = document.getElementById('endpointsList');
    if (endpointsList) {
        endpointsList.innerHTML = '';
        
        endpoints.forEach(endpoint => {
            const row = document.createElement('tr');
            
            const methodCell = document.createElement('td');
            const methodBadge = document.createElement('span');
            methodBadge.className = `badge bg-${getMethodColor(endpoint.method)}`;
            methodBadge.textContent = endpoint.method;
            methodCell.appendChild(methodBadge);
            
            const pathCell = document.createElement('td');
            pathCell.textContent = endpoint.path;
            
            const descCell = document.createElement('td');
            descCell.textContent = endpoint.summary || endpoint.description || '无描述';
            
            row.appendChild(methodCell);
            row.appendChild(pathCell);
            row.appendChild(descCell);
            
            endpointsList.appendChild(row);
        });
    }
    
    // 显示分析结果卡片
    apiAnalysisResult.style.display = 'block';
}

// 显示场景与关联分析
function displayScenarioAnalysis(scenarios, relations) {
    const scenarioAnalysis = document.getElementById('scenarioAnalysis');
    if (!scenarioAnalysis) {
        console.warn('Element with ID "scenarioAnalysis" not found');
        return;
    }
    
    // 显示场景列表
    const scenariosList = document.getElementById('scenariosList');
    if (scenariosList) {
        scenariosList.innerHTML = '';
        
        scenarios.forEach(scene => {
            const sceneCard = document.createElement('div');
            sceneCard.className = 'card mb-2';
            
            const sceneCardBody = document.createElement('div');
            sceneCardBody.className = 'card-body p-2';
            
            const sceneTitle = document.createElement('h6');
            sceneTitle.className = 'card-title mb-1';
            sceneTitle.textContent = scene.name;
            
            const sceneDescription = document.createElement('p');
            sceneDescription.className = 'card-text small text-muted';
            sceneDescription.textContent = scene.description;
            
            const sceneApis = document.createElement('div');
            sceneApis.className = 'mt-2';
            
            scene.apis.forEach(api => {
                const apiBadge = document.createElement('span');
                apiBadge.className = `badge bg-${getMethodColor(api.method)} me-1`;
                apiBadge.textContent = `${api.method} ${api.path}`;
                sceneApis.appendChild(apiBadge);
            });
            
            sceneCardBody.appendChild(sceneTitle);
            sceneCardBody.appendChild(sceneDescription);
            sceneCardBody.appendChild(sceneApis);
            sceneCard.appendChild(sceneCardBody);
            scenariosList.appendChild(sceneCard);
        });
    }
    
    // 显示场景与关联分析卡片
    scenarioAnalysis.style.display = 'block';
}

// 显示智能测试生成
function displayTestGeneration() {
    const testGeneration = document.getElementById('testGeneration');
    if (!testGeneration) {
        console.warn('Element with ID "testGeneration" not found');
        return;
    }
    
    // 显示测试场景
    const testScenarios = document.getElementById('testScenarios');
    if (testScenarios) {
        testScenarios.innerHTML = '';
        
        scenarios.forEach(scene => {
            const scenarioCheck = document.createElement('div');
            scenarioCheck.className = 'form-check';
            
            const checkInput = document.createElement('input');
            checkInput.className = 'form-check-input';
            checkInput.type = 'checkbox';
            checkInput.value = scene.id;
            checkInput.id = `scenario-${scene.id}`;
            checkInput.checked = true;
            
            const checkLabel = document.createElement('label');
            checkLabel.className = 'form-check-label';
            checkLabel.htmlFor = `scenario-${scene.id}`;
            checkLabel.textContent = scene.name;
            
            scenarioCheck.appendChild(checkInput);
            scenarioCheck.appendChild(checkLabel);
            testScenarios.appendChild(scenarioCheck);
        });
    }
    
    // 显示智能测试生成卡片
    testGeneration.style.display = 'block';
}

// 获取方法对应的颜色
function getMethodColor(method) {
    const colors = {
        'GET': 'success',
        'POST': 'primary',
        'PUT': 'warning',
        'DELETE': 'danger',
        'PATCH': 'info',
        'HEAD': 'secondary',
        'OPTIONS': 'secondary'
    };
    return colors[method] || 'secondary';
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
    if (!apiList) {
        console.warn('Element with ID "apiList" not found');
        return;
    }
    
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
    if (!scenesList) {
        console.warn('Element with ID "scenesList" not found');
        return;
    }
    
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
    if (!relationsList) {
        console.warn('Element with ID "relationsList" not found');
        return;
    }
    
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
                showSmartTestNotification('测试用例生成完成', 'success');
                
                // 进入步骤3
                goToStep(3);
            })
            .catch(error => {
                hideLoading();
                showSmartTestNotification('测试用例生成失败: ' + error.message, 'error');
            });
    }, 2000);
}

// 显示测试用例
function displayTestCases(testCases) {
    const testCasesList = document.getElementById('testCasesList');
    if (!testCasesList) {
        console.warn('Element with ID "testCasesList" not found');
        return;
    }
    
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

// 筛选测试用例
function filterTestCases() {
    const searchCasesInput = document.getElementById('searchCasesInput');
    const statusFilter = document.getElementById('statusFilter');
    const typeFilter = document.getElementById('typeFilter');
    const apiFilter = document.getElementById('apiFilter');
    const listViewBtn = document.getElementById('listViewBtn');
    
    if (!searchCasesInput || !statusFilter || !typeFilter || !apiFilter || !listViewBtn) {
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
    
    const viewMode = listViewBtn.classList.contains('btn-primary') ? 'list' : 'grid';
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
        const listViewBtn = document.getElementById('listViewBtn');
        if (listViewBtn) {
            const viewMode = listViewBtn.classList.contains('btn-primary') ? 'list' : 'grid';
            renderTestCasesList(viewMode);
        } else {
            console.warn('Element with ID "listViewBtn" not found');
        }
        
        hideLoading();
        showSmartTestNotification('所有测试用例运行完成', 'success');
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
        const listViewBtn = document.getElementById('listViewBtn');
        if (listViewBtn) {
            const viewMode = listViewBtn.classList.contains('btn-primary') ? 'list' : 'grid';
            renderTestCasesList(viewMode);
        } else {
            console.warn('Element with ID "listViewBtn" not found');
        }
        
        hideLoading();
        showSmartTestNotification(`测试用例 "${testCase.name}" 运行完成`, 'success');
    }, 1500);
}

// 编辑测试用例
function editTestCase(testCaseId) {
    const testCase = testCases.find(tc => tc.id === testCaseId);
    if (!testCase) return;
    
    showSmartTestNotification(`编辑测试用例: ${testCase.name}`, 'info');
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
        const listViewBtn = document.getElementById('listViewBtn');
        if (listViewBtn) {
            const viewMode = listViewBtn.classList.contains('btn-primary') ? 'list' : 'grid';
            renderTestCasesList(viewMode);
        } else {
            console.warn('Element with ID "listViewBtn" not found');
        }
        
        showSmartTestNotification(`测试用例 "${testCase.name}" 已删除`, 'success');
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
        showSmartTestNotification('所有测试运行完成', 'success');
    }, 3000);
}

// 导出测试用例
function exportTestCases() {
    if (!testCases || testCases.length === 0) {
        showSmartTestNotification('没有可导出的测试用例', 'error');
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
    
    showSmartTestNotification('测试用例导出成功', 'success');
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
    showSmartTestNotification('配置保存成功', 'success');
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
        
        showSmartTestNotification('配置已重置', 'success');
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
        } else {
            console.warn('Element with ID "test-cases-tab" not found');
        }
        
        // 重新加载测试用例
        loadTestCases();
        
        showSmartTestNotification('测试生成流程已完成', 'success');
    }
}

// 显示添加场景模态框
function showAddSceneModal() {
    const addSceneModal = document.getElementById('addSceneModal');
    if (!addSceneModal) {
        console.warn('Element with ID "addSceneModal" not found');
        return;
    }
    
    const modal = new bootstrap.Modal(addSceneModal);
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            // 填充API复选框
            const sceneApis = document.getElementById('sceneApis');
            if (!sceneApis) {
                console.warn('Element with ID "sceneApis" not found');
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
            showSmartTestNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 保存场景
function saveScene() {
    const sceneNameEl = document.getElementById('sceneName');
    const sceneDescriptionEl = document.getElementById('sceneDescription');
    
    if (!sceneNameEl) {
        console.warn('Element with ID "sceneName" not found');
        return;
    }
    
    if (!sceneDescriptionEl) {
        console.warn('Element with ID "sceneDescription" not found');
        return;
    }
    
    const sceneName = sceneNameEl.value.trim();
    const sceneDescription = sceneDescriptionEl.value.trim();
    
    if (!sceneName) {
        showSmartTestNotification('请输入场景名称', 'error');
        return;
    }
    
    // 获取选中的API
    const selectedApiElements = document.querySelectorAll('#sceneApis input:checked');
    if (selectedApiElements.length === 0) {
        showSmartTestNotification('请选择至少一个API', 'error');
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
            if (sceneNameEl) sceneNameEl.value = '';
            if (sceneDescriptionEl) sceneDescriptionEl.value = '';
            
            showSmartTestNotification('场景添加成功', 'success');
        })
        .catch(error => {
            showSmartTestNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 显示添加依赖关系模态框
function showAddRelationModal() {
    const addRelationModal = document.getElementById('addRelationModal');
    if (!addRelationModal) {
        console.warn('Element with ID "addRelationModal" not found');
        return;
    }
    
    const modal = new bootstrap.Modal(addRelationModal);
    
    // 首先提取API端点
    extractApiEndpoints(apiDocData)
        .then(endpoints => {
            // 填充源API和目标API下拉框
            const relationSource = document.getElementById('relationSource');
            const relationTarget = document.getElementById('relationTarget');
            
            if (!relationSource) {
                console.warn('Element with ID "relationSource" not found');
                return;
            }
            
            if (!relationTarget) {
                console.warn('Element with ID "relationTarget" not found');
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
            showSmartTestNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 保存依赖关系
function saveRelation() {
    const relationSourceEl = document.getElementById('relationSource');
    const relationTargetEl = document.getElementById('relationTarget');
    const relationTypeEl = document.getElementById('relationType');
    const relationDescriptionEl = document.getElementById('relationDescription');
    
    if (!relationSourceEl) {
        console.warn('Element with ID "relationSource" not found');
        return;
    }
    
    if (!relationTargetEl) {
        console.warn('Element with ID "relationTarget" not found');
        return;
    }
    
    if (!relationTypeEl) {
        console.warn('Element with ID "relationType" not found');
        return;
    }
    
    if (!relationDescriptionEl) {
        console.warn('Element with ID "relationDescription" not found');
        return;
    }
    
    const sourceValue = relationSourceEl.value;
    const targetValue = relationTargetEl.value;
    const relationType = relationTypeEl.value;
    const relationDescription = relationDescriptionEl.value.trim();
    
    if (!sourceValue || !targetValue) {
        showSmartTestNotification('请选择源API和目标API', 'error');
        return;
    }
    
    if (sourceValue === targetValue) {
        showSmartTestNotification('源API和目标API不能相同', 'error');
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
            const addRelationModal = document.getElementById('addRelationModal');
            if (addRelationModal) {
                const modal = bootstrap.Modal.getInstance(addRelationModal);
                if (modal) {
                    modal.hide();
                }
            }
            
            // 清空表单
            if (relationDescriptionEl) relationDescriptionEl.value = '';
            
            showSmartTestNotification('依赖关系添加成功', 'success');
        })
        .catch(error => {
            showSmartTestNotification('获取API端点失败: ' + error.message, 'error');
        });
}

// 切换到指定步骤
function goToStep(step) {
    // 隐藏所有步骤内容
    const stepContents = document.querySelectorAll('.step-content');
    if (stepContents.length === 0) {
        console.warn('No elements with class "step-content" found');
        return;
    }
    
    stepContents.forEach(content => {
        content.style.display = 'none';
    });
    
    // 更新步骤指示器
    const stepElements = document.querySelectorAll('.step');
    if (stepElements.length === 0) {
        console.warn('No elements with class "step" found');
        return;
    }
    
    stepElements.forEach((stepElement, index) => {
        stepElement.classList.remove('active', 'completed');
        if (index + 1 < step) {
            stepElement.classList.add('completed');
        } else if (index + 1 === step) {
            stepElement.classList.add('active');
        }
    });
    
    // 显示当前步骤内容
    const currentStepContent = document.getElementById(`step${step}Content`);
    if (!currentStepContent) {
        console.warn(`Element with ID "step${step}Content" not found`);
        return;
    }
    
    currentStepContent.style.display = 'block';
    
    currentStep = step;
}

// 加载已保存的数据 - 智能测试功能专用
function loadSmartTestSavedData() {
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
                
                const analyzeApiBtn = document.getElementById('analyzeApiBtn');
                if (analyzeApiBtn) {
                    analyzeApiBtn.disabled = false;
                } else {
                    console.warn('Element with ID "analyzeApiBtn" not found');
                }
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
    } else {
        console.warn('Element with ID "uploadProgress" not found');
    }
}

// 隐藏上传进度
function hideUploadProgress() {
    const progressElement = document.getElementById('uploadProgress');
    if (progressElement) {
        progressElement.style.display = 'none';
    } else {
        console.warn('Element with ID "uploadProgress" not found');
    }
}

// 更新进度条
function updateProgressBar(percent) {
    const progressBar = document.getElementById('uploadProgressBar');
    const uploadPercent = document.getElementById('uploadPercent');
    
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.setAttribute('aria-valuenow', percent);
    } else {
        console.warn('Element with ID "uploadProgressBar" not found');
    }
    
    if (uploadPercent) {
        uploadPercent.textContent = percent + '%';
    } else {
        console.warn('Element with ID "uploadPercent" not found');
    }
}

// 更新进度消息
function updateProgressMessage(message) {
    const progressElement = document.getElementById('uploadProgress');
    if (progressElement) {
        const messageElement = progressElement.querySelector('.d-flex span:first-child');
        if (messageElement) {
            messageElement.textContent = message;
        }
    } else {
        console.warn('Element with ID "uploadProgress" not found');
    }
}

// 显示加载遮罩
function showLoading(message = '正在处理，请稍候...') {
    const loadingMessage = document.getElementById('loadingMessage');
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    if (loadingMessage) {
        loadingMessage.textContent = message;
    } else {
        console.warn('Element with ID "loadingMessage" not found');
    }
    
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    } else {
        console.warn('Element with ID "loadingOverlay" not found');
    }
}

// 隐藏加载遮罩
function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    } else {
        console.warn('Element with ID "loadingOverlay" not found');
    }
}

// 显示通知 - 智能测试功能专用
function showSmartTestNotification(message, type = 'info') {
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

// 生成选中的测试用例
function generateSelectedTests() {
    // 获取选中的场景
    const selectedScenarios = [];
    const checkboxes = document.querySelectorAll('#testScenarios input[type="checkbox"]:checked');
    
    checkboxes.forEach(checkbox => {
        const scenarioId = checkbox.value;
        const scenario = scenarios.find(s => s.id === scenarioId);
        if (scenario) {
            selectedScenarios.push(scenario);
        }
    });
    
    if (selectedScenarios.length === 0) {
        showSmartTestNotification('请至少选择一个测试场景', 'warning');
        return;
    }
    
    showLoading('正在生成测试用例...');
    
    // 模拟API调用生成测试用例
    setTimeout(() => {
        try {
            // 生成测试用例
            const testCases = [];
            
            selectedScenarios.forEach(scenario => {
                scenario.apis.forEach(api => {
                    // 为每个API生成基础测试
                    testCases.push({
                        id: `test-${api.method}-${api.path}-${scenario.id}`,
                        name: `${scenario.name} - ${api.method} ${api.path}`,
                        description: `测试${api.method} ${api.path}在${scenario.name}场景中的功能`,
                        type: 'scenario',
                        api: api,
                        scenario: scenario,
                        status: 'pending'
                    });
                });
            });
            
            // 保存测试用例到全局变量
            window.generatedTestCases = testCases;
            
            // 切换到测试用例标签页
            const testCasesTab = document.getElementById('test-cases-tab');
            if (testCasesTab) {
                testCasesTab.click();
            }
            
            // 显示生成的测试用例
            renderTestCasesList('list');
            
            hideLoading();
            showSmartTestNotification(`成功生成 ${testCases.length} 个测试用例`, 'success');
            
        } catch (error) {
            hideLoading();
            showSmartTestNotification('生成测试用例失败: ' + error.message, 'error');
        }
    }, 2000);
}