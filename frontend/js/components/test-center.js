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
if (typeof multiApiDocuments === 'undefined') {
    var multiApiDocuments = [];
}

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 注意：不要在这里调用initTestCenter，因为它会在test-center.js中被调用
    // 避免重复初始化
    // 直接调用智能测试功能的初始化
    initSmartTestTab();
    loadSmartTestSavedData();
    
    // 加载已上传文档列表
    loadUploadedDocuments();
    
    // 初始化测试编辑器按钮
    initTestEditorButtons();
    
    // 初始化文档标签页
    initDocumentTabs();
    
    // 初始化测试工作流
    initTestWorkflow();
    
    // 确保多接口文档标签页默认加载一次数据
    setTimeout(() => {
        // 检查是否已经加载过多接口文档数据
        if (!multiApiDocuments || multiApiDocuments.length === 0) {
            console.log('页面初始化时加载多接口文档数据');
            loadMultiApiDocuments();
        }
    }, 1000);
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
    
    // 选择文件按钮
    const selectFileBtn = document.getElementById('selectFileBtn');
    if (selectFileBtn) {
        selectFileBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.click();
            }
        });
    }
    
    // 上传容器点击事件
    const uploadContainer = document.getElementById('uploadContainer');
    if (uploadContainer) {
        uploadContainer.addEventListener('click', function(e) {
            // 确保点击的不是按钮或其他交互元素
            if (e.target === uploadContainer || 
                e.target.tagName === 'I' || 
                e.target.tagName === 'H4' || 
                e.target.tagName === 'P' ||
                e.target.classList.contains('file-icon')) {
                const fileInput = document.getElementById('fileInput');
                if (fileInput) {
                    fileInput.click();
                }
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
    
    // 刷新按钮事件监听
    const refreshDocsBtn = document.getElementById('refreshDocsBtn');
    if (refreshDocsBtn) {
        refreshDocsBtn.addEventListener('click', loadUploadedDocuments);
    }
    
    const refreshOpenApiDocsBtn = document.getElementById('refreshOpenApiDocsBtn');
    if (refreshOpenApiDocsBtn) {
        refreshOpenApiDocsBtn.addEventListener('click', loadUploadedDocuments);
    }
    
    // 关联关系文档刷新按钮
    const refreshRelationDocsBtn = document.getElementById('refreshRelationDocsBtn');
    if (refreshRelationDocsBtn) {
        refreshRelationDocsBtn.addEventListener('click', loadUploadedDocuments);
    }
    
    // 业务场景文档刷新按钮
    const refreshSceneDocsBtn = document.getElementById('refreshSceneDocsBtn');
    if (refreshSceneDocsBtn) {
        refreshSceneDocsBtn.addEventListener('click', loadUploadedDocuments);
    }
    
    // 多接口文档刷新按钮
    const refreshMultiApiDocsBtn = document.getElementById('refreshMultiApiDocsBtn');
    if (refreshMultiApiDocsBtn) {
        refreshMultiApiDocsBtn.addEventListener('click', loadMultiApiDocuments);
    }
    
    // 初始化标签页切换事件
    initDocumentTabs();
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
    updateProgressMessage('正在上传文件...');
    updateProgressBar(10);
    
    // 创建FormData对象用于文件上传
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', 'openapi');
    formData.append('target_path', '/Users/oss/code/PytestAutoApi/multiuploads/openapi');
    
    // 上传文件到服务器
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const uploadUrl = baseUrl + (endpoints.DOCS ? endpoints.DOCS.UPLOAD : '/api/docs/upload');
    
    fetch(uploadUrl, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        updateProgressMessage('正在解析文件内容...');
        updateProgressBar(50);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        updateProgressMessage('正在处理API文档...');
        updateProgressBar(80);
        
        if (!data.success) {
            throw new Error(data.message || '上传失败');
        }
        
        // 读取文件内容进行本地解析
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const content = e.target.result;
                updateProgressMessage('正在完成文档解析...');
                updateProgressBar(90);
                
                parseSmartApiDocContent(content, file.name, file.size);
                
                updateProgressBar(100);
                setTimeout(() => {
                    hideUploadProgress();
                    showSmartTestNotification(`文件 ${file.name} 上传成功`, 'success');
                }, 500);
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
    })
    .catch(error => {
        console.error('Upload error:', error);
        showSmartTestNotification('文件上传失败: ' + error.message, 'error');
        hideUploadProgress();
    });
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


// 加载已上传文档列表
function loadUploadedDocuments() {
    console.log('开始加载已上传文档列表');
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    
    console.log('API_CONFIG.BASE_URL:', baseUrl);
    console.log('API_CONFIG.ENDPOINTS.DOCS.ALL_DOCUMENTS:', docsEndpoint.ALL_DOCUMENTS || '/api/docs/all-documents');
    
    // 使用新的API端点 - 获取所有类型的文档列表
    const apiUrl = baseUrl + (docsEndpoint.ALL_DOCUMENTS || '/api/docs/all-documents');
    console.log('完整的API URL:', apiUrl);
    
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            console.log('获取文档列表响应:', data);
            
            // API返回格式为 {success: true, data: {openapi: {...}, relation: {...}, scene: {...}}, total_count: N}
            const allDocuments = data.data || {};
            console.log('所有文档列表:', allDocuments);
            
            // 处理OpenAPI文档
            const openapiDocs = allDocuments.openapi ? allDocuments.openapi.documents : [];
            const openapiTableBody = document.getElementById('openApiDocsTableBody');
            const noOpenApiDocsMessage = document.getElementById('noOpenApiDocsMessage');
            
            if (openapiTableBody) {
                // 清空现有内容
                openapiTableBody.innerHTML = '';
                
                if (openapiDocs.length === 0) {
                    // 显示无文档消息
                    if (noOpenApiDocsMessage) {
                        noOpenApiDocsMessage.style.display = 'block';
                    }
                    console.log('没有OpenAPI文档');
                } else {
                    // 隐藏无文档消息
                    if (noOpenApiDocsMessage) {
                        noOpenApiDocsMessage.style.display = 'none';
                    }
                    
                    // 添加文档到表格
                    openapiDocs.forEach(doc => {
                        console.log('OpenAPI文档数据:', doc);
                        const row = document.createElement('tr');
                        
                        // 文档ID
                        const idCell = document.createElement('td');
                        idCell.textContent = doc.file_id || '未知ID';
                        row.appendChild(idCell);
                        
                        // 上传时间
                        const uploadTimeCell = document.createElement('td');
                        const uploadDate = new Date(doc.upload_time);
                        uploadTimeCell.textContent = uploadDate.toLocaleString();
                        row.appendChild(uploadTimeCell);
                        
                        // 操作
                        const actionsCell = document.createElement('td');
                        const viewBtn = document.createElement('button');
                        viewBtn.className = 'btn btn-sm btn-outline-primary me-1';
                        viewBtn.innerHTML = '<i class="fas fa-eye"></i> 查看';
                        viewBtn.addEventListener('click', () => {
                            console.log('点击查看按钮，文档类型: openapi, 文档ID:', doc.file_id);
                            console.log('完整文档对象:', doc);
                            viewDocument('openapi', doc.file_id);
                        });
                        
                        const generateBtn = document.createElement('button');
                        generateBtn.className = 'btn btn-sm btn-outline-success me-1';
                        generateBtn.innerHTML = '<i class="fas fa-code"></i> 生成测试用例';
                        generateBtn.addEventListener('click', () => {
                            generateTestCases(doc.file_id);
                        });
                        
                        const executeBtn = document.createElement('button');
                        executeBtn.className = 'btn btn-sm btn-outline-info me-1';
                        executeBtn.innerHTML = '<i class="fas fa-play"></i> 执行测试用例';
                        executeBtn.addEventListener('click', () => {
                            executeTestCases(doc.file_id);
                        });
                        
                        const editBtn = document.createElement('button');
                        editBtn.className = 'btn btn-sm btn-outline-warning me-1';
                        editBtn.innerHTML = '<i class="fas fa-edit"></i> 编辑';
                        editBtn.addEventListener('click', () => editThreeDocuments(doc.file_id));
                        
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'btn btn-sm btn-outline-danger';
                        deleteBtn.innerHTML = '<i class="fas fa-trash"></i> 删除';
                        deleteBtn.addEventListener('click', () => deleteDocument('openapi', doc.file_id));
                        
                        actionsCell.appendChild(viewBtn);
                        actionsCell.appendChild(generateBtn);
                        actionsCell.appendChild(executeBtn);
                        actionsCell.appendChild(editBtn);
                        actionsCell.appendChild(deleteBtn);
                        row.appendChild(actionsCell);
                        
                        openapiTableBody.appendChild(row);
                    });
                }
            }
            
            // 处理关系文档
            const relationDocs = allDocuments.relation ? allDocuments.relation.documents : [];
            const relationTableBody = document.getElementById('relationDocsTableBody');
            const noRelationDocsMessage = document.getElementById('noRelationDocsMessage');
            
            if (relationTableBody) {
                // 清空现有内容
                relationTableBody.innerHTML = '';
                
                if (relationDocs.length === 0) {
                    // 显示无文档消息
                    if (noRelationDocsMessage) {
                        noRelationDocsMessage.style.display = 'block';
                    }
                    console.log('没有关系文档');
                } else {
                    // 隐藏无文档消息
                    if (noRelationDocsMessage) {
                        noRelationDocsMessage.style.display = 'none';
                    }
                    
                    // 添加文档到表格
                    relationDocs.forEach(doc => {
                        console.log('关联关系文档数据:', doc);
                        const row = document.createElement('tr');
                        
                        // 文档名称
                        const nameCell = document.createElement('td');
                        nameCell.textContent = doc.file_name || '未知文件';
                        row.appendChild(nameCell);
                        
                        // 项目数量
                        const itemCountCell = document.createElement('td');
                        itemCountCell.textContent = doc.item_count || 0;
                        row.appendChild(itemCountCell);
                        
                        // 上传时间
                        const uploadTimeCell = document.createElement('td');
                        const uploadDate = new Date(doc.upload_time);
                        uploadTimeCell.textContent = uploadDate.toLocaleString();
                        row.appendChild(uploadTimeCell);
                        
                        // 操作
                        const actionsCell = document.createElement('td');
                        const viewBtn = document.createElement('button');
                        viewBtn.className = 'btn btn-sm btn-outline-primary me-1';
                        viewBtn.innerHTML = '<i class="fas fa-eye"></i> 查看';
                        viewBtn.addEventListener('click', () => {
                            console.log('点击查看按钮，文档类型: relation, 文档ID:', doc.file_id);
                            console.log('完整文档对象:', doc);
                            viewDocument('relation', doc.file_id);
                        });
                        
                        const editBtn = document.createElement('button');
                        editBtn.className = 'btn btn-sm btn-outline-warning me-1';
                        editBtn.innerHTML = '<i class="fas fa-edit"></i> 编辑';
                        editBtn.addEventListener('click', () => editThreeDocuments(doc.file_id));
                        
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'btn btn-sm btn-outline-danger';
                        deleteBtn.innerHTML = '<i class="fas fa-trash"></i> 删除';
                        deleteBtn.addEventListener('click', () => deleteDocument('relation', doc.file_id));
                        
                        actionsCell.appendChild(viewBtn);
                        actionsCell.appendChild(editBtn);
                        actionsCell.appendChild(deleteBtn);
                        row.appendChild(actionsCell);
                        
                        relationTableBody.appendChild(row);
                    });
                }
            }
            
            // 处理场景文档
            const sceneDocs = allDocuments.scene ? allDocuments.scene.documents : [];
            const sceneTableBody = document.getElementById('sceneDocsTableBody');
            const noSceneDocsMessage = document.getElementById('noSceneDocsMessage');
            
            if (sceneTableBody) {
                // 清空现有内容
                sceneTableBody.innerHTML = '';
                
                if (sceneDocs.length === 0) {
                    // 显示无文档消息
                    if (noSceneDocsMessage) {
                        noSceneDocsMessage.style.display = 'block';
                    }
                    console.log('没有场景文档');
                } else {
                    // 隐藏无文档消息
                    if (noSceneDocsMessage) {
                        noSceneDocsMessage.style.display = 'none';
                    }
                    
                    // 添加文档到表格
                    sceneDocs.forEach(doc => {
                        console.log('场景文档数据:', doc);
                        const row = document.createElement('tr');
                        
                        // 文档名称
                        const nameCell = document.createElement('td');
                        nameCell.textContent = doc.file_name || '未知文件';
                        row.appendChild(nameCell);
                        
                        // 项目数量
                        const itemCountCell = document.createElement('td');
                        itemCountCell.textContent = doc.item_count || 0;
                        row.appendChild(itemCountCell);
                        
                        // 上传时间
                        const uploadTimeCell = document.createElement('td');
                        const uploadDate = new Date(doc.upload_time);
                        uploadTimeCell.textContent = uploadDate.toLocaleString();
                        row.appendChild(uploadTimeCell);
                        
                        // 操作
                        const actionsCell = document.createElement('td');
                        const viewBtn = document.createElement('button');
                        viewBtn.className = 'btn btn-sm btn-outline-primary me-1';
                        viewBtn.innerHTML = '<i class="fas fa-eye"></i> 查看';
                        viewBtn.addEventListener('click', () => {
                            console.log('点击查看按钮，文档类型: scene, 文档ID:', doc.file_id);
                            console.log('完整文档对象:', doc);
                            viewDocument('scene', doc.file_id);
                        });
                        
                        const editBtn = document.createElement('button');
                        editBtn.className = 'btn btn-sm btn-outline-warning me-1';
                        editBtn.innerHTML = '<i class="fas fa-edit"></i> 编辑';
                        editBtn.addEventListener('click', () => editThreeDocuments(doc.file_id));
                        
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'btn btn-sm btn-outline-danger';
                        deleteBtn.innerHTML = '<i class="fas fa-trash"></i> 删除';
                        deleteBtn.addEventListener('click', () => deleteDocument('scene', doc.file_id));
                        
                        actionsCell.appendChild(viewBtn);
                        actionsCell.appendChild(editBtn);
                        actionsCell.appendChild(deleteBtn);
                        row.appendChild(actionsCell);
                        
                        sceneTableBody.appendChild(row);
                    });
                }
            }
            
            console.log(`已加载 ${openapiDocs.length} 个OpenAPI文档, ${relationDocs.length} 个关系文档, ${sceneDocs.length} 个场景文档`);
        })
        .catch(error => {
            console.error('加载文档列表失败:', error);
            showSmartTestNotification('加载文档列表失败: ' + error.message, 'error');
        });
}



// 查看文档详情
function viewDocument(docType, docId) {
    console.log(`查看${docType}文档详情:`, docId);
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    
    // 获取文档内容
    const endpointTemplate = docsEndpoint.GET_DOCUMENT || '/api/docs/get-document/{doc_type}/{file_id}';
    console.log('原始端点模板:', endpointTemplate);
    
    // 先替换占位符，再构建完整URL
    const endpoint = endpointTemplate
        .replace('{doc_type}', docType)
        .replace('{file_id}', docId);
    
    const apiUrl = baseUrl + endpoint;
    
    console.log('构建的API URL:', apiUrl);
    console.log('API_CONFIG.BASE_URL:', baseUrl);
    console.log('docType:', docType);
    console.log('docId:', docId);
    
    // 创建一个Promise数组，用于获取所有三种类型的文档
    const documentPromises = [];
    const docTypes = ['openapi', 'relation', 'scene'];
    
    docTypes.forEach(type => {
        const typeEndpoint = endpointTemplate
            .replace('{doc_type}', type)
            .replace('{file_id}', docId);
        const typeApiUrl = baseUrl + typeEndpoint;
        
        const promise = fetch(typeApiUrl)
            .then(response => response.json())
            .then(data => {
                return { type, data };
            })
            .catch(error => {
                console.error(`获取${type}文档内容失败:`, error);
                return { type, error };
            });
        
        documentPromises.push(promise);
    });
    
    // 等待所有文档请求完成
    Promise.all(documentPromises)
        .then(results => {
            // 使用第一个成功获取的文档来填充基本信息
            const firstSuccess = results.find(result => result.data && result.data.success);
            if (!firstSuccess) {
                throw new Error('无法获取任何文档信息');
            }
            
            const data = firstSuccess.data;
            
            // 填充文档详情模态框
            document.getElementById('docDetailId').textContent = data.data.file_id;
            
            document.getElementById('docDetailCreatedAt').textContent = new Date().toLocaleString(); // API没有返回创建时间，使用当前时间
            document.getElementById('docDetailApiCount').textContent = 1; // 单接口文档API数量固定为1
            
            // API端点列表已移除，不再显示
            
            // 处理所有文档类型的内容
            results.forEach(result => {
                const { type, data, error } = result;
                
                if (error) {
                    console.error(`处理${type}文档时出错:`, error);
                    return;
                }
                
                if (!data || !data.success) {
                    console.warn(`${type}文档获取失败或无数据`);
                    return;
                }
                
                // 设置文档名称到对应的显示区域
                let docNameElement = null;
                
                if (type === 'openapi') {
                    docNameElement = document.getElementById('openapiDocName');
                } else if (type === 'relation') {
                    docNameElement = document.getElementById('relationDocName');
                } else if (type === 'scene') {
                    docNameElement = document.getElementById('sceneDocName');
                }
                
                if (docNameElement) {
                    docNameElement.textContent = data.data.file_name || data.data.file_id;
                }
                
                try {
                    // 尝试解析为JSON，如果失败则直接显示原始内容
                    let formattedContent;
                    try {
                        formattedContent = JSON.stringify(JSON.parse(data.data.content), null, 2);
                        console.log(`${type}文档JSON解析成功`);
                    } catch (e) {
                        // 如果不是JSON格式，直接显示原始内容
                        formattedContent = data.data.content;
                        console.log(`${type}文档不是JSON格式，直接显示原始内容:`, e);
                    }
                    
                    // 根据文档类型设置到对应的编辑器
                    if (type === 'openapi') {
                        const openApiEditor = document.getElementById('openApiSpecEditor');
                        if (openApiEditor) {
                            openApiEditor.value = formattedContent;
                            window.openApiEditorContent = formattedContent;
                            console.log('OpenAPI文档内容已设置到编辑器，长度:', formattedContent.length);
                        }
                    } else if (type === 'relation') {
                        const relationEditor = document.getElementById('relationSpecEditor');
                        if (relationEditor) {
                            relationEditor.value = formattedContent;
                            window.relationEditorContent = formattedContent;
                            console.log('关联关系文档内容已设置到编辑器，长度:', formattedContent.length);
                        }
                    } else if (type === 'scene') {
                        const sceneEditor = document.getElementById('sceneSpecEditor');
                        if (sceneEditor) {
                            sceneEditor.value = formattedContent;
                            window.sceneEditorContent = formattedContent;
                            console.log('业务场景文档内容已设置到编辑器，长度:', formattedContent.length);
                        }
                    }
                } catch (error) {
                    console.error(`处理${type}文档内容时出错:`, error);
                    
                    // 出错时直接设置原始内容
                    if (type === 'openapi') {
                        const openApiEditor = document.getElementById('openApiSpecEditor');
                        if (openApiEditor) {
                            openApiEditor.value = data.data.content;
                            window.openApiEditorContent = data.data.content;
                        }
                    } else if (type === 'relation') {
                        const relationEditor = document.getElementById('relationSpecEditor');
                        if (relationEditor) {
                            relationEditor.value = data.data.content;
                            window.relationEditorContent = data.data.content;
                        }
                    } else if (type === 'scene') {
                        const sceneEditor = document.getElementById('sceneSpecEditor');
                        if (sceneEditor) {
                            sceneEditor.value = data.data.content;
                            window.sceneEditorContent = data.data.content;
                        }
                    }
                }
            });
            
            // 显示文档详情模态框
            const modal = new bootstrap.Modal(document.getElementById('documentDetailsModal'));
            modal.show();
            
            // 延迟切换到对应的选项卡，确保模态框已完全显示
            setTimeout(() => {
                // 根据原始请求的文档类型切换到对应的选项卡
                if (docType === 'openapi') {
                    document.getElementById('openapi-tab').click();
                } else if (docType === 'relation') {
                    document.getElementById('relation-tab').click();
                } else if (docType === 'scene') {
                    document.getElementById('scene-tab').click();
                }
                
                // 确保编辑器在选项卡切换后正确初始化
                setTimeout(() => {
                    // 初始化所有编辑器
                    if (typeof initOpenApiEditor === 'function') {
                        initOpenApiEditor();
                    }
                    if (typeof initRelationEditor === 'function') {
                        initRelationEditor();
                    }
                    if (typeof initSceneEditor === 'function') {
                        initSceneEditor();
                    }
                }, 200);
            }, 300);
        })
        .catch(error => {
            console.error('获取文档内容失败:', error);
            showSmartTestNotification('获取文档内容失败: ' + error.message, 'error');
        });
}

// 编辑三个文档
function editThreeDocuments(docId) {
    console.log(`编辑三个文档:`, docId);
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    
    // 获取三种文档类型的内容
    const documentTypes = ['openapi', 'relation', 'scene'];
    const documentPromises = [];
    
    documentTypes.forEach(docType => {
        const endpoint = (docsEndpoint.GET_DOCUMENT || '/api/docs/get-document/{doc_type}/{file_id}')
            .replace('{doc_type}', docType)
            .replace('{file_id}', docId);
        
        const apiUrl = baseUrl + endpoint;
        
        documentPromises.push(
            fetch(apiUrl)
                .then(response => response.json())
                .then(data => {
                    return { docType, data };
                })
                .catch(error => {
                    console.error(`获取${docType}文档失败:`, error);
                    return { docType, data: { success: false, error: error.message } };
                })
        );
    });
    
    Promise.all(documentPromises)
        .then(results => {
            // 显示三文档编辑模态框
            const modal = document.getElementById('threeDocEditModal');
            const modalTitle = document.getElementById('threeDocEditModalTitle');
            
            if (modal && modalTitle) {
                // 设置模态框标题
                modalTitle.textContent = `编辑文档: ${docId}`;
                
                // 填充文档基本信息
                const openapiDoc = results.find(r => r.docType === 'openapi').data;
                if (openapiDoc.success) {
                    document.getElementById('editDocId').textContent = openapiDoc.data.file_id;
                    document.getElementById('editDocCreatedTime').textContent = new Date(openapiDoc.data.created_at).toLocaleString();
                    
                    // 计算API数量
                    let apiCount = 0;
                    try {
                        // 尝试解析为JSON
                        const openApiSpec = JSON.parse(openapiDoc.data.content);
                        if (openApiSpec.paths) {
                            apiCount = Object.keys(openApiSpec.paths).length;
                        }
                    } catch (e) {
                        // 如果JSON解析失败，可能是YAML格式
                        console.log('OpenAPI文档可能是YAML格式，尝试其他方法计算API数量');
                        // 简单计算path条目数量（适用于YAML格式）
                        const content = openapiDoc.data.content;
                        const pathMatches = content.match(/paths:\s*\n((?:\s{2,}[^:\n]+:\s*\n(?:\s{4,}[^\n]*\n?)*)*)/);
                        if (pathMatches && pathMatches[1]) {
                            // 匹配路径行（以2个或更多空格开头，后跟非冒号字符，然后是冒号）
                            const pathLines = pathMatches[1].match(/^\s{2,}[^:\s]+:/gm);
                            if (pathLines) {
                                apiCount = pathLines.length;
                            }
                        }
                    }
                    document.getElementById('editDocApiCount').textContent = apiCount;
                }
                
                // 初始化全局变量
                if (!window.threeDocContents) {
                    window.threeDocContents = {
                        openapi: '',
                        relation: '',
                        scene: ''
                    };
                }
                
                // 填充各文档内容
                results.forEach(result => {
                    if (result.data.success) {
                        const { docType, data } = result;
                        const content = data.data.content || '';
                        
                        // 存储内容到全局变量
                        window.threeDocContents[docType] = content;
                        console.log(`已将${docType}文档内容存储到全局变量，长度: ${content.length}`);
                        
                        // 设置文档名称
                        const docNameElement = document.getElementById(`edit${docType.charAt(0).toUpperCase() + docType.slice(1)}DocName`);
                        if (docNameElement) {
                            docNameElement.textContent = data.data.file_name || data.data.file_id;
                        }
                        
                        // 设置文档内容到textarea（作为备用）
                        const editorElement = document.getElementById(`edit${docType.charAt(0).toUpperCase() + docType.slice(1)}SpecEditor`);
                        if (editorElement) {
                            editorElement.value = content;
                        }
                    }
                });
                
                // 打印全局变量内容，用于调试
                console.log('全局变量window.threeDocContents内容:', window.threeDocContents);
                
                // 设置保存按钮事件
                const saveBtn = document.getElementById('saveThreeDocumentsBtn');
                if (saveBtn) {
                    saveBtn.onclick = function() {
                        saveThreeDocuments(docId, results);
                    };
                }
                
                // 显示模态框
                const modalInstance = new bootstrap.Modal(modal);
                modalInstance.show();
            }
        })
        .catch(error => {
            console.error('获取文档内容失败:', error);
            showSmartTestNotification('获取文档内容失败: ' + error.message, 'error');
        });
}

// 保存三个文档
function saveThreeDocuments(docId, originalDocs) {
    console.log(`保存三个文档:`, docId);
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    
    const documentTypes = ['openapi', 'relation', 'scene'];
    const savePromises = [];
    
    documentTypes.forEach(docType => {
        // 获取编辑器内容
        let content = '';
        
        // 优先使用全局编辑器变量
        const editorVarName = `edit${docType.charAt(0).toUpperCase() + docType.slice(1)}SpecEditor`;
        if (window[editorVarName] && typeof window[editorVarName].getValue === 'function') {
            content = window[editorVarName].getValue();
            console.log(`从全局变量获取${docType}编辑器内容，长度:`, content.length);
        } else {
            // 备用方法：通过DOM元素获取编辑器内容
            const editorElement = document.getElementById(`edit${docType.charAt(0).toUpperCase() + docType.slice(1)}SpecEditor`);
            
            if (editorElement) {
                // 如果有CodeMirror编辑器，从编辑器获取内容
                const cmElement = editorElement.nextElementSibling;
                if (cmElement && cmElement.classList.contains('CodeMirror')) {
                    const cm = cmElement.CodeMirror;
                    if (cm && typeof cm.getValue === 'function') {
                        content = cm.getValue();
                    }
                } else {
                    // 否则从textarea获取内容
                    content = editorElement.value;
                }
            }
        }
        
        // 检查内容是否有变化
        const originalDoc = originalDocs.find(d => d.docType === docType);
        const originalContent = originalDoc && originalDoc.data.success ? originalDoc.data.data.content : '';
        
        // 只有内容有变化时才保存
        if (content !== originalContent) {
            const endpoint = (docsEndpoint.UPDATE_DOCUMENT || '/api/docs/update-document/{doc_type}/{file_id}')
                .replace('{doc_type}', docType)
                .replace('{file_id}', docId);
            
            const updateUrl = baseUrl + endpoint;
            
            savePromises.push(
                fetch(updateUrl, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: content
                    })
                })
                .then(response => response.json())
                .then(data => {
                    return { docType, success: data.success, message: data.message };
                })
                .catch(error => {
                    console.error(`保存${docType}文档失败:`, error);
                    return { docType, success: false, message: error.message };
                })
            );
        } else {
            // 内容没有变化，视为成功
            savePromises.push(Promise.resolve({ docType, success: true, message: '内容未变化' }));
        }
    });
    
    Promise.all(savePromises)
        .then(results => {
            const successCount = results.filter(r => r.success).length;
            const failCount = results.length - successCount;
            
            if (failCount === 0) {
                showSmartTestNotification('所有文档保存成功', 'success');
                // 关闭模态框
                const modal = document.getElementById('threeDocEditModal');
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
                // 刷新文档列表
                loadUploadedDocuments();
            } else {
                const failedDocs = results.filter(r => !r.success).map(r => r.docType).join(', ');
                showSmartTestNotification(`部分文档保存失败: ${failedDocs}`, 'error');
            }
        })
        .catch(error => {
            console.error('保存文档失败:', error);
            showSmartTestNotification('保存文档失败: ' + error.message, 'error');
        });
}

// 编辑文档
function editDocument(docType, docId) {
    console.log(`编辑${docType}文档:`, docId);
    
    // 获取文档内容
    // 安全获取配置并替换占位符，再构建完整URL
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const docsEndpoint = endpoints.DOCS || {};
    
    const endpoint = (docsEndpoint.GET_DOCUMENT || '/api/docs/get-document/{doc_type}/{file_id}')
        .replace('{doc_type}', docType)
        .replace('{file_id}', docId);
    
    const apiUrl = baseUrl + endpoint;
    
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 显示文档编辑模态框
                const modal = document.getElementById('documentEditModal');
                const modalTitle = document.getElementById('documentEditModalTitle');
                const modalContent = document.getElementById('documentEditContent');
                const saveBtn = document.getElementById('saveDocumentBtn');
                
                if (modal && modalTitle && modalContent && saveBtn) {
                    modalTitle.textContent = `编辑${docType}文档: ${data.data.file_name}`;
                    modalContent.value = data.data.content;
                    
                    // 设置保存按钮事件
                    saveBtn.onclick = function() {
                        const updatedContent = modalContent.value;
                        
                        // 更新文档内容
                        // 安全获取配置并替换占位符，再构建完整URL
                        const updateEndpoint = (docsEndpoint.UPDATE_DOCUMENT || '/api/docs/update-document/{doc_type}/{file_id}')
                            .replace('{doc_type}', docType)
                            .replace('{file_id}', docId);
                        
                        const updateUrl = baseUrl + updateEndpoint;
                        
                        fetch(updateUrl, {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                content: updatedContent
                            })
                        })
                        .then(response => response.json())
                        .then(updateData => {
                            if (updateData.success) {
                                showSmartTestNotification('文档更新成功', 'success');
                                // 关闭模态框
                                const modalInstance = bootstrap.Modal.getInstance(modal);
                                modalInstance.hide();
                                // 刷新文档列表
                                loadUploadedDocuments();
                            } else {
                                showSmartTestNotification('文档更新失败: ' + updateData.message, 'error');
                            }
                        })
                        .catch(error => {
                            console.error('文档更新失败:', error);
                            showSmartTestNotification('文档更新失败: ' + error.message, 'error');
                        });
                    };
                    
                    // 显示模态框
                    const modalInstance = new bootstrap.Modal(modal);
                    modalInstance.show();
                }
            } else {
                showSmartTestNotification('获取文档内容失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('获取文档内容失败:', error);
            showSmartTestNotification('获取文档内容失败: ' + error.message, 'error');
        });
}

// 删除文档
function deleteDocument(docType, docId) {
    console.log(`删除${docType}文档:`, docId);
    
    if (confirm(`确定要删除这个${docType}文档吗？此操作不可恢复。`)) {
        const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
        const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
        const docsEndpoint = endpoints.DOCS || {};
        
        // 调用删除API
        // 先替换占位符，再构建完整URL
        const endpoint = (docsEndpoint.DELETE_DOCUMENT || '/api/docs/delete-document/{doc_type}/{file_id}')
            .replace('{doc_type}', docType)
            .replace('{file_id}', docId);
        
        const apiUrl = baseUrl + endpoint;
        
        fetch(apiUrl, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSmartTestNotification(`${docType}文档删除成功`, 'success');
                // 刷新文档列表
                loadUploadedDocuments();
            } else {
                showSmartTestNotification(`删除${docType}文档失败: ` + data.message, 'error');
            }
        })
        .catch(error => {
            console.error(`删除${docType}文档失败:`, error);
            showSmartTestNotification(`删除${docType}文档失败: ` + error.message, 'error');
        });
    }
}

// 生成测试用例
function generateTestCases(taskId) {
    if (!taskId) {
        showSmartTestNotification('文档ID不能为空', 'error');
        return;
    }
    
    showLoading('正在生成测试用例...');
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const apiUrl = baseUrl + '/api/generate_test_cases';
    
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            file_id: taskId
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showSmartTestNotification('测试用例生成成功', 'success');
            // 刷新测试用例列表
            loadTestCases();
            updateTestCasesStats();
        } else {
            showSmartTestNotification('测试用例生成失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('生成测试用例失败:', error);
        showSmartTestNotification('生成测试用例失败: ' + error.message, 'error');
    });
}

// 执行测试用例
function executeTestCases(taskId) {
    if (!taskId) {
        showSmartTestNotification('文档ID不能为空', 'error');
        return;
    }
    
    showLoading('正在执行测试用例...');
    
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const apiUrl = baseUrl + '/api/execute_test_cases';
    
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            file_id: taskId
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showSmartTestNotification('测试用例执行成功', 'success');
            // 刷新测试用例列表
            loadTestCases();
            updateTestCasesStats();
        } else {
            showSmartTestNotification('测试用例执行失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('执行测试用例失败:', error);
        showSmartTestNotification('执行测试用例失败: ' + error.message, 'error');
    });
}

// 初始化文档标签页切换功能
function initDocumentTabs() {
    // 获取所有标签页按钮和内容区域 - 使用正确的ID
    const openApiTab = document.getElementById('openapi-docs-tab');
    const multiApiTab = document.getElementById('multiapi-docs-tab');
    
    const openApiContent = document.getElementById('openapi-docs-content');
    const multiApiContent = document.getElementById('multiapi-docs-content');
    
    // 如果元素不存在，直接返回
    if (!openApiTab || !multiApiTab || !openApiContent || !multiApiContent) {
        return;
    }
    
    // 设置默认显示OpenAPI文档标签页
    openApiTab.classList.add('active');
    openApiContent.classList.add('active', 'show');
    multiApiContent.classList.remove('active', 'show');
    
    // 添加标签页切换事件监听
    openApiTab.addEventListener('click', function(e) {
        e.preventDefault();
        
        // 切换标签页状态
        openApiTab.classList.add('active');
        multiApiTab.classList.remove('active');
        
        // 切换内容显示
        openApiContent.classList.add('active', 'show');
        multiApiContent.classList.remove('active', 'show');
    });
    
    multiApiTab.addEventListener('click', function(e) {
        e.preventDefault();
        
        // 切换标签页状态
        multiApiTab.classList.add('active');
        openApiTab.classList.remove('active');
        
        // 切换内容显示
        multiApiContent.classList.add('active', 'show');
        openApiContent.classList.remove('active', 'show');
        
        // 加载多接口文档数据
        loadMultiApiDocuments();
    });
}

// 加载多接口文档列表
function loadMultiApiDocuments() {
    console.log('开始加载多接口文档列表');
    
    // 显示加载状态
    const multiApiTableBody = document.getElementById('multiApiDocsTableBody');
    const noMultiApiDocsMessage = document.getElementById('noMultiApiDocsMessage');
    
    if (multiApiTableBody) {
        multiApiTableBody.innerHTML = '<tr><td colspan="5" class="text-center"><div class="spinner-border spinner-border-sm me-2" role="status"></div>正在加载多接口文档...</td></tr>';
    }
    
    // 使用直接拼接URL的方式，避免undefined问题
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const apiUrl = baseUrl + '/api/multiapi/documents';
    console.log('多接口文档API URL:', apiUrl);
    
    return fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            console.log('获取多接口文档列表响应:', data);
            
            // 清空加载状态
            if (multiApiTableBody) {
                multiApiTableBody.innerHTML = '';
            }
            
            // 处理响应数据
            // 后端返回格式: { success: true, data: { documents: [...], count: N } }
            const documents = data.success && data.data && data.data.documents ? data.data.documents : [];
            
            if (documents.length === 0) {
                // 显示无文档消息
                if (noMultiApiDocsMessage) {
                    noMultiApiDocsMessage.style.display = 'block';
                }
                console.log('没有多接口文档');
            } else {
                // 隐藏无文档消息
                if (noMultiApiDocsMessage) {
                    noMultiApiDocsMessage.style.display = 'none';
                }
                
                // 保存到全局变量，转换格式以匹配前端期望
                multiApiDocuments = documents.map(doc => ({
                    file_id: doc.file_id,  // 保留原始file_id
                    document_id: doc.file_id,  // 将file_id映射为document_id
                    document_name: doc.file_name,
                    api_count: doc.api_count,
                    upload_time: doc.upload_time,
                    status: doc.status,
                    editable: doc.editable
                }));
                
                // 添加文档到表格
                documents.forEach(doc => {
                    console.log('多接口文档数据:', doc);
                    const row = document.createElement('tr');
                    
                    // 文档ID
                    const idCell = document.createElement('td');
                    idCell.textContent = doc.file_id || '未知ID';
                    row.appendChild(idCell);
                    
                    // 文档名称
                    const nameCell = document.createElement('td');
                    nameCell.textContent = doc.file_name || '未知名称';
                    row.appendChild(nameCell);
                    
                    // 接口数量
                    const apiCountCell = document.createElement('td');
                    apiCountCell.textContent = doc.api_count || 0;
                    row.appendChild(apiCountCell);
                    
                    // 上传时间
                    const uploadTimeCell = document.createElement('td');
                    if (doc.upload_time) {
                        const uploadDate = new Date(doc.upload_time);
                        uploadTimeCell.textContent = uploadDate.toLocaleString();
                    } else {
                        uploadTimeCell.textContent = '未知时间';
                    }
                    row.appendChild(uploadTimeCell);
                    
                    // 操作
                    const actionsCell = document.createElement('td');
                    
                    const viewBtn = document.createElement('button');
                    viewBtn.className = 'btn btn-sm btn-outline-primary me-1';
                    viewBtn.innerHTML = '<i class="fas fa-eye"></i> 查看';
                    viewBtn.addEventListener('click', () => {
                        viewMultiApiDocument(doc.file_id);
                    });
                    
                    const generateBtn = document.createElement('button');
                    generateBtn.className = 'btn btn-sm btn-outline-success me-1';
                    generateBtn.innerHTML = '<i class="fas fa-code"></i> 生成测试用例';
                    generateBtn.addEventListener('click', () => {
                        generateMultiApiTestCases(doc.file_id);
                    });
                    
                    const executeBtn = document.createElement('button');
                    executeBtn.className = 'btn btn-sm btn-outline-info me-1';
                    executeBtn.innerHTML = '<i class="fas fa-play"></i> 执行测试用例';
                    executeBtn.addEventListener('click', () => {
                        executeMultiApiTestCases(doc.file_id);
                    });
                    
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'btn btn-sm btn-outline-danger';
                    deleteBtn.innerHTML = '<i class="fas fa-trash"></i> 删除';
                    deleteBtn.addEventListener('click', () => {
                        deleteMultiApiDocument(doc.file_id);
                    });
                    
                    actionsCell.appendChild(viewBtn);
                    actionsCell.appendChild(generateBtn);
                    actionsCell.appendChild(executeBtn);
                    actionsCell.appendChild(deleteBtn);
                    row.appendChild(actionsCell);
                    
                    multiApiTableBody.appendChild(row);
                });
            }
            
            return multiApiDocuments; // 返回加载的数据
        })
        .catch(error => {
            console.error('加载多接口文档失败:', error);
            
            // 显示错误信息
            if (multiApiTableBody) {
                multiApiTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">加载多接口文档失败: ' + error.message + '</td></tr>';
            }
            
            throw error; // 重新抛出错误，以便调用者可以处理
        });
}

// 直接操作DOM显示模态框的函数
function showModalDirectly(modal) {
    try {
        console.log('尝试直接操作DOM显示模态框');
        
        // 确保模态框有正确的类和样式
        modal.classList.add('show');
        modal.style.display = 'block';
        modal.style.visibility = 'visible';
        modal.style.opacity = '1';
        
        // 确保body有modal-open类
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
        
        // 创建或更新backdrop
        let backdrop = document.getElementById('multiApiDocDetailModal-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            backdrop.id = 'multiApiDocDetailModal-backdrop';
            document.body.appendChild(backdrop);
        } else {
            backdrop.classList.add('show');
        }
        
        // 确保backdrop在最上层
        backdrop.style.zIndex = '1055';
        modal.style.zIndex = '1056';
        
        // 清除旧的事件监听器，避免重复添加
        const closeButtons = modal.querySelectorAll('[data-bs-dismiss="modal"]');
        closeButtons.forEach(button => {
            // 克隆按钮以移除所有事件监听器
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
        });
        
        // 重新获取关闭按钮并添加事件监听器
        const newCloseButtons = modal.querySelectorAll('[data-bs-dismiss="modal"]');
        newCloseButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('点击关闭按钮，关闭模态框');
                hideModalDirectly(modal);
            });
        });
        
        // 移除旧的backdrop点击事件监听器
        const newBackdrop = document.getElementById('multiApiDocDetailModal-backdrop');
        const newBackdropClone = newBackdrop.cloneNode(true);
        newBackdrop.parentNode.replaceChild(newBackdropClone, newBackdrop);
        
        // 添加新的backdrop点击事件监听器
        document.getElementById('multiApiDocDetailModal-backdrop').addEventListener('click', function() {
            console.log('点击backdrop，关闭模态框');
            hideModalDirectly(modal);
        });
        
        // 添加ESC键关闭模态框
        const escHandler = function(e) {
            if (e.key === 'Escape') {
                console.log('按下ESC键，关闭模态框');
                hideModalDirectly(modal);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
        
        console.log('直接操作DOM显示模态框成功');
    } catch (domError) {
        console.error('直接操作DOM显示模态框也失败:', domError);
        showSmartTestNotification('无法显示文档详情，请刷新页面重试', 'error');
    }
}

// 直接操作DOM隐藏模态框的函数
function hideModalDirectly(modal) {
    try {
        // 移除模态框的显示类和样式
        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
        modal.style.opacity = '0';
        
        // 恢复body的样式
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        
        // 移除backdrop
        const backdrop = document.getElementById('multiApiDocDetailModal-backdrop');
        if (backdrop) {
            backdrop.remove();
        }
        
        console.log('直接操作DOM隐藏模态框成功');
    } catch (error) {
        console.error('隐藏模态框失败:', error);
    }
}

// 获取HTTP方法对应的颜色
function getMethodColor(method) {
    const methodColors = {
        'get': 'success',
        'post': 'primary',
        'put': 'warning',
        'delete': 'danger',
        'patch': 'info',
        'head': 'secondary',
        'options': 'secondary'
    };
    return methodColors[method.toLowerCase()] || 'secondary';
}

// 查看多接口文档详情
function viewMultiApiDocument(documentId) {
    console.log('查看多接口文档详情:', documentId);
    console.log('当前multiApiDocuments状态:', multiApiDocuments);
    
    // 检查multiApiDocuments是否已加载
    if (!multiApiDocuments || multiApiDocuments.length === 0) {
        console.log('multiApiDocuments未加载，尝试加载...');
        loadMultiApiDocuments().then(() => {
            console.log('multiApiDocuments加载完成，重新调用viewMultiApiDocument');
            viewMultiApiDocument(documentId);
        }).catch(error => {
            console.error('加载multiApiDocuments失败:', error);
            showSmartTestNotification('加载多接口文档列表失败: ' + error.message, 'error');
        });
        return;
    }
    
    // 确保多接口文档标签页是激活状态
    const multiApiTab = document.getElementById('multiapi-docs-tab');
    if (multiApiTab && !multiApiTab.classList.contains('active')) {
        console.log('激活多接口文档标签页');
        multiApiTab.click();
    }
    
    // 检查模态框是否存在
    const modal = document.getElementById('multiApiDocDetailModal');
    console.log('模态框检查:', modal);
    
    if (!modal) {
        console.error('未找到多接口文档详情模态框，尝试重新加载');
        showSmartTestNotification('正在重新加载页面，请稍候...', 'info');
        
        // 尝试重新加载页面
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        return;
    }
    
    // 使用直接拼接URL的方式，避免undefined问题
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const docUrl = `${baseUrl}/api/multiapi/document/${documentId}`;
    const relationsUrl = `${baseUrl}/api/multiapi/relation/${documentId}`;
    
    console.log('多接口文档详情API URL:', docUrl);
    console.log('多接口文档关联关系API URL:', relationsUrl);
    
    // 获取文档内容和关联关系
    Promise.all([
        fetch(docUrl).then(response => response.json()),
        fetch(relationsUrl).then(response => response.json())
    ])
    .then(([docData, relationsData]) => {
        console.log('文档数据:', docData);
        console.log('关联关系数据:', relationsData);
        
        // 查找文档信息
        let globalDoc = null;
        
        // 先尝试通过file_id查找
        globalDoc = multiApiDocuments.find(doc => doc.file_id === documentId);
        
        // 如果没找到，再尝试通过document_id查找
        if (!globalDoc) {
            globalDoc = multiApiDocuments.find(doc => doc.document_id === documentId);
        }
        
        console.log('找到的全局文档信息:', globalDoc);
        
        // 填充文档基本信息
        const docIdElement = document.getElementById('multiApiDocId');
        const docNameElement = document.getElementById('multiApiDocName');
        const docApiCountElement = document.getElementById('multiApiDocApiCount');
        const docUploadTimeElement = document.getElementById('multiApiDocUploadTime');
        
        // 同时填充详情显示区域的元素
        const detailDocIdElement = document.getElementById('detailMultiApiDocId');
        const detailDocNameElement = document.getElementById('detailMultiApiDocName');
        const detailDocUploadTimeElement = document.getElementById('detailMultiApiDocUploadTime');
        
        console.log('DOM元素检查结果:');
        console.log('docIdElement:', docIdElement);
        console.log('docNameElement:', docNameElement);
        console.log('docApiCountElement:', docApiCountElement);
        console.log('docUploadTimeElement:', docUploadTimeElement);
        console.log('detailDocIdElement:', detailDocIdElement);
        console.log('detailDocNameElement:', detailDocNameElement);
        console.log('detailDocUploadTimeElement:', detailDocUploadTimeElement);
        
        // 填充多接口文档解析部分的元素
        if (docIdElement) {
            docIdElement.textContent = documentId;
        }
        
        if (docNameElement) {
            docNameElement.textContent = globalDoc ? globalDoc.document_name : '未知文档';
        }
        
        if (docApiCountElement) {
            docApiCountElement.textContent = globalDoc ? globalDoc.api_count || 0 : 0;
        }
        
        if (docUploadTimeElement) {
            if (globalDoc && globalDoc.upload_time) {
                const uploadDate = new Date(globalDoc.upload_time);
                docUploadTimeElement.textContent = uploadDate.toLocaleString();
            } else {
                docUploadTimeElement.textContent = '未知时间';
            }
        } else {
            console.error('未找到上传时间元素 multiApiDocUploadTime');
        }
        
        // 填充详情显示区域的元素
        if (detailDocIdElement) {
            detailDocIdElement.textContent = documentId;
        }
        
        if (detailDocNameElement) {
            detailDocNameElement.textContent = globalDoc ? globalDoc.document_name : '未知文档';
        }
        
        if (detailDocUploadTimeElement) {
            if (globalDoc && globalDoc.upload_time) {
                const uploadDate = new Date(globalDoc.upload_time);
                detailDocUploadTimeElement.textContent = uploadDate.toLocaleString();
            } else {
                detailDocUploadTimeElement.textContent = '未知时间';
            }
        } else {
            console.error('未找到上传时间元素 detailMultiApiDocUploadTime');
        }
        
        // 解析API内容
        let apiContent = {};
        try {
            if (docData.success && docData.data && docData.data.content) {
                const contentStr = docData.data.content;
                console.log('原始API内容:', contentStr.substring(0, 200));
                
                // 尝试解析为YAML格式
                try {
                    apiContent = jsyaml.load(contentStr);
                    console.log('YAML解析成功，API内容:', apiContent);
                    console.log('API paths:', apiContent.paths);
                } catch (yamlError) {
                    console.warn('YAML解析失败，尝试JSON解析:', yamlError);
                    // 如果YAML解析失败，尝试JSON解析
                    apiContent = JSON.parse(contentStr);
                    console.log('JSON解析成功，API内容:', apiContent);
                    console.log('API paths:', apiContent.paths);
                }
            } else {
                console.log('文档数据结构:', docData);
            }
        } catch (e) {
            console.error('解析API内容失败:', e);
        }
        
        // 显示API列表
        const apiListContainer = document.getElementById('multiApiDocApiList');
        const detailApiListContainer = document.getElementById('multiApiEndpointsList');
        console.log('API列表容器:', apiListContainer);
        console.log('详情API列表容器:', detailApiListContainer);
        
        // 清空两个容器
        if (apiListContainer) {
            apiListContainer.innerHTML = '';
        }
        if (detailApiListContainer) {
            detailApiListContainer.innerHTML = '';
        }
        
        if (apiContent.paths) {
            console.log('开始渲染API列表，paths数量:', Object.keys(apiContent.paths).length);
            Object.keys(apiContent.paths).forEach(path => {
                const methods = apiContent.paths[path];
                Object.keys(methods).forEach(method => {
                    const methodInfo = methods[method];
                    
                    // 为模态框中的API列表创建元素
                    if (apiListContainer) {
                        const apiItem = document.createElement('div');
                        apiItem.className = 'api-item mb-2 p-2 border rounded';
                        
                        const methodBadge = document.createElement('span');
                        methodBadge.className = `badge bg-${getMethodColor(method)} me-2`;
                        methodBadge.textContent = method.toUpperCase();
                        
                        const pathText = document.createElement('span');
                        pathText.textContent = path;
                        
                        apiItem.appendChild(methodBadge);
                        apiItem.appendChild(pathText);
                        
                        if (methodInfo.summary) {
                            const summaryText = document.createElement('div');
                            summaryText.className = 'text-muted small mt-1';
                            summaryText.textContent = methodInfo.summary;
                            apiItem.appendChild(summaryText);
                        }
                        
                        apiListContainer.appendChild(apiItem);
                    }
                    
                    // 为详情显示区域的API列表创建表格行
                    if (detailApiListContainer) {
                        const row = document.createElement('tr');
                        
                        const methodCell = document.createElement('td');
                        const methodBadge = document.createElement('span');
                        methodBadge.className = `badge bg-${getMethodColor(method)}`;
                        methodBadge.textContent = method.toUpperCase();
                        methodCell.appendChild(methodBadge);
                        
                        const pathCell = document.createElement('td');
                        pathCell.textContent = path;
                        
                        const descCell = document.createElement('td');
                        descCell.textContent = methodInfo.summary || '';
                        
                        const actionCell = document.createElement('td');
                        const viewBtn = document.createElement('button');
                        viewBtn.className = 'btn btn-sm btn-outline-primary';
                        viewBtn.textContent = '查看';
                        viewBtn.onclick = () => {
                            // 这里可以添加查看API详情的逻辑
                            console.log('查看API详情:', method, path);
                        };
                        actionCell.appendChild(viewBtn);
                        
                        row.appendChild(methodCell);
                        row.appendChild(pathCell);
                        row.appendChild(descCell);
                        row.appendChild(actionCell);
                        
                        detailApiListContainer.appendChild(row);
                    }
                });
            });
            
            console.log('API列表渲染完成，模态框子元素数量:', apiListContainer ? apiListContainer.children.length : 0);
            console.log('API列表渲染完成，详情区域子元素数量:', detailApiListContainer ? detailApiListContainer.children.length : 0);
        } else {
            console.log('没有找到API paths，显示空提示');
            if (apiListContainer) {
                apiListContainer.innerHTML = '<p class="text-muted">暂无API内容</p>';
            }
            if (detailApiListContainer) {
                const emptyRow = document.createElement('tr');
                const emptyCell = document.createElement('td');
                emptyCell.colSpan = 4;
                emptyCell.className = 'text-center text-muted';
                emptyCell.textContent = '暂无API内容';
                emptyRow.appendChild(emptyCell);
                detailApiListContainer.appendChild(emptyRow);
            }
        }
        
        if (!apiListContainer) {
            console.error('未找到API列表容器 multiApiDocApiList');
        }
        if (!detailApiListContainer) {
            console.error('未找到详情API列表容器 multiApiEndpointsList');
        }
        
        // 显示关联关系
        const relationsListContainer = document.getElementById('multiApiDocRelationList');
        console.log('关联关系容器:', relationsListContainer);
        if (relationsListContainer) {
            relationsListContainer.innerHTML = '';
            
            // 适配后端返回的数据结构
            let relationsArray = [];
            if (relationsData.success && relationsData.data) {
                if (relationsData.data.relation_data && relationsData.data.relation_data.related_pairs) {
                    // 关联关系在related_pairs数组中
                    relationsArray = relationsData.data.relation_data.related_pairs;
                } else if (relationsData.data.relation_data && relationsData.data.relation_data.relations) {
                    // 兼容relations数组的情况
                    relationsArray = relationsData.data.relation_data.relations;
                } else if (Array.isArray(relationsData.data)) {
                    // 如果data直接是数组
                    relationsArray = relationsData.data;
                }
            }
            
            if (relationsArray.length > 0) {
                console.log('开始渲染关联关系，数量:', relationsArray.length);
                relationsArray.forEach(relation => {
                    const relationItem = document.createElement('div');
                    relationItem.className = 'relation-item mb-2 p-2 border rounded';
                    
                    const sourceApi = document.createElement('div');
                    sourceApi.innerHTML = `<strong>源API:</strong> ${relation.source_api_path}`;
                    
                    const targetApi = document.createElement('div');
                    targetApi.innerHTML = `<strong>目标API:</strong> ${relation.target_api_path}`;
                    
                    const relationDesc = document.createElement('div');
                    relationDesc.innerHTML = `<strong>关系描述:</strong> ${relation.relation_desc || '无描述'}`;
                    
                    relationItem.appendChild(sourceApi);
                    relationItem.appendChild(targetApi);
                    relationItem.appendChild(relationDesc);
                    
                    // 如果有关系参数，显示参数详情
                    if (relation.relation_params && relation.relation_params.length > 0) {
                        const paramsTitle = document.createElement('div');
                        paramsTitle.className = 'mt-2 mb-1';
                        paramsTitle.innerHTML = '<strong>关系参数:</strong>';
                        relationItem.appendChild(paramsTitle);
                        
                        const paramsList = document.createElement('ul');
                        paramsList.className = 'mb-0 ps-3';
                        
                        relation.relation_params.forEach(param => {
                            const paramItem = document.createElement('li');
                            paramItem.className = 'small';
                            paramItem.innerHTML = `${param.source_param} → ${param.target_param} (${param.param_location}, ${param.relation_type})`;
                            paramsList.appendChild(paramItem);
                        });
                        
                        relationItem.appendChild(paramsList);
                    }
                    
                    relationsListContainer.appendChild(relationItem);
                });
                
                console.log('关联关系渲染完成，子元素数量:', relationsListContainer.children.length);
                
                // 如果有关联关系，激活关联关系选项卡
                const relationTab = document.getElementById('relation-list-tab');
                if (relationTab) {
                    const tab = new bootstrap.Tab(relationTab);
                    tab.show();
                }
            } else {
                console.log('没有关联关系数据，显示空提示');
                console.log('关联关系数据结构:', relationsData);
                relationsListContainer.innerHTML = '<p class="text-muted">暂无关联关系</p>';
            }
        } else {
            console.error('未找到关联关系容器 multiApiDocRelationList');
        }
        
        // 同时填充详情区域的关联关系（如果存在）
        // 注意：详情区域可能没有关联关系显示区域，所以这里只是尝试获取
        const detailRelationsContainer = document.getElementById('detailMultiApiDocRelationList');
        if (detailRelationsContainer) {
            console.log('详情区域关联关系容器:', detailRelationsContainer);
            detailRelationsContainer.innerHTML = '';
            
            // 适配后端返回的数据结构
            let relationsArray = [];
            if (relationsData.success && relationsData.data) {
                if (relationsData.data.relation_data && relationsData.data.relation_data.related_pairs) {
                    relationsArray = relationsData.data.relation_data.related_pairs;
                } else if (relationsData.data.relation_data && relationsData.data.relation_data.relations) {
                    relationsArray = relationsData.data.relation_data.relations;
                } else if (Array.isArray(relationsData.data)) {
                    relationsArray = relationsData.data;
                }
            }
            
            if (relationsArray.length > 0) {
                console.log('开始渲染详情区域关联关系，数量:', relationsArray.length);
                relationsArray.forEach(relation => {
                    const relationItem = document.createElement('div');
                    relationItem.className = 'relation-item mb-2 p-2 border rounded';
                    
                    const sourceApi = document.createElement('div');
                    sourceApi.innerHTML = `<strong>源API:</strong> ${relation.source_api_path}`;
                    
                    const targetApi = document.createElement('div');
                    targetApi.innerHTML = `<strong>目标API:</strong> ${relation.target_api_path}`;
                    
                    const relationDesc = document.createElement('div');
                    relationDesc.innerHTML = `<strong>关系描述:</strong> ${relation.relation_desc || '无描述'}`;
                    
                    relationItem.appendChild(sourceApi);
                    relationItem.appendChild(targetApi);
                    relationItem.appendChild(relationDesc);
                    
                    // 如果有关系参数，显示参数详情
                    if (relation.relation_params && relation.relation_params.length > 0) {
                        const paramsTitle = document.createElement('div');
                        paramsTitle.className = 'mt-2 mb-1';
                        paramsTitle.innerHTML = '<strong>关系参数:</strong>';
                        relationItem.appendChild(paramsTitle);
                        
                        const paramsList = document.createElement('ul');
                        paramsList.className = 'mb-0 ps-3';
                        
                        relation.relation_params.forEach(param => {
                            const paramItem = document.createElement('li');
                            paramItem.className = 'small';
                            paramItem.innerHTML = `${param.source_param} → ${param.target_param} (${param.param_location}, ${param.relation_type})`;
                            paramsList.appendChild(paramItem);
                        });
                        
                        relationItem.appendChild(paramsList);
                    }
                    
                    detailRelationsContainer.appendChild(relationItem);
                });
                
                console.log('详情区域关联关系渲染完成，子元素数量:', detailRelationsContainer.children.length);
            } else {
                console.log('没有关联关系数据，显示空提示');
                detailRelationsContainer.innerHTML = '<p class="text-muted">暂无关联关系</p>';
            }
        }
        
        // 显示模态框
        console.log('准备显示模态框');
        const modalElement = document.getElementById('multiApiDocDetailModal');
        if (modalElement) {
            showModalDirectly(modalElement);
        } else {
            console.error('未找到模态框元素');
            showSmartTestNotification('无法显示文档详情，请刷新页面重试', 'error');
            return;
        }
        
        // 验证模态框是否成功显示
        setTimeout(() => {
            const modalElement = document.getElementById('multiApiDocDetailModal');
            if (modalElement) {
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) {
                    console.log('模态框实例存在');
                } else {
                    console.log('模态框实例不存在，尝试使用Bootstrap Modal');
                    const modal = new bootstrap.Modal(modalElement);
                    modal.show();
                }
            } else {
                console.error('模态框元素不存在');
            }
        }, 100);
    })
    .catch(error => {
        console.error('获取多接口文档详情失败:', error);
        showSmartTestNotification('获取多接口文档详情失败: ' + error.message, 'error');
    });
}

// 删除多接口文档
function deleteMultiApiDocument(documentId) {
    if (!confirm('确定要删除这个多接口文档吗？此操作不可恢复。')) {
        return;
    }
    
    console.log('删除多接口文档:', documentId);
    
    // 调用删除API
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const apiUrl = baseUrl + '/api/multiapi/document/' + documentId;
    
    fetch(apiUrl, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSmartTestNotification('多接口文档删除成功', 'success');
            // 刷新文档列表
            loadMultiApiDocuments();
        } else {
            showSmartTestNotification('删除多接口文档失败: ' + (data.error || data.message), 'error');
        }
    })
    .catch(error => {
        console.error('删除多接口文档失败:', error);
        showSmartTestNotification('删除多接口文档失败: ' + error.message, 'error');
    });
}

// 生成多接口文档的测试用例
function generateMultiApiTestCases(documentId) {
    console.log('为多接口文档生成测试用例:', documentId);
    
    // 调用后端API生成测试用例
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const apiUrl = `${baseUrl}/api/multiapi/testcases/generate/${documentId}`;
    
    showLoading('正在生成多接口文档测试用例...');
    
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            showSmartTestNotification('多接口文档测试用例生成成功', 'success');
            // 刷新测试用例列表
            loadTestCases();
        } else {
            showSmartTestNotification('生成测试用例失败: ' + (data.error || data.message), 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('生成测试用例失败:', error);
        showSmartTestNotification('生成测试用例失败: ' + error.message, 'error');
    });
}

// 执行多接口文档的测试用例
function executeMultiApiTestCases(documentId) {
    console.log('执行多接口文档测试用例:', documentId);
    
    // 调用后端API执行测试用例
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const apiUrl = `${baseUrl}/api/multiapi/testcases/execute/${documentId}`;
    
    showLoading('正在执行多接口文档测试用例...');
    
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            showSmartTestNotification('多接口文档测试用例执行成功', 'success');
            // 刷新测试报告列表
            loadTestReports();
        } else {
            showSmartTestNotification('执行测试用例失败: ' + (data.error || data.message), 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('执行测试用例失败:', error);
        showSmartTestNotification('执行测试用例失败: ' + error.message, 'error');
    });
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

// 初始化测试工作流
function initTestWorkflow() {
    // 文档类型选择
    const workflowDocTypeSelect = document.getElementById('workflowDocTypeSelect');
    if (workflowDocTypeSelect) {
        workflowDocTypeSelect.addEventListener('change', function() {
            const docType = this.value;
            if (docType) {
                // 根据文档类型加载对应的文档列表
                loadWorkflowDocuments(docType);
            } else {
                // 清空文档列表
                clearWorkflowDocument();
            }
        });
    }
    
    // 更换文档按钮
    const workflowChangeDocBtn = document.getElementById('workflowChangeDocBtn');
    if (workflowChangeDocBtn) {
        workflowChangeDocBtn.addEventListener('click', function() {
            const docType = document.getElementById('workflowDocTypeSelect').value;
            if (docType) {
                showWorkflowDocumentSelector(docType);
            } else {
                showSmartTestNotification('请先选择文档类型', 'warning');
            }
        });
    }
}



// 加载工作流文档
function loadWorkflowDocuments(docType) {
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    let apiUrl;
    
    if (docType === 'single') {
        apiUrl = baseUrl + '/api/docs/by-type/single';
    } else if (docType === 'multi') {
        apiUrl = baseUrl + '/api/docs/by-type/multi';
    } else {
        console.error('未知的文档类型:', docType);
        return;
    }
    
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data.length > 0) {
                // 默认选择第一个文档
                const doc = data.data[0];
                updateWorkflowDocument(doc, docType);
            } else {
                showSmartTestNotification(`没有找到${docType === 'single' ? '单接口' : '多接口'}文档`, 'warning');
                clearWorkflowDocument();
            }
        })
        .catch(error => {
            console.error('加载文档失败:', error);
            showSmartTestNotification('加载文档失败: ' + error.message, 'error');
        });
}

// 更新工作流文档显示
function updateWorkflowDocument(doc, docType) {
    const docNameElement = document.querySelector('.workflow-step .card-body h6');
    const docInfoElement = document.querySelector('.workflow-step .card-body small.text-muted');
    
    if (docNameElement) {
        if (docType === 'single') {
            // 单接口文档使用文档ID
            docNameElement.textContent = `${doc.id || doc.file_id}`;
        } else {
            // 多接口文档使用文档名称
            docNameElement.textContent = doc.file_name || doc.name || '未命名文档';
        }
    }
    
    if (docInfoElement) {
        if (docType === 'single') {
            // 单接口文档不显示额外信息，因为文档名称已经是ID
            docInfoElement.textContent = '';
        } else if (docType === 'multi') {
            const endpointCount = doc.endpoint_count || doc.endpoints?.length || 0;
            docInfoElement.textContent = `多接口文档，包含${endpointCount}个API端点`;
        }
    }
    
    // 显示更换文档按钮
    const changeDocBtn = document.getElementById('workflowChangeDocBtn');
    if (changeDocBtn) {
        changeDocBtn.style.display = 'inline-block';
    }
    
    // 显示状态徽章
    const statusBadge = document.getElementById('workflowDocStatusBadge');
    if (statusBadge) {
        statusBadge.style.display = 'inline-block';
        statusBadge.classList.remove('bg-secondary');
        statusBadge.classList.add('bg-success');
    }
    
    // 保存当前文档信息到全局变量
    window.workflowCurrentDoc = {
        id: doc.id || doc.file_id,
        name: doc.file_name || doc.name,
        type: docType
    };
    
    // 如果文档类型是多接口，加载文档详情
    if (docType === 'multi') {
        loadMultiApiDocumentDetails(doc.id || doc.file_id);
    }
}

// 清空工作流文档显示
function clearWorkflowDocument() {
    const docNameElement = document.querySelector('.workflow-step .card-body h6');
    const docInfoElement = document.querySelector('.workflow-step .card-body small.text-muted');
    
    if (docNameElement) {
        docNameElement.textContent = '未选择文档';
    }
    
    if (docInfoElement) {
        docInfoElement.textContent = '请选择文档类型';
    }
    
    // 隐藏更换文档按钮
    const changeDocBtn = document.getElementById('workflowChangeDocBtn');
    if (changeDocBtn) {
        changeDocBtn.style.display = 'none';
    }
    
    // 隐藏状态徽章
    const statusBadge = document.getElementById('workflowDocStatusBadge');
    if (statusBadge) {
        statusBadge.style.display = 'none';
        statusBadge.classList.remove('bg-success');
        statusBadge.classList.add('bg-secondary');
    }
    
    // 清空全局变量
    window.workflowCurrentDoc = null;
    
    // 重置文档类型选择下拉框
    const workflowDocTypeSelect = document.getElementById('workflowDocTypeSelect');
    if (workflowDocTypeSelect) {
        workflowDocTypeSelect.value = '';
    }
}

// 显示工作流文档选择器
function showWorkflowDocumentSelector(docType) {
    // 创建模态框
    const modalId = 'workflowDocumentSelectorModal';
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        // 创建模态框HTML
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="${modalId}Label">选择${docType === 'single' ? '单接口' : '多接口'}文档</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>文档ID</th>
                                            <th>上传时间</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody id="workflowDocumentTableBody">
                                        <tr>
                                            <td colspan="3" class="text-center">
                                                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                                                正在加载文档列表...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        modal = document.getElementById(modalId);
    }
    
    // 加载文档列表
    loadWorkflowDocumentList(docType);
    
    // 显示模态框
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// 加载工作流文档列表
function loadWorkflowDocumentList(docType) {
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    let apiUrl;
    
    if (docType === 'single') {
        apiUrl = baseUrl + '/api/docs/by-type/single';
    } else if (docType === 'multi') {
        apiUrl = baseUrl + '/api/docs/by-type/multi';
    } else {
        console.error('未知的文档类型:', docType);
        return;
    }
    
    const tableBody = document.getElementById('workflowDocumentTableBody');
    
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.data.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="3" class="text-center text-muted">
                                没有找到${docType === 'single' ? '单接口' : '多接口'}文档
                            </td>
                        </tr>
                    `;
                } else {
                    tableBody.innerHTML = data.data.map(doc => {
                        // 根据文档类型显示不同的信息
                        let displayName;
                        if (docType === 'single') {
                            // 单接口文档显示文档ID
                            displayName = `${doc.id || doc.file_id}`;
                        } else {
                            // 多接口文档显示文档名称
                            displayName = doc.file_name || doc.name;
                        }
                        
                        return `
                        <tr>
                            <td>${displayName}</td>
                            <td>${doc.upload_time || new Date().toLocaleString()}</td>
                            <td>
                                <button class="btn btn-sm btn-primary" onclick="selectWorkflowDocument('${doc.id || doc.file_id}', '${doc.file_name || doc.name}', '${docType}')">
                                    选择
                                </button>
                            </td>
                        </tr>
                    `;
                    }).join('');
                }
            } else {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="3" class="text-center text-danger">
                            加载文档失败: ${data.message}
                        </td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            console.error('加载文档列表失败:', error);
            tableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-danger">
                        加载文档失败: ${error.message}
                    </td>
                </tr>
            `;
        });
}

// 选择工作流文档
function selectWorkflowDocument(docId, docName, docType) {
    // 更新文档显示
    updateWorkflowDocument({
        id: docId,
        file_name: docName
    }, docType);
    
    // 关闭模态框
    const modal = document.getElementById('workflowDocumentSelectorModal');
    if (modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
            modalInstance.hide();
        }
    }
    
    // 根据文档类型显示不同的通知信息
    let notificationMessage;
    if (docType === 'single') {
        notificationMessage = `已选择单接口文档，ID: ${docId}`;
    } else {
        notificationMessage = `已选择文档: ${docName}`;
    }
    
    showSmartTestNotification(notificationMessage, 'success');
}

// 初始化测试按钮事件监听器 - 移至主初始化函数中
function initTestEditorButtons() {
    // 测试关联关系编辑器按钮
    const testRelationEditorBtn = document.getElementById('testRelationEditorBtn');
    if (testRelationEditorBtn) {
        testRelationEditorBtn.addEventListener('click', function() {
            console.log('测试关联关系编辑器按钮被点击');
            const relationEditor = document.getElementById('relationSpecEditor');
            if (relationEditor) {
                console.log('找到关联关系编辑器元素:', relationEditor);
                
                // 设置一些测试内容
                relationEditor.value = JSON.stringify({
                    "test": "这是测试内容",
                    "timestamp": new Date().toISOString()
                }, null, 2);
                
                // 如果已经初始化了CodeMirror，先销毁它
                if (relationEditor.nextElementSibling && relationEditor.nextElementSibling.classList.contains('CodeMirror')) {
                    const wrapper = relationEditor.nextElementSibling;
                    wrapper.parentNode.replaceChild(relationEditor, wrapper);
                }
                
                // 初始化CodeMirror
                try {
                    const cm = CodeMirror.fromTextArea(relationEditor, {
                        mode: {name: "javascript", json: true},
                        theme: 'default',
                        lineNumbers: true,
                        readOnly: false,
                        autoCloseBrackets: true,
                        matchBrackets: true
                    });
                    console.log('关联关系编辑器测试初始化完成', cm);
                } catch (error) {
                    console.error('关联关系编辑器测试初始化失败:', error);
                    // 尝试使用简单模式
                    try {
                        const cm = CodeMirror.fromTextArea(relationEditor, {
                            mode: 'text/plain',
                            theme: 'default',
                            lineNumbers: true,
                            readOnly: false
                        });
                        console.log('关联关系编辑器使用简单模式初始化完成', cm);
                    } catch (fallbackError) {
                        console.error('关联关系编辑器简单模式初始化也失败:', fallbackError);
                    }
                }
            } else {
                console.error('未找到关联关系编辑器元素');
            }
        });
    }
    
    // 测试业务场景编辑器按钮
    const testSceneEditorBtn = document.getElementById('testSceneEditorBtn');
    if (testSceneEditorBtn) {
        testSceneEditorBtn.addEventListener('click', function() {
            console.log('测试业务场景编辑器按钮被点击');
            const sceneEditor = document.getElementById('sceneSpecEditor');
            if (sceneEditor) {
                console.log('找到业务场景编辑器元素:', sceneEditor);
                
                // 设置一些测试内容
                sceneEditor.value = JSON.stringify({
                    "test": "这是测试内容",
                    "timestamp": new Date().toISOString()
                }, null, 2);
                
                // 如果已经初始化了CodeMirror，先销毁它
                if (sceneEditor.nextElementSibling && sceneEditor.nextElementSibling.classList.contains('CodeMirror')) {
                    const wrapper = sceneEditor.nextElementSibling;
                    wrapper.parentNode.replaceChild(sceneEditor, wrapper);
                }
                
                // 初始化CodeMirror
                try {
                    const cm = CodeMirror.fromTextArea(sceneEditor, {
                        mode: {name: "javascript", json: true},
                        theme: 'default',
                        lineNumbers: true,
                        readOnly: false,
                        autoCloseBrackets: true,
                        matchBrackets: true
                    });
                    console.log('业务场景编辑器测试初始化完成', cm);
                } catch (error) {
                    console.error('业务场景编辑器测试初始化失败:', error);
                    // 尝试使用简单模式
                    try {
                        const cm = CodeMirror.fromTextArea(sceneEditor, {
                            mode: 'text/plain',
                            theme: 'default',
                            lineNumbers: true,
                            readOnly: false
                        });
                        console.log('业务场景编辑器使用简单模式初始化完成', cm);
                    } catch (fallbackError) {
                        console.error('业务场景编辑器简单模式初始化也失败:', fallbackError);
                    }
                }
            } else {
                console.error('未找到业务场景编辑器元素');
            }
        });
    }
}