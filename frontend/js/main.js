// 主要JavaScript功能

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 添加平滑滚动效果
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // 添加页面加载动画
    animateElements();
    
    // 延迟初始化其他功能，确保DOM完全加载
    setTimeout(function() {
        // 初始化导航栏滚动效果
        initNavbarScroll();
        
        // 初始化功能卡片悬停效果
        initFeatureCards();
        
        // 初始化统计数字动画
        initCounters();
        
        // 加载主页面数据
        loadMainPageData();
    }, 100);
    
    // 初始化页面特定功能（检查当前页面）
    setTimeout(() => initPageSpecificFeatures(), 50);
});

// 初始化页面特定功能
function initPageSpecificFeatures() {
    console.log('初始化页面特定功能，当前路径:', window.location.pathname);
    
    // 获取当前页面路径
    const currentPath = window.location.pathname;
    
    // 根据不同页面初始化特定功能
    if (currentPath.includes('api-docs.html')) {
        console.log('检测到API文档页面，将延迟初始化页面功能');
        // 延迟初始化API文档页面功能，确保组件JS已加载
        setTimeout(() => {
            console.log('开始初始化API文档页面功能');
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
        }, 100); // 减少延迟时间
    } else if (currentPath.includes('test-cases.html')) {
        // 测试用例页面特定初始化
        setTimeout(() => {
            if (typeof initTestCasesPage === 'function') {
                initTestCasesPage();
            }
        }, 100);
    } else if (currentPath.includes('coverage.html')) {
        // 覆盖度页面特定初始化
        setTimeout(() => {
            if (typeof initCoveragePage === 'function') {
                initCoveragePage();
            }
        }, 100);
    } else if (currentPath.includes('suggestions.html')) {
        // 智能建议页面特定初始化
        setTimeout(() => {
            if (typeof initSuggestionsPage === 'function') {
                initSuggestionsPage();
            }
        }, 100);
    } else if (currentPath.includes('settings.html')) {
        // 设置页面特定初始化
        console.log('检测到设置页面，将延迟初始化页面功能');
        setTimeout(() => {
            try {
                if (typeof initSettingsApp === 'function') {
                    initSettingsApp();
                    console.log('initSettingsApp 执行完成');
                } else {
                    console.error('initSettingsApp 函数未定义');
                }
            } catch (error) {
                console.error('初始化设置页面时出错:', error);
            }
        }, 200); // 增加延迟时间，确保所有依赖都已加载
    }
}

// 页面元素动画
function animateElements() {
    const elements = document.querySelectorAll('.card:not(.feature-card), .fade-in');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    elements.forEach(element => {
        observer.observe(element);
    });
}

// API请求封装
const API = {
    // 基础URL
    baseUrl: '/api',
    
    // GET请求
    get: async function(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API GET Error:', error);
            throw error;
        }
    },
    
    // POST请求
    post: async function(endpoint, data) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API POST Error:', error);
            throw error;
        }
    },
    
    // PUT请求
    put: async function(endpoint, data) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API PUT Error:', error);
            throw error;
        }
    },
    
    // DELETE请求
    delete: async function(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API DELETE Error:', error);
            throw error;
        }
    }
};

// 通知功能
const Notification = {
    // 显示成功通知
    success: function(message, title = '成功') {
        this.show(message, 'success', title);
    },
    
    // 显示错误通知
    error: function(message, title = '错误') {
        this.show(message, 'danger', title);
    },
    
    // 显示警告通知
    warning: function(message, title = '警告') {
        this.show(message, 'warning', title);
    },
    
    // 显示信息通知
    info: function(message, title = '信息') {
        this.show(message, 'info', title);
    },
    
    // 显示通知
    show: function(message, type = 'info', title = '') {
        // 创建通知容器（如果不存在）
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '1050';
            container.style.maxWidth = '350px';
            document.body.appendChild(container);
        }
        
        // 创建通知元素
        const alertId = 'alert-' + Date.now();
        const alertElement = document.createElement('div');
        alertElement.className = `alert alert-${type} alert-dismissible fade show`;
        alertElement.id = alertId;
        alertElement.role = 'alert';
        
        // 构建通知内容
        let alertContent = '';
        if (title) {
            alertContent += `<strong>${title}</strong><br>`;
        }
        alertContent += message;
        alertContent += `<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        
        alertElement.innerHTML = alertContent;
        
        // 添加到容器
        container.appendChild(alertElement);
        
        // 自动关闭
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
};

// 加载状态管理
const Loading = {
    // 显示加载状态
    show: function(element, text = '加载中...') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;
        
        // 保存原始内容
        element.dataset.originalContent = element.innerHTML;
        
        // 创建加载指示器
        const spinner = document.createElement('div');
        spinner.className = 'd-flex justify-content-center align-items-center';
        spinner.innerHTML = `
            <div class="spinner-border spinner-border-sm me-2" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span>${text}</span>
        `;
        
        // 替换内容
        element.innerHTML = '';
        element.appendChild(spinner);
        element.disabled = true;
    },
    
    // 隐藏加载状态
    hide: function(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element || !element.dataset.originalContent) return;
        
        // 恢复原始内容
        element.innerHTML = element.dataset.originalContent;
        element.disabled = false;
        delete element.dataset.originalContent;
    }
};

// 表单验证
const FormValidation = {
    // 验证必填字段
    required: function(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, '此字段为必填项');
                isValid = false;
            } else {
                this.clearFieldError(field);
            }
        });
        
        return isValid;
    },
    
    // 验证邮箱格式
    email: function(field) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (field.value && !emailRegex.test(field.value)) {
            this.showFieldError(field, '请输入有效的邮箱地址');
            return false;
        } else {
            this.clearFieldError(field);
            return true;
        }
    },
    
    // 显示字段错误
    showFieldError: function(field, message) {
        // 移除之前的错误
        this.clearFieldError(field);
        
        // 添加错误样式
        field.classList.add('is-invalid');
        
        // 创建错误消息
        const errorElement = document.createElement('div');
        errorElement.className = 'invalid-feedback';
        errorElement.textContent = message;
        
        // 添加到字段后
        field.parentNode.appendChild(errorElement);
    },
    
    // 清除字段错误
    clearFieldError: function(field) {
        // 移除错误样式
        field.classList.remove('is-invalid');
        
        // 移除错误消息
        const errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.remove();
        }
    }
};

// 数据格式化
const Format = {
    // 格式化日期
    date: function(dateString, format = 'YYYY-MM-DD HH:mm:ss') {
        const date = new Date(dateString);
        
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    },
    
    // 格式化文件大小
    fileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // 格式化百分比
    percentage: function(value, total, decimals = 1) {
        if (total === 0) return '0%';
        
        const percentage = (value / total) * 100;
        return percentage.toFixed(decimals) + '%';
    }
};

// 导出全局函数
window.API = API;
window.Notification = Notification;
window.Loading = Loading;
window.FormValidation = FormValidation;
window.Format = Format;

// 导航栏滚动效果
function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    
    // 防止重复初始化
    if (!navbar || navbar.classList.contains('scroll-initialized')) return;
    
    // 标记为已初始化
    navbar.classList.add('scroll-initialized');
    
    // 使用防抖函数优化滚动事件
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        if (scrollTimeout) {
            window.cancelAnimationFrame(scrollTimeout);
        }
        
        scrollTimeout = window.requestAnimationFrame(function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    });
}

// 功能卡片悬停效果
function initFeatureCards() {
    const featureCards = document.querySelectorAll('.feature-card');
    
    // 防止重复初始化
    if (featureCards.length === 0) return;
    
    featureCards.forEach(card => {
        // 移除可能存在的旧事件监听器
        card.removeEventListener('mouseenter', handleCardMouseEnter);
        card.removeEventListener('mouseleave', handleCardMouseLeave);
        
        // 添加新的事件监听器
        card.addEventListener('mouseenter', handleCardMouseEnter);
        card.addEventListener('mouseleave', handleCardMouseLeave);
    });
}

// 处理卡片鼠标进入事件
function handleCardMouseEnter() {
    this.classList.add('hover');
}

// 处理卡片鼠标离开事件
function handleCardMouseLeave() {
    this.classList.remove('hover');
}

// 统计数字动画
function initCounters() {
    const counters = document.querySelectorAll('.counter');
    
    // 防止重复初始化
    if (counters.length === 0) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = parseInt(counter.getAttribute('data-target'));
                const duration = parseInt(counter.getAttribute('data-duration')) || 2000;
                
                // 检查是否已经初始化过
                if (!counter.classList.contains('animated')) {
                    counter.classList.add('animated');
                    animateCounter(counter, target, duration);
                }
                
                observer.unobserve(counter);
            }
        });
    }, {
        threshold: 0.5
    });
    
    counters.forEach(counter => {
        observer.observe(counter);
    });
}

// 数字动画函数
function animateCounter(element, target, duration) {
    let start = 0;
    const increment = target / (duration / 16);
    
    const updateCounter = () => {
        start += increment;
        
        if (start < target) {
            element.textContent = Math.ceil(start);
            requestAnimationFrame(updateCounter);
        } else {
            element.textContent = target;
        }
    };
    
    updateCounter();
}

// 加载主页面数据
function loadMainPageData() {
    // 加载覆盖度报告数据
    loadCoverageData();
    
    // 加载智能建议数据
    loadSuggestionsData();
    
    // 加载统计数据
    loadStatisticsData();
}

// 加载覆盖度报告数据
function loadCoverageData() {
    // 检查元素是否存在
    const coveragePercentage = document.querySelector('.coverage-percentage');
    if (!coveragePercentage) return;
    
    // 模拟API请求
    setTimeout(() => {
        // 更新覆盖度百分比
        const percentage = Math.floor(Math.random() * 30) + 70; // 70-100%
        coveragePercentage.textContent = percentage + '%';
        
        // 更新进度条
        const progressBar = document.querySelector('.coverage-progress-bar');
        if (progressBar) {
            progressBar.style.width = percentage + '%';
            
            // 根据百分比设置颜色
            progressBar.className = 'progress-bar';
            if (percentage >= 90) {
                progressBar.classList.add('bg-success');
            } else if (percentage >= 70) {
                progressBar.classList.add('bg-info');
            } else {
                progressBar.classList.add('bg-warning');
            }
        }
        
        // 更新生成时间
        const lastGenerated = document.querySelector('.coverage-last-generated');
        if (lastGenerated) {
            const date = new Date();
            date.setHours(date.getHours() - Math.floor(Math.random() * 24)); // 24小时内
            lastGenerated.textContent = Format.date(date, 'MM-DD HH:mm');
        }
    }, 500);
}

// 加载智能建议数据
function loadSuggestionsData() {
    // 检查元素是否存在
    const suggestionsTotal = document.querySelector('.suggestions-total');
    if (!suggestionsTotal) return;
    
    // 模拟API请求
    setTimeout(() => {
        // 更新待处理建议数量
        const total = Math.floor(Math.random() * 10) + 1; // 1-10
        suggestionsTotal.textContent = total;
        
        // 更新生成时间
        const lastGenerated = document.querySelector('.suggestions-last-generated');
        if (lastGenerated) {
            const date = new Date();
            date.setHours(date.getHours() - Math.floor(Math.random() * 12)); // 12小时内
            lastGenerated.textContent = Format.date(date, 'MM-DD HH:mm');
        }
    }, 800);
}

// 加载统计数据
function loadStatisticsData() {
    // 模拟API请求
    setTimeout(() => {
        // 这里可以添加更多统计数据加载逻辑
        // 例如：API文档数量、测试用例数量等
    }, 1000);
}