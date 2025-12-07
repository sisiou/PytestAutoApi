// 智能建议页面JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initSuggestionsPage();
    
    // 加载数据
    loadSuggestionsData();
    
    // 绑定事件
    bindEvents();
});

// 页面初始化
function initSuggestionsPage() {
    // 初始化视图模式
    initViewMode();
    
    // 初始化筛选器
    initFilters();
}

// 初始化视图模式
function initViewMode() {
    const cardViewRadio = document.getElementById('cardView');
    const listViewRadio = document.getElementById('listView');
    const cardView = document.getElementById('suggestionsCardView');
    const listView = document.getElementById('suggestionsListView');
    
    // 默认显示卡片视图
    cardViewRadio.checked = true;
    cardView.classList.remove('d-none');
    listView.classList.add('d-none');
    
    // 绑定视图切换事件
    cardViewRadio.addEventListener('change', function() {
        if (this.checked) {
            cardView.classList.remove('d-none');
            listView.classList.add('d-none');
        }
    });
    
    listViewRadio.addEventListener('change', function() {
        if (this.checked) {
            cardView.classList.add('d-none');
            listView.classList.remove('d-none');
        }
    });
}

// 初始化筛选器
function initFilters() {
    const categoryFilter = document.getElementById('categoryFilter');
    const priorityFilter = document.getElementById('priorityFilter');
    const statusFilter = document.getElementById('statusFilter');
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    
    // 绑定筛选事件
    categoryFilter.addEventListener('change', applyFilters);
    priorityFilter.addEventListener('change', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
    
    // 绑定搜索事件
    searchBtn.addEventListener('click', applyFilters);
    searchInput.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
}

// 加载建议数据
function loadSuggestionsData() {
    // 显示加载状态
    showLoading();
    
    // 模拟API请求
    setTimeout(() => {
        // 生成模拟数据
        const suggestions = generateMockSuggestions();
        
        // 渲染建议
        renderSuggestions(suggestions);
        
        // 更新统计数据
        updateStatistics(suggestions);
        
        // 隐藏加载状态
        hideLoading();
    }, 1000);
}

// 生成模拟建议数据
function generateMockSuggestions() {
    const categories = ['coverage', 'performance', 'security', 'usability', 'maintenance'];
    const priorities = ['high', 'medium', 'low'];
    const statuses = ['pending', 'adopted', 'rejected'];
    
    const suggestions = [];
    
    // 生成24条建议
    for (let i = 1; i <= 24; i++) {
        const category = categories[Math.floor(Math.random() * categories.length)];
        const priority = priorities[Math.floor(Math.random() * priorities.length)];
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        
        // 根据类别生成不同的建议内容
        let content, reason, benefit, implementation, relatedApis;
        
        switch (category) {
            case 'coverage':
                content = `建议增加对${getRandomApiName()}API的测试用例，以提升API覆盖度。`;
                reason = `根据API文档分析，${getRandomApiName()}API尚未被现有测试用例覆盖。`;
                benefit = `通过添加测试用例，可以将API覆盖度提升约${Math.floor(Math.random() * 5) + 1}%。`;
                implementation = `创建${getRandomApiName()}API的测试用例，验证各种输入参数和响应。`;
                relatedApis = [getRandomApiName(), getRandomApiName()];
                break;
                
            case 'performance':
                content = `建议对${getRandomApiName()}API进行性能测试，以验证系统在高并发情况下的表现。`;
                reason = `根据API文档分析，${getRandomApiName()}API可能成为系统性能瓶颈。`;
                benefit = `通过性能测试，可以提前发现并解决潜在的性能问题，提升用户体验。`;
                implementation = `设计并发测试场景，模拟${Math.floor(Math.random() * 100) + 50}个并发请求，监控响应时间和资源使用情况。`;
                relatedApis = [getRandomApiName(), getRandomApiName()];
                break;
                
            case 'security':
                content = `建议对${getRandomApiName()}API进行安全测试，验证系统的安全性。`;
                reason = `根据API文档分析，${getRandomApiName()}API涉及敏感数据操作，需要进行安全测试。`;
                benefit = `通过安全测试，可以发现并修复潜在的安全漏洞，保护用户数据安全。`;
                implementation = `进行SQL注入、XSS攻击、权限绕过等安全测试，验证系统的安全性。`;
                relatedApis = [getRandomApiName(), '认证API', '授权API'];
                break;
                
            case 'usability':
                content = `建议优化${getRandomApiName()}API的错误处理机制，提升API的可用性。`;
                reason = `根据API文档分析，${getRandomApiName()}API的错误信息不够明确，影响开发者使用体验。`;
                benefit = `通过优化错误处理，可以提高API的易用性，减少开发者调试时间。`;
                implementation = `设计更明确的错误码和错误信息，提供详细的错误文档。`;
                relatedApis = [getRandomApiName(), '错误日志API'];
                break;
                
            case 'maintenance':
                content = `建议重构${getRandomApiName()}API的测试用例，提高测试用例的可维护性。`;
                reason = `根据测试用例分析，${getRandomApiName()}API的测试用例存在重复代码，维护成本高。`;
                benefit = `通过重构测试用例，可以降低维护成本，提高测试效率。`;
                implementation = `提取公共测试步骤，创建可复用的测试函数，优化测试数据管理。`;
                relatedApis = [getRandomApiName(), '测试管理API'];
                break;
        }
        
        // 生成创建时间（最近30天内）
        const createdAt = new Date();
        createdAt.setDate(createdAt.getDate() - Math.floor(Math.random() * 30));
        
        suggestions.push({
            id: `SUG-${String(i).padStart(3, '0')}`,
            category: category,
            priority: priority,
            status: status,
            content: content,
            reason: reason,
            benefit: benefit,
            implementation: implementation,
            relatedApis: relatedApis,
            createdAt: createdAt,
            confidence: Math.floor(Math.random() * 30) + 70 // 70-100之间的置信度
        });
    }
    
    return suggestions;
}

// 获取随机API名称
function getRandomApiName() {
    const apiNames = [
        '用户注册', '用户登录', '用户注销', '用户信息查询', '用户信息更新',
        '订单创建', '订单查询', '订单更新', '订单取消', '订单支付',
        '产品查询', '产品创建', '产品更新', '产品删除', '库存查询',
        '库存更新', '库存预警', '支付处理', '支付查询', '支付退款',
        '数据分析', '报表生成', '通知发送', '消息推送', '系统配置'
    ];
    
    return apiNames[Math.floor(Math.random() * apiNames.length)];
}

// 渲染建议
function renderSuggestions(suggestions) {
    // 渲染卡片视图
    renderCardView(suggestions);
    
    // 渲染列表视图
    renderListView(suggestions);
}

// 渲染卡片视图
function renderCardView(suggestions) {
    const container = document.getElementById('suggestionsCardView');
    
    if (suggestions.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-lightbulb fa-3x text-muted mb-3"></i>
                <h4 class="text-muted">暂无符合条件的智能建议</h4>
                <p class="text-muted">请尝试调整筛选条件或生成新建议</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    suggestions.forEach(suggestion => {
        const categoryText = getCategoryText(suggestion.category);
        const priorityText = getPriorityText(suggestion.priority);
        const statusText = getStatusText(suggestion.priority);
        const statusClass = getStatusClass(suggestion.status);
        
        html += `
            <div class="suggestion-card card priority-${suggestion.priority}" data-id="${suggestion.id}">
                <div class="card-body">
                    <div class="suggestion-header">
                        <div class="suggestion-id">${suggestion.id}</div>
                        <div class="suggestion-badges">
                            <span class="badge bg-primary category-${suggestion.category}">${categoryText}</span>
                            <span class="badge bg-${getPriorityBadgeColor(suggestion.priority)}">${priorityText}</span>
                            <span class="badge ${statusClass}">${statusText}</span>
                        </div>
                    </div>
                    
                    <div class="suggestion-content">
                        ${suggestion.content}
                    </div>
                    
                    <div class="suggestion-meta">
                        <div>
                            <i class="fas fa-calendar-alt me-1"></i>
                            ${formatDate(suggestion.createdAt)}
                        </div>
                        <div>
                            置信度: ${suggestion.confidence}%
                            <div class="confidence-indicator d-inline-block">
                                <div class="confidence-bar" style="width: ${suggestion.confidence}%"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="suggestion-actions">
                        <button class="btn btn-sm btn-outline-primary view-suggestion-btn" data-id="${suggestion.id}">
                            <i class="fas fa-eye me-1"></i>查看详情
                        </button>
                        <button class="btn btn-sm btn-outline-success adopt-suggestion-btn" data-id="${suggestion.id}" ${suggestion.status !== 'pending' ? 'disabled' : ''}>
                            <i class="fas fa-check me-1"></i>采纳
                        </button>
                        <button class="btn btn-sm btn-outline-danger reject-suggestion-btn" data-id="${suggestion.id}" ${suggestion.status !== 'pending' ? 'disabled' : ''}>
                            <i class="fas fa-times me-1"></i>拒绝
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // 绑定卡片视图中的按钮事件
    bindCardViewEvents();
}

// 渲染列表视图
function renderListView(suggestions) {
    const tableBody = document.getElementById('suggestionsTableBody');
    
    if (suggestions.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-lightbulb fa-2x text-muted mb-2"></i>
                    <p class="text-muted mb-0">暂无符合条件的智能建议</p>
                </td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    
    suggestions.forEach(suggestion => {
        const categoryText = getCategoryText(suggestion.category);
        const priorityText = getPriorityText(suggestion.priority);
        const statusText = getStatusText(suggestion.status);
        
        html += `
            <tr data-id="${suggestion.id}">
                <td>${suggestion.id}</td>
                <td>
                    <div class="suggestion-list-content" title="${suggestion.content}">
                        ${suggestion.content}
                    </div>
                </td>
                <td><span class="badge bg-primary category-${suggestion.category}">${categoryText}</span></td>
                <td><span class="badge bg-${getPriorityBadgeColor(suggestion.priority)}">${priorityText}</span></td>
                <td><span class="badge ${getStatusClass(suggestion.status)}">${statusText}</span></td>
                <td>${formatDate(suggestion.createdAt)}</td>
                <td>
                    <div class="suggestion-list-actions">
                        <button class="btn btn-sm btn-outline-primary view-suggestion-btn" data-id="${suggestion.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success adopt-suggestion-btn" data-id="${suggestion.id}" ${suggestion.status !== 'pending' ? 'disabled' : ''}>
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger reject-suggestion-btn" data-id="${suggestion.id}" ${suggestion.status !== 'pending' ? 'disabled' : ''}>
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
    
    // 绑定列表视图中的按钮事件
    bindListViewEvents();
}

// 绑定卡片视图中的按钮事件
function bindCardViewEvents() {
    // 查看详情按钮
    document.querySelectorAll('.view-suggestion-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const suggestionId = this.getAttribute('data-id');
            showSuggestionDetail(suggestionId);
        });
    });
    
    // 采纳建议按钮
    document.querySelectorAll('.adopt-suggestion-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const suggestionId = this.getAttribute('data-id');
            adoptSuggestion(suggestionId);
        });
    });
    
    // 拒绝建议按钮
    document.querySelectorAll('.reject-suggestion-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const suggestionId = this.getAttribute('data-id');
            rejectSuggestion(suggestionId);
        });
    });
}

// 绑定列表视图中的按钮事件
function bindListViewEvents() {
    // 查看详情按钮
    document.querySelectorAll('.view-suggestion-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const suggestionId = this.getAttribute('data-id');
            showSuggestionDetail(suggestionId);
        });
    });
    
    // 采纳建议按钮
    document.querySelectorAll('.adopt-suggestion-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const suggestionId = this.getAttribute('data-id');
            adoptSuggestion(suggestionId);
        });
    });
    
    // 拒绝建议按钮
    document.querySelectorAll('.reject-suggestion-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const suggestionId = this.getAttribute('data-id');
            rejectSuggestion(suggestionId);
        });
    });
}

// 更新统计数据
function updateStatistics(suggestions) {
    // 计算统计数据
    const totalSuggestions = suggestions.length;
    const adoptedSuggestions = suggestions.filter(s => s.status === 'adopted').length;
    const pendingSuggestions = suggestions.filter(s => s.status === 'pending').length;
    const adoptionRate = totalSuggestions > 0 ? Math.round((adoptedSuggestions / totalSuggestions) * 100) : 0;
    
    // 更新DOM
    document.getElementById('totalSuggestions').textContent = totalSuggestions;
    document.getElementById('adoptedSuggestions').textContent = adoptedSuggestions;
    document.getElementById('pendingSuggestions').textContent = pendingSuggestions;
    document.getElementById('adoptionRate').textContent = adoptionRate + '%';
}

// 应用筛选器
function applyFilters() {
    const category = document.getElementById('categoryFilter').value;
    const priority = document.getElementById('priorityFilter').value;
    const status = document.getElementById('statusFilter').value;
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    // 获取所有建议数据
    const allSuggestions = generateMockSuggestions();
    
    // 应用筛选条件
    let filteredSuggestions = allSuggestions.filter(suggestion => {
        // 类别筛选
        if (category && suggestion.category !== category) {
            return false;
        }
        
        // 优先级筛选
        if (priority && suggestion.priority !== priority) {
            return false;
        }
        
        // 状态筛选
        if (status && suggestion.status !== status) {
            return false;
        }
        
        // 搜索筛选
        if (searchTerm && !suggestion.content.toLowerCase().includes(searchTerm)) {
            return false;
        }
        
        return true;
    });
    
    // 重新渲染建议
    renderSuggestions(filteredSuggestions);
    
    // 更新统计数据
    updateStatistics(filteredSuggestions);
}

// 显示建议详情
function showSuggestionDetail(suggestionId) {
    // 获取建议数据
    const allSuggestions = generateMockSuggestions();
    const suggestion = allSuggestions.find(s => s.id === suggestionId);
    
    if (!suggestion) {
        showSmartTestNotification('未找到建议详情', 'error');
        return;
    }
    
    // 填充模态框数据
    document.getElementById('detailSuggestionId').textContent = suggestion.id;
    document.getElementById('detailCategory').textContent = getCategoryText(suggestion.category);
    document.getElementById('detailCategory').className = `badge bg-primary category-${suggestion.category}`;
    document.getElementById('detailPriority').textContent = getPriorityText(suggestion.priority);
    document.getElementById('detailPriority').className = `badge bg-${getPriorityBadgeColor(suggestion.priority)}`;
    document.getElementById('detailStatus').textContent = getStatusText(suggestion.status);
    document.getElementById('detailStatus').className = `badge ${getStatusClass(suggestion.status)}`;
    document.getElementById('detailContent').textContent = suggestion.content;
    document.getElementById('detailReason').textContent = suggestion.reason;
    document.getElementById('detailBenefit').textContent = suggestion.benefit;
    
    // 填充实施建议
    const implementationElement = document.getElementById('detailImplementation');
    implementationElement.innerHTML = `<ol><li>${suggestion.implementation}</li></ol>`;
    
    // 填充相关API
    const relatedApisElement = document.getElementById('detailRelatedApis');
    relatedApisElement.innerHTML = suggestion.relatedApis.map(api => 
        `<span class="badge bg-light text-dark me-2">${api}API</span>`
    ).join('');
    
    // 填充其他信息
    document.getElementById('detailCreatedAt').textContent = formatDateTime(suggestion.createdAt);
    document.getElementById('detailConfidence').textContent = suggestion.confidence + '%';
    
    // 设置采纳和拒绝按钮的数据ID
    document.getElementById('adoptSuggestionBtn').setAttribute('data-id', suggestionId);
    document.getElementById('rejectSuggestionBtn').setAttribute('data-id', suggestionId);
    
    // 禁用/启用按钮
    const isPending = suggestion.status === 'pending';
    document.getElementById('adoptSuggestionBtn').disabled = !isPending;
    document.getElementById('rejectSuggestionBtn').disabled = !isPending;
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('suggestionDetailModal'));
    modal.show();
}

// 采纳建议
function adoptSuggestion(suggestionId) {
    // 显示确认对话框
    if (!confirm('确定要采纳这条建议吗？')) {
        return;
    }
    
    // 模拟API请求
    setTimeout(() => {
        // 重新加载数据
        loadSuggestionsData();
        
        // 关闭模态框（如果在详情模态框中）
        const detailModal = bootstrap.Modal.getInstance(document.getElementById('suggestionDetailModal'));
        if (detailModal) {
            detailModal.hide();
        }
        
        // 显示成功提示
        showSmartTestNotification('建议已采纳', 'success');
    }, 500);
}

// 拒绝建议
function rejectSuggestion(suggestionId) {
    // 显示确认对话框
    if (!confirm('确定要拒绝这条建议吗？')) {
        return;
    }
    
    // 模拟API请求
    setTimeout(() => {
        // 重新加载数据
        loadSuggestionsData();
        
        // 关闭模态框（如果在详情模态框中）
        const detailModal = bootstrap.Modal.getInstance(document.getElementById('suggestionDetailModal'));
        if (detailModal) {
            detailModal.hide();
        }
        
        // 显示成功提示
        showSmartTestNotification('建议已拒绝', 'info');
    }, 500);
}

// 生成新建议
function generateNewSuggestions() {
    const generateBtn = document.getElementById('generateBtn');
    const originalHTML = generateBtn.innerHTML;
    
    // 设置加载状态
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>生成中...';
    generateBtn.disabled = true;
    
    // 模拟API请求
    setTimeout(() => {
        // 恢复按钮状态
        generateBtn.innerHTML = originalHTML;
        generateBtn.disabled = false;
        
        // 重新加载数据
        loadSuggestionsData();
        
        // 显示成功提示
        showSmartTestNotification('新建议已生成', 'success');
    }, 2000);
}

// 刷新建议
function refreshSuggestions() {
    const refreshBtn = document.getElementById('refreshBtn');
    const originalHTML = refreshBtn.innerHTML;
    
    // 设置加载状态
    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>刷新中...';
    refreshBtn.disabled = true;
    
    // 模拟API请求
    setTimeout(() => {
        // 恢复按钮状态
        refreshBtn.innerHTML = originalHTML;
        refreshBtn.disabled = false;
        
        // 重新加载数据
        loadSuggestionsData();
        
        // 显示成功提示
        showSmartTestNotification('建议已刷新', 'success');
    }, 1500);
}

// 绑定事件
function bindEvents() {
    // 刷新按钮
    document.getElementById('refreshBtn').addEventListener('click', function() {
        refreshSuggestions();
    });
    
    // 生成建议按钮
    document.getElementById('generateBtn').addEventListener('click', function() {
        showGenerateModal();
    });
    
    // 空状态生成建议按钮
    document.getElementById('emptyStateGenerateBtn').addEventListener('click', function() {
        showGenerateModal();
    });
    
    // 确认生成建议按钮
    document.getElementById('confirmGenerateBtn').addEventListener('click', function() {
        generateNewSuggestions();
    });
    
    // 采纳建议按钮（详情模态框中）
    document.getElementById('adoptSuggestionBtn').addEventListener('click', function() {
        const suggestionId = this.getAttribute('data-id');
        adoptSuggestion(suggestionId);
    });
    
    // 拒绝建议按钮（详情模态框中）
    document.getElementById('rejectSuggestionBtn').addEventListener('click', function() {
        const suggestionId = this.getAttribute('data-id');
        rejectSuggestion(suggestionId);
    });
}

// 显示生成建议模态框
function showGenerateModal() {
    const modal = new bootstrap.Modal(document.getElementById('generateModal'));
    modal.show();
}

// 获取类别文本
function getCategoryText(category) {
    const categoryMap = {
        'coverage': '覆盖度提升',
        'performance': '性能优化',
        'security': '安全增强',
        'usability': '可用性改进',
        'maintenance': '维护性提升'
    };
    
    return categoryMap[category] || category;
}

// 获取优先级文本
function getPriorityText(priority) {
    const priorityMap = {
        'high': '高优先级',
        'medium': '中优先级',
        'low': '低优先级'
    };
    
    return priorityMap[priority] || priority;
}

// 获取状态文本
function getStatusText(status) {
    const statusMap = {
        'pending': '待处理',
        'adopted': '已采纳',
        'rejected': '已拒绝'
    };
    
    return statusMap[status] || status;
}

// 获取优先级徽章颜色
function getPriorityBadgeColor(priority) {
    const colorMap = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'secondary'
    };
    
    return colorMap[priority] || 'secondary';
}

// 获取状态徽章类
function getStatusClass(status) {
    const classMap = {
        'pending': 'bg-warning text-dark',
        'adopted': 'bg-success',
        'rejected': 'bg-danger'
    };
    
    return classMap[status] || 'bg-secondary';
}

// 格式化日期
function formatDate(date) {
    const options = { year: 'numeric', month: '2-digit', day: '2-digit' };
    return new Date(date).toLocaleDateString('zh-CN', options);
}

// 格式化日期时间
function formatDateTime(date) {
    const options = { 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    return new Date(date).toLocaleString('zh-CN', options);
}

// 显示加载状态
function showLoading() {
    document.getElementById('loadingState').classList.remove('d-none');
    document.getElementById('suggestionsCardView').classList.add('d-none');
    document.getElementById('suggestionsListView').classList.add('d-none');
    document.getElementById('emptyState').classList.add('d-none');
}

// 隐藏加载状态
function hideLoading() {
    document.getElementById('loadingState').classList.add('d-none');
    
    // 根据当前视图模式显示相应内容
    const isCardView = document.getElementById('cardView').checked;
    if (isCardView) {
        document.getElementById('suggestionsCardView').classList.remove('d-none');
    } else {
        document.getElementById('suggestionsListView').classList.remove('d-none');
    }
}

// 显示通知
function showNotification(message, type) {
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