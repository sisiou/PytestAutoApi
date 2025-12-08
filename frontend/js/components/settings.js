// 系统设置页面JavaScript

// 初始化函数 - 确保在主JS加载后再执行
function initSettingsApp() {
    console.log('设置页面初始化开始');
    
    try {
        // 初始化页面
        initSettingsPage();
        
        // 加载设置数据
        loadSettingsData();
        
        // 绑定事件
        bindEvents();
        
        console.log('设置页面初始化完成');
    } catch (error) {
        console.error('设置页面初始化过程中出错:', error);
    }
}

// 加载设置数据
function loadSettingsData() {
    console.log('加载设置数据');
    
    try {
        // 从localStorage加载设置
        const settings = JSON.parse(localStorage.getItem('apiTestSettings') || '{}');
        
        // 填充表单
        fillFormData(settings);
        
        console.log('设置数据加载完成');
    } catch (error) {
        console.error('加载设置数据时出错:', error);
    }
}

// 保存设置
function saveSettings() {
    console.log('保存设置');
    
    try {
        // 收集表单数据
        const settings = collectFormData();
        
        // 显示加载状态
        showLoadingState(true);
        
        // 模拟保存过程
        setTimeout(() => {
            try {
                // 保存到localStorage
                localStorage.setItem('apiTestSettings', JSON.stringify(settings));
                
                // 隐藏加载状态
                showLoadingState(false);
                
                // 显示成功消息
                showAlert('设置已保存', 'success');
                
                console.log('设置保存完成');
            } catch (error) {
                console.error('保存设置时出错:', error);
                showLoadingState(false);
                showAlert('保存设置时出错', 'danger');
            }
        }, 500);
        
    } catch (error) {
        console.error('保存设置时出错:', error);
        showAlert('保存设置时出错', 'danger');
    }
}

// 显示提示消息
function showAlert(message, type = 'info') {
    // 创建提示元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 添加到页面顶部
    const container = document.querySelector('main');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 3秒后自动关闭
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 3000);
}

// DOM加载完成后执行
// 注意：这个事件监听器已被main.js中的initPageSpecificFeatures替代
// document.addEventListener('DOMContentLoaded', function() {
//     console.log('设置页面 DOMContentLoaded 事件触发');
//     
//     // 延迟初始化，确保main.js中的函数已定义
//     setTimeout(initSettingsApp, 100);
// });

// 如果DOM已经加载完成，直接执行初始化
// 注意：这个逻辑已被main.js中的initPageSpecificFeatures替代
// if (document.readyState === 'loading') {
//     // DOM还在加载中，等待DOMContentLoaded事件
//     console.log('DOM正在加载中，等待DOMContentLoaded事件');
// } else {
//     // DOM已经加载完成，直接执行初始化
//     console.log('DOM已经加载完成，直接执行初始化');
//     setTimeout(initSettingsApp, 100);
// }

// 初始化设置页面
function initSettingsPage() {
    console.log('初始化设置页面');
    
    try {
        // 初始化选项卡
        initTabs();
        
        // 初始化表单验证
        initFormValidation();
        
        // 初始化密码强度检查
        initPasswordStrengthCheck();
        
        // 初始化文件上传
        initFileUpload();
        
        // 绑定事件
        bindEvents();
        
        // 加载设置数据
        loadSettingsData();
        
        console.log('设置页面初始化完成');
    } catch (error) {
        console.error('初始化设置页面时出错:', error);
    }
}

// 初始化选项卡
function initTabs() {
    console.log('初始化选项卡');
    
    // 获取当前选项卡
    const currentTab = localStorage.getItem('settingsCurrentTab') || 'general';
    
    // 激活当前选项卡
    const tabLink = document.querySelector(`a[href="#${currentTab}"]`);
    if (tabLink) {
        tabLink.click();
    }
    
    // 监听选项卡切换事件
    document.querySelectorAll('a[data-bs-toggle="pill"]').forEach(link => {
        link.addEventListener('shown.bs.tab', function(e) {
            const tabId = e.target.getAttribute('href').substring(1);
            localStorage.setItem('settingsCurrentTab', tabId);
        });
    });
}

// 初始化表单验证
function initFormValidation() {
    console.log('初始化表单验证');
    
    // 获取所有表单
    const forms = document.querySelectorAll('form');
    
    // 为每个表单添加验证
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 检查表单是否有效
            if (!form.checkValidity()) {
                e.stopPropagation();
                form.classList.add('was-validated');
                return;
            }
            
            // 表单有效，保存设置
            saveSettings();
        });
    });
}

// 初始化密码强度检查
function initPasswordStrengthCheck() {
    console.log('初始化密码强度检查');
    
    // 获取密码输入框
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            // 检查密码强度
            const strength = checkPasswordStrength(this.value);
            
            // 显示密码强度
            showPasswordStrength(this, strength);
        });
    });
}

// 检查密码强度
function checkPasswordStrength(password) {
    if (!password) return 0;
    
    let strength = 0;
    
    // 检查长度
    if (password.length >= 8) strength += 1;
    if (password.length >= 12) strength += 1;
    
    // 检查是否包含数字
    if (/\d/.test(password)) strength += 1;
    
    // 检查是否包含小写字母
    if (/[a-z]/.test(password)) strength += 1;
    
    // 检查是否包含大写字母
    if (/[A-Z]/.test(password)) strength += 1;
    
    // 检查是否包含特殊字符
    if (/[^A-Za-z0-9]/.test(password)) strength += 1;
    
    return Math.min(strength, 3); // 返回0-3的强度级别
}

// 显示密码强度
function showPasswordStrength(input, strength) {
    // 查找或创建密码强度指示器
    let strengthIndicator = input.parentNode.querySelector('.password-strength');
    
    if (!strengthIndicator) {
        strengthIndicator = document.createElement('div');
        strengthIndicator.className = 'password-strength';
        input.parentNode.appendChild(strengthIndicator);
    }
    
    // 移除所有强度类
    strengthIndicator.classList.remove('weak', 'medium', 'strong');
    
    // 根据强度添加相应的类
    if (strength === 0) {
        strengthIndicator.style.width = '0%';
    } else if (strength === 1) {
        strengthIndicator.classList.add('weak');
        strengthIndicator.style.width = '33%';
    } else if (strength === 2) {
        strengthIndicator.classList.add('medium');
        strengthIndicator.style.width = '66%';
    } else {
        strengthIndicator.classList.add('strong');
        strengthIndicator.style.width = '100%';
    }
}

// 初始化文件上传
function initFileUpload() {
    console.log('初始化文件上传');
    
    try {
        const fileInput = document.getElementById('settingsFileInput');
        const uploadArea = document.getElementById('importExportArea');
        
        if (!fileInput || !uploadArea) {
            console.warn('文件上传元素不存在');
            return;
        }
        
        // 创建文件信息区域
        const fileInfoContainer = document.createElement('div');
        fileInfoContainer.id = 'settingsFileInfo';
        fileInfoContainer.className = 'file-info-container mt-3';
        fileInfoContainer.style.display = 'none';
        uploadArea.parentNode.insertBefore(fileInfoContainer, uploadArea.nextSibling);
        
        // 点击上传区域触发文件选择
        uploadArea.addEventListener('click', function() {
            fileInput.click();
        });
        
        // 文件选择事件
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                displaySettingsFileInfo(file);
            }
        });
        
        // 拖拽上传
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, function() {
                uploadArea.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, function() {
                uploadArea.classList.remove('dragover');
            }, false);
        });
        
        uploadArea.addEventListener('drop', function(e) {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                displaySettingsFileInfo(files[0]);
            }
        });
        
        console.log('文件上传初始化完成');
    } catch (error) {
        console.error('初始化文件上传时出错:', error);
    }
}

// 显示设置文件信息
function displaySettingsFileInfo(file) {
    console.log('显示设置文件信息');
    
    try {
        let fileInfo = document.getElementById('settingsFileInfo');
        
        // 如果文件信息区域不存在，创建它
        if (!fileInfo) {
            fileInfo = document.createElement('div');
            fileInfo.id = 'settingsFileInfo';
            fileInfo.className = 'file-info-container mt-3';
            
            // 插入到上传区域后面
            const uploadArea = document.getElementById('importExportArea');
            if (uploadArea) {
                uploadArea.parentNode.insertBefore(fileInfo, uploadArea.nextSibling);
            } else {
                console.warn('未找到上传区域，无法显示文件信息');
                return;
            }
        }
        
        // 显示文件信息区域
        fileInfo.style.display = 'block';
        
        // 更新文件信息
        fileInfo.innerHTML = `
            <div class="file-info-item">
                <span class="file-info-label">
                    <i class="fas fa-file file-info-icon"></i>文件名
                </span>
                <span class="file-info-value">${file.name}</span>
            </div>
            <div class="file-info-item">
                <span class="file-info-label">
                    <i class="fas fa-weight file-info-icon"></i>文件大小
                </span>
                <span class="file-info-value">${formatFileSize(file.size)}</span>
            </div>
            <div class="file-info-item">
                <span class="file-info-label">
                    <i class="fas fa-clock file-info-icon"></i>修改时间
                </span>
                <span class="file-info-value">${formatDate(file.lastModified)}</span>
            </div>
            <div class="mt-3">
                <button type="button" class="btn btn-success btn-sm" id="confirmImportBtn">
                    <i class="fas fa-check me-1"></i>确认导入
                </button>
                <button type="button" class="btn btn-outline-secondary btn-sm" id="cancelImportBtn">
                    <i class="fas fa-times me-1"></i>取消
                </button>
            </div>
        `;
        
        // 绑定确认导入按钮事件
        const confirmBtn = document.getElementById('confirmImportBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', function() {
                importSettings(file);
            });
        }
        
        // 绑定取消按钮事件
        const cancelBtn = document.getElementById('cancelImportBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                // 清空文件输入
                document.getElementById('settingsFileInput').value = '';
                // 隐藏文件信息区域
                fileInfo.style.display = 'none';
            });
        }
        
        console.log('设置文件信息显示完成');
    } catch (error) {
        console.error('显示设置文件信息时出错:', error);
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

// 加载设置数据
function loadSettingsData() {
    console.log('加载设置数据');
    
    try {
        // 从localStorage加载设置
        const settings = JSON.parse(localStorage.getItem('apiTestSettings') || '{}');
        
        // 填充表单数据
        fillFormData(settings);
        
        console.log('设置数据加载完成');
    } catch (error) {
        console.error('加载设置数据时出错:', error);
    }
}

// 填充表单数据
function fillFormData(settings) {
    console.log('填充表单数据');
    
    try {
        // 遍历所有设置项
        Object.keys(settings).forEach(key => {
            const element = document.getElementById(key);
            
            if (!element) return;
            
            const value = settings[key];
            
            // 根据元素类型设置值
            if (element.type === 'checkbox') {
                element.checked = value;
            } else if (element.type === 'radio') {
                if (element.value === value) {
                    element.checked = true;
                }
            } else if (element.tagName === 'SELECT') {
                element.value = value;
            } else if (element.tagName === 'TEXTAREA' || element.type === 'text' || element.type === 'number' || element.type === 'password' || element.type === 'email' || element.type === 'url' || element.type === 'tel' || element.type === 'search' || element.type === 'date' || element.type === 'time' || element.type === 'datetime-local' || element.type === 'month' || element.type === 'week' || element.type === 'color' || element.type === 'range') {
                element.value = value;
            }
        });
        
        console.log('表单数据填充完成');
    } catch (error) {
        console.error('填充表单数据时出错:', error);
    }
}

// 保存设置
function saveSettings() {
    console.log('保存设置');
    
    try {
        // 收集表单数据
        const settings = collectFormData();
        
        // 显示加载状态
        showLoadingState(true);
        
        // 模拟保存过程
        setTimeout(() => {
            try {
                // 保存到localStorage
                localStorage.setItem('apiTestSettings', JSON.stringify(settings));
                
                // 隐藏加载状态
                showLoadingState(false);
                
                // 显示成功消息
                showAlert('设置已保存', 'success');
                
                console.log('设置保存完成');
            } catch (error) {
                console.error('保存设置时出错:', error);
                showLoadingState(false);
                showAlert('保存设置时出错', 'danger');
            }
        }, 500);
        
    } catch (error) {
        console.error('保存设置时出错:', error);
        showAlert('保存设置时出错', 'danger');
    }
}

// 收集表单数据
function collectFormData() {
    console.log('收集表单数据');
    
    try {
        const settings = {};
        
        // 获取所有表单元素
        const formElements = document.querySelectorAll('input, select, textarea');
        
        formElements.forEach(element => {
            if (!element.id) return;
            
            // 根据元素类型获取值
            if (element.type === 'checkbox') {
                settings[element.id] = element.checked;
            } else if (element.type === 'radio') {
                if (element.checked) {
                    settings[element.name] = element.value;
                }
            } else {
                settings[element.id] = element.value;
            }
        });
        
        console.log('表单数据收集完成');
        return settings;
    } catch (error) {
        console.error('收集表单数据时出错:', error);
        return {};
    }
}

// 重置设置
function resetSettings() {
    console.log('重置设置');
    
    try {
        // 显示确认对话框
        if (!confirm('确定要重置所有设置吗？此操作不可撤销。')) {
            console.log('用户取消重置设置');
            return;
        }
        
        // 显示加载状态
        showLoadingState(true);
        
        // 模拟API请求
        setTimeout(() => {
            try {
                // 清除localStorage中的设置
                localStorage.removeItem('apiTestSettings');
                
                // 重新加载默认设置
                loadDefaultSettings();
                
                // 隐藏加载状态
                showLoadingState(false);
                
                // 显示成功消息
                showAlert('设置已重置', 'success');
                
                console.log('设置重置完成');
            } catch (error) {
                console.error('重置设置时出错:', error);
                showLoadingState(false);
                showAlert('重置设置失败', 'danger');
            }
        }, 500);
    } catch (error) {
        console.error('重置设置时出错:', error);
        showAlert('重置设置失败', 'danger');
    }
}

// 加载默认设置
function loadDefaultSettings() {
    console.log('加载默认设置');
    
    try {
        // 默认设置
        const defaultSettings = {
            // 常规设置
            systemName: '智能自动化测试平台',
            systemDescription: '基于AI的API自动化测试平台，支持API文档解析、测试用例生成、覆盖度分析和智能建议。',
            systemVersion: '1.0.0',
            defaultLanguage: 'zh-CN',
            timezone: 'Asia/Shanghai',
            theme: 'light',
            enableDebug: true,
            
            // API配置
            apiTimeout: 30,
            maxConcurrentRequests: 10,
            retryAttempts: 3,
            retryDelay: 1,
            followRedirects: true,
            verifySsl: true,
            customHeaders: JSON.stringify({
                "User-Agent": "PytestAutoApi/1.0.0",
                "Accept": "application/json"
            }, null, 2),
            
            // 测试配置
            testTimeout: 60,
            testParallelism: 4,
            testRetryAttempts: 1,
            coverageThreshold: 80,
            testDataPath: './data',
            testReportPath: './report',
            generateAllureReport: true,
            generateHtmlReport: true,
            autoGenerateSuggestions: true,
            
            // 通知设置
            enableEmailNotification: true,
            smtpServer: 'smtp.example.com',
            smtpPort: 587,
            smtpUsername: '',
            smtpPassword: '',
            notificationRecipients: 'admin@example.com',
            enableDingTalkNotification: false,
            dingTalkWebhook: '',
            enableWeChatNotification: false,
            weChatWebhook: '',
            
            // 安全设置
            sessionTimeout: 30,
            passwordMinLength: 8,
            requireUppercase: true,
            requireLowercase: true,
            requireNumbers: true,
            requireSpecialChars: true,
            maxLoginAttempts: 5,
            lockoutDuration: 15,
            enableTwoFactorAuth: false,
            logSecurityEvents: true,
            
            // 备份与恢复
            backupPath: './backup',
            backupRetention: 30,
            backupSchedule: 'daily',
            backupTime: '02:00',
            compressBackup: true,
            encryptBackup: false,
            backupEncryptionKey: '',
            remoteBackupUrl: '',
            remoteBackupUsername: '',
            remoteBackupPassword: ''
        };
        
        // 填充表单数据
        fillFormData(defaultSettings);
        
        console.log('默认设置加载完成');
    } catch (error) {
        console.error('加载默认设置时出错:', error);
    }
}

// 立即备份
function backupNow() {
    console.log('立即备份');
    
    try {
        // 显示加载状态
        showLoadingState(true);
        
        // 模拟API请求
        setTimeout(() => {
            // 隐藏加载状态
            showLoadingState(false);
            
            // 显示成功消息
            showMessage('备份已创建', 'success');
            
            console.log('备份创建完成');
        }, 2000);
    } catch (error) {
        console.error('创建备份时出错:', error);
        showLoadingState(false);
        showMessage('创建备份失败', 'danger');
    }
}

// 显示恢复模态框
function showRestoreModal() {
    console.log('显示恢复模态框');
    
    try {
        const modal = new bootstrap.Modal(document.getElementById('restoreModal'));
        modal.show();
        
        console.log('恢复模态框显示完成');
    } catch (error) {
        console.error('显示恢复模态框时出错:', error);
        showMessage('无法显示恢复对话框', 'danger');
    }
}

// 确认恢复备份
function confirmRestore() {
    console.log('确认恢复备份');
    
    try {
        const fileInput = document.getElementById('backupFile');
        
        if (!fileInput.files || !fileInput.files[0]) {
            console.log('未选择备份文件');
            showMessage('请选择备份文件', 'error');
            return;
        }
        
        // 显示加载状态
        showLoadingState(true);
        
        // 模拟API请求
        setTimeout(() => {
            // 隐藏加载状态
            showLoadingState(false);
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('restoreModal'));
            modal.hide();
            
            // 显示成功消息
            showMessage('备份已恢复', 'success');
            
            // 重新加载页面
            setTimeout(() => {
                window.location.reload();
            }, 2000);
            
            console.log('备份恢复完成');
        }, 3000);
    } catch (error) {
        console.error('恢复备份时出错:', error);
        showLoadingState(false);
        showMessage('恢复备份失败', 'danger');
    }
}

// 显示/隐藏加载状态
function showLoadingState(show) {
    console.log(show ? '显示加载状态' : '隐藏加载状态');
    
    try {
        const mainElement = document.querySelector('main');
        
        if (show) {
            mainElement.classList.add('loading');
        } else {
            mainElement.classList.remove('loading');
        }
    } catch (error) {
        console.error('切换加载状态时出错:', error);
    }
}

// 显示消息
function showMessage(message, type) {
    // 创建消息元素
    const messageElement = document.createElement('div');
    messageElement.className = `${type}-message`;
    messageElement.textContent = message;
    
    // 添加到页面
    document.body.appendChild(messageElement);
    
    // 自动移除
    setTimeout(() => {
        if (messageElement.parentNode) {
            messageElement.parentNode.removeChild(messageElement);
        }
    }, 3000);
}

// 绑定事件
function bindEvents() {
    console.log('绑定事件处理器');
    
    try {
        // 保存设置按钮
        const saveBtn = document.getElementById('saveSettingsBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', saveSettings);
        }
        
        // 重置设置按钮
        const resetBtn = document.getElementById('resetSettingsBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetSettings);
        }
        
        // 导出设置按钮
        const exportBtn = document.getElementById('exportSettingsBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', exportSettings);
        }
        
        // 导入设置按钮
        const importBtn = document.getElementById('importSettingsBtn');
        if (importBtn) {
            importBtn.addEventListener('click', function() {
                const fileInput = document.getElementById('settingsFileInput');
                if (fileInput) {
                    fileInput.click();
                }
            });
        }
        
        console.log('事件绑定完成');
    } catch (error) {
        console.error('绑定事件时出错:', error);
    }
}

// 导出设置
function exportSettings() {
    console.log('开始导出设置');
    
    try {
        // 获取当前设置
        let settings = localStorage.getItem('apiTestSettings');
        
        if (!settings) {
            // 如果localStorage中没有设置，从表单收集当前设置
            settings = collectFormData();
        } else {
            settings = JSON.parse(settings);
        }
        
        // 添加导出元数据
        const exportData = {
            ...settings,
            _exportInfo: {
                date: new Date().toISOString(),
                version: '1.0',
                description: 'API测试工具设置导出文件'
            }
        };
        
        // 创建JSON字符串
        const jsonString = JSON.stringify(exportData, null, 2);
        
        // 创建Blob对象
        const blob = new Blob([jsonString], { type: 'application/json' });
        
        // 创建下载链接
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `api-test-settings-${formatDate(new Date().getTime())}.json`;
        
        // 触发下载
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 释放URL对象
        URL.revokeObjectURL(url);
        
        // 显示成功消息
        showAlert('设置导出成功！', 'success');
        
        console.log('设置导出完成');
    } catch (error) {
        console.error('导出设置时出错:', error);
        showAlert('导出设置时出错，请重试', 'danger');
    }
}

// 导入设置
function importSettings() {
    console.log('导入设置');
    
    try {
        // 获取文件输入元素
        const fileInput = document.getElementById('settingsFileInput');
        if (!fileInput || !fileInput.files || !fileInput.files[0]) {
            showAlert('请选择要导入的设置文件', 'warning');
            return;
        }
        
        const file = fileInput.files[0];
        
        // 显示加载状态
        showLoadingState(true);
        
        // 读取文件内容
        const reader = new FileReader();
        
        reader.onload = function(e) {
            try {
                const content = e.target.result;
                const settings = JSON.parse(content);
                
                // 验证设置数据
                if (!validateSettingsData(settings)) {
                    showLoadingState(false);
                    showAlert('无效的设置文件格式', 'danger');
                    return;
                }
                
                // 移除导出元数据
                const cleanSettings = { ...settings };
                delete cleanSettings._exportInfo;
                
                // 保存设置到localStorage
                localStorage.setItem('apiTestSettings', JSON.stringify(cleanSettings));
                
                // 填充表单
                fillFormData(cleanSettings);
                
                // 隐藏加载状态
                showLoadingState(false);
                
                // 显示成功消息
                showAlert('设置导入成功', 'success');
                
                // 清空文件输入
                fileInput.value = '';
                
                console.log('设置导入完成');
            } catch (error) {
                console.error('导入设置时出错:', error);
                showLoadingState(false);
                showAlert('导入设置时出错: ' + error.message, 'danger');
            }
        };
        
        reader.onerror = function() {
            console.error('读取文件时出错');
            showLoadingState(false);
            showAlert('读取文件时出错', 'danger');
        };
        
        reader.readAsText(file);
        
    } catch (error) {
        console.error('导入设置时出错:', error);
        showAlert('导入设置时出错', 'danger');
    }
}

// 验证设置数据
function validateSettingsData(settings) {
    try {
        // 检查是否为对象
        if (typeof settings !== 'object' || settings === null) {
            return false;
        }
        
        // 检查是否包含导出信息
        if (!settings._exportInfo) {
            return false;
        }
        
        // 检查导出信息是否有效
        const exportInfo = settings._exportInfo;
        if (!exportInfo.date || !exportInfo.version) {
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('验证设置数据时出错:', error);
        return false;
    }
}

// 格式化日期
function formatDate(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}${month}${day}-${hours}${minutes}`;
}