// 仪表板JavaScript功能

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化图表
    initTestTrendChart();
    initCoverageDistributionChart();
    
    // 绑定刷新按钮事件
    document.getElementById('refreshBtn').addEventListener('click', function() {
        refreshDashboardData();
    });
    
    // 模拟实时数据更新
    setInterval(updateRealTimeData, 30000); // 每30秒更新一次
});

// 初始化测试执行趋势图表
function initTestTrendChart() {
    const ctx = document.getElementById('testTrendChart').getContext('2d');
    
    // 生成模拟数据
    const labels = [];
    const passData = [];
    const failData = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
        
        // 模拟数据
        const total = Math.floor(Math.random() * 20) + 25;
        const pass = Math.floor(total * (0.7 + Math.random() * 0.2));
        passData.push(pass);
        failData.push(total - pass);
    }
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '通过',
                    data: passData,
                    backgroundColor: 'rgba(25, 135, 84, 0.2)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: '失败',
                    data: failData,
                    backgroundColor: 'rgba(220, 53, 69, 0.2)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '测试用例数量'
                    }
                }
            }
        }
    });
}

// 初始化覆盖度分布图表
function initCoverageDistributionChart() {
    const ctx = document.getElementById('coverageDistributionChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['功能覆盖度', '参数覆盖度', '异常覆盖度', '业务场景覆盖度', '集成测试覆盖度'],
            datasets: [{
                data: [0, 0, 0, 0, 0], // 模拟数据，实际应从API获取
                backgroundColor: [
                    'rgba(13, 110, 253, 0.7)',
                    'rgba(25, 135, 84, 0.7)',
                    'rgba(255, 193, 7, 0.7)',
                    'rgba(220, 53, 69, 0.7)',
                    'rgba(108, 117, 125, 0.7)'
                ],
                borderColor: [
                    'rgba(13, 110, 253, 1)',
                    'rgba(25, 135, 84, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(220, 53, 69, 1)',
                    'rgba(108, 117, 125, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.raw + '%';
                        }
                    }
                }
            }
        }
    });
}

// 刷新仪表板数据
function refreshDashboardData() {
    const refreshBtn = document.getElementById('refreshBtn');
    
    // 添加刷新动画
    refreshBtn.classList.add('refreshing');
    refreshBtn.disabled = true;
    
    // 调用API获取数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const dashboardEndpoint = endpoints.DASHBOARD || {};
    const refreshUrl = baseUrl + (dashboardEndpoint.REFRESH || '/api/dashboard/refresh');
    
    fetch(refreshUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // 更新统计数据
        updateStatistics();
        
        // 更新最新测试执行表格
        updateRecentTestsTable();
        
        // 更新高优先级建议
        updateHighPrioritySuggestions();
        
        // 移除刷新动画
        refreshBtn.classList.remove('refreshing');
        refreshBtn.disabled = false;
        
        // 显示成功通知
        Notification.success('仪表板数据已更新');
    })
    .catch(error => {
        console.error('刷新仪表板数据失败:', error);
        
        // 如果API调用失败，仍然更新界面
        updateStatistics();
        updateRecentTestsTable();
        updateHighPrioritySuggestions();
        
        // 移除刷新动画
        refreshBtn.classList.remove('refreshing');
        refreshBtn.disabled = false;
        
        // 显示错误通知
        Notification.error('刷新数据失败，显示缓存数据');
    });
}

// 更新统计数据
function updateStatistics() {
    // 调用API获取数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const dashboardEndpoint = endpoints.DASHBOARD || {};
    const statisticsUrl = baseUrl + (dashboardEndpoint.STATISTICS || '/api/dashboard/statistics');
    
    fetch(statisticsUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新API数量
            document.getElementById('apiCount').textContent = data.data.api_count || 0;
            
            // 更新测试用例数量
            document.getElementById('testCaseCount').textContent = data.data.test_case_count || 0;
            
            // 更新执行次数
            document.getElementById('executionCount').textContent = data.data.execution_count || 0;
            
            // 更新成功率
            const successRate = data.data.success_rate || 0;
            document.getElementById('successRate').textContent = successRate.toFixed(1) + '%';
            
            // 更新成功率进度条
            const successRateBar = document.getElementById('successRateBar');
            if (successRateBar) {
                successRateBar.style.width = successRate + '%';
                
                // 根据成功率设置颜色
                if (successRate >= 90) {
                    successRateBar.className = 'progress-bar bg-success';
                } else if (successRate >= 70) {
                    successRateBar.className = 'progress-bar bg-warning';
                } else {
                    successRateBar.className = 'progress-bar bg-danger';
                }
            }
        }
    })
    .catch(error => {
        console.error('获取统计数据失败:', error);
        
        // 使用模拟数据
        document.getElementById('apiCount').textContent = Math.floor(Math.random() * 50) + 10;
        document.getElementById('testCaseCount').textContent = Math.floor(Math.random() * 200) + 50;
        document.getElementById('executionCount').textContent = Math.floor(Math.random() * 1000) + 200;
        
        const successRate = 70 + Math.random() * 25;
        document.getElementById('successRate').textContent = successRate.toFixed(1) + '%';
        
        const successRateBar = document.getElementById('successRateBar');
        if (successRateBar) {
            successRateBar.style.width = successRate + '%';
            
            if (successRate >= 90) {
                successRateBar.className = 'progress-bar bg-success';
            } else if (successRate >= 70) {
                successRateBar.className = 'progress-bar bg-warning';
            } else {
                successRateBar.className = 'progress-bar bg-danger';
            }
        }
    });
}

// 更新最新测试执行表格
function updateRecentTestsTable() {
    // 调用API获取数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const dashboardEndpoint = endpoints.DASHBOARD || {};
    const recentTestsUrl = baseUrl + (dashboardEndpoint.RECENT_TESTS || '/api/dashboard/recent-tests');
    
    fetch(recentTestsUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const tableBody = document.querySelector('#recentTestsTable tbody');
            tableBody.innerHTML = '';
            
            data.data.tests.forEach(test => {
                const row = document.createElement('tr');
                
                // 测试名称
                const nameCell = document.createElement('td');
                nameCell.textContent = test.name;
                row.appendChild(nameCell);
                
                // API
                const apiCell = document.createElement('td');
                apiCell.textContent = test.api;
                row.appendChild(apiCell);
                
                // 状态
                const statusCell = document.createElement('td');
                const statusBadge = document.createElement('span');
                statusBadge.className = 'badge';
                
                if (test.status === '通过') {
                    statusBadge.classList.add('bg-success');
                } else if (test.status === '失败') {
                    statusBadge.classList.add('bg-danger');
                } else {
                    statusBadge.classList.add('bg-secondary');
                }
                
                statusBadge.textContent = test.status;
                statusCell.appendChild(statusBadge);
                row.appendChild(statusCell);
                
                // 执行时间
                const timeCell = document.createElement('td');
                timeCell.textContent = new Date(test.execution_time).toLocaleString();
                row.appendChild(timeCell);
                
                // 耗时
                const durationCell = document.createElement('td');
                durationCell.textContent = test.duration + 'ms';
                row.appendChild(durationCell);
                
                // 操作
                const actionCell = document.createElement('td');
                const viewBtn = document.createElement('button');
                viewBtn.className = 'btn btn-sm btn-outline-primary';
                viewBtn.textContent = '查看';
                viewBtn.addEventListener('click', () => {
                    viewTestResult(test.id);
                });
                actionCell.appendChild(viewBtn);
                row.appendChild(actionCell);
                
                tableBody.appendChild(row);
            });
        }
    })
    .catch(error => {
        console.error('获取最新测试执行数据失败:', error);
        
        // 使用模拟数据
        const tableBody = document.querySelector('#recentTestsTable tbody');
        tableBody.innerHTML = '';
        
        const mockTests = [
            {
                id: 'test_001',
                name: '用户登录测试',
                api: 'POST /api/auth/login',
                status: '通过',
                execution_time: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
                duration: 245
            },
            {
                id: 'test_002',
                name: '获取用户信息测试',
                api: 'GET /api/users/{id}',
                status: '失败',
                execution_time: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
                duration: 523
            },
            {
                id: 'test_003',
                name: '创建订单测试',
                api: 'POST /api/orders',
                status: '通过',
                execution_time: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
                duration: 892
            }
        ];
        
        mockTests.forEach(test => {
            const row = document.createElement('tr');
            
            // 测试名称
            const nameCell = document.createElement('td');
            nameCell.textContent = test.name;
            row.appendChild(nameCell);
            
            // API
            const apiCell = document.createElement('td');
            apiCell.textContent = test.api;
            row.appendChild(apiCell);
            
            // 状态
            const statusCell = document.createElement('td');
            const statusBadge = document.createElement('span');
            statusBadge.className = 'badge';
            
            if (test.status === '通过') {
                statusBadge.classList.add('bg-success');
            } else if (test.status === '失败') {
                statusBadge.classList.add('bg-danger');
            } else {
                statusBadge.classList.add('bg-secondary');
            }
            
            statusBadge.textContent = test.status;
            statusCell.appendChild(statusBadge);
            row.appendChild(statusCell);
            
            // 执行时间
            const timeCell = document.createElement('td');
            timeCell.textContent = new Date(test.execution_time).toLocaleString();
            row.appendChild(timeCell);
            
            // 耗时
            const durationCell = document.createElement('td');
            durationCell.textContent = test.duration + 'ms';
            row.appendChild(durationCell);
            
            // 操作
            const actionCell = document.createElement('td');
            const viewBtn = document.createElement('button');
            viewBtn.className = 'btn btn-sm btn-outline-primary';
            viewBtn.textContent = '查看';
            viewBtn.addEventListener('click', () => {
                viewTestResult(test.id);
            });
            actionCell.appendChild(viewBtn);
            row.appendChild(actionCell);
            
            tableBody.appendChild(row);
        });
    });
}

// 更新高优先级建议
function updateHighPrioritySuggestions() {
    // 调用API获取数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const dashboardEndpoint = endpoints.DASHBOARD || {};
    const suggestionsUrl = baseUrl + (dashboardEndpoint.SUGGESTIONS || '/api/dashboard/suggestions');
    
    fetch(suggestionsUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const suggestionsList = document.getElementById('highPrioritySuggestions');
            suggestionsList.innerHTML = '';
            
            if (data.data.suggestions.length === 0) {
                const emptyMessage = document.createElement('li');
                emptyMessage.className = 'list-group-item text-center text-muted';
                emptyMessage.textContent = '暂无建议';
                suggestionsList.appendChild(emptyMessage);
                return;
            }
            
            data.data.suggestions.forEach(suggestion => {
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item';
                
                const header = document.createElement('div');
                header.className = 'd-flex w-100 justify-content-between';
                
                const title = document.createElement('h6');
                title.className = 'mb-1';
                title.textContent = suggestion.title;
                header.appendChild(title);
                
                const priority = document.createElement('span');
                priority.className = 'badge';
                
                if (suggestion.priority === '高') {
                    priority.classList.add('bg-danger');
                } else if (suggestion.priority === '中') {
                    priority.classList.add('bg-warning');
                } else {
                    priority.classList.add('bg-info');
                }
                
                priority.textContent = suggestion.priority;
                header.appendChild(priority);
                
                listItem.appendChild(header);
                
                const description = document.createElement('p');
                description.className = 'mb-1';
                description.textContent = suggestion.description;
                listItem.appendChild(description);
                
                const actions = document.createElement('div');
                actions.className = 'd-flex justify-content-end';
                
                const applyBtn = document.createElement('button');
                applyBtn.className = 'btn btn-sm btn-outline-primary me-2';
                applyBtn.textContent = '应用';
                applyBtn.addEventListener('click', () => {
                    applySuggestion(suggestion.id);
                });
                actions.appendChild(applyBtn);
                
                const ignoreBtn = document.createElement('button');
                ignoreBtn.className = 'btn btn-sm btn-outline-secondary';
                ignoreBtn.textContent = '忽略';
                ignoreBtn.addEventListener('click', () => {
                    ignoreSuggestion(suggestion.id);
                });
                actions.appendChild(ignoreBtn);
                
                listItem.appendChild(actions);
                suggestionsList.appendChild(listItem);
            });
        }
    })
    .catch(error => {
        console.error('获取建议数据失败:', error);
        
        // 使用模拟数据
        const suggestionsList = document.getElementById('highPrioritySuggestions');
        suggestionsList.innerHTML = '';
        
        const mockSuggestions = [
            {
                id: 'suggestion_001',
                title: '增加异常场景测试',
                description: '发现部分API缺少异常输入场景的测试用例，建议增加相关测试以提高代码健壮性。',
                priority: '高'
            },
            {
                id: 'suggestion_002',
                title: '优化测试数据',
                description: '部分测试用例使用重复数据，建议使用动态生成的测试数据以提高测试覆盖率。',
                priority: '中'
            },
            {
                id: 'suggestion_003',
                title: '添加业务流程测试',
                description: '建议添加跨API的业务流程测试，以验证系统整体功能。',
                priority: '中'
            }
        ];
        
        mockSuggestions.forEach(suggestion => {
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item';
            
            const header = document.createElement('div');
            header.className = 'd-flex w-100 justify-content-between';
            
            const title = document.createElement('h6');
            title.className = 'mb-1';
            title.textContent = suggestion.title;
            header.appendChild(title);
            
            const priority = document.createElement('span');
            priority.className = 'badge';
            
            if (suggestion.priority === '高') {
                priority.classList.add('bg-danger');
            } else if (suggestion.priority === '中') {
                priority.classList.add('bg-warning');
            } else {
                priority.classList.add('bg-info');
            }
            
            priority.textContent = suggestion.priority;
            header.appendChild(priority);
            
            listItem.appendChild(header);
            
            const description = document.createElement('p');
            description.className = 'mb-1';
            description.textContent = suggestion.description;
            listItem.appendChild(description);
            
            const actions = document.createElement('div');
            actions.className = 'd-flex justify-content-end';
            
            const applyBtn = document.createElement('button');
            applyBtn.className = 'btn btn-sm btn-outline-primary me-2';
            applyBtn.textContent = '应用';
            applyBtn.addEventListener('click', () => {
                applySuggestion(suggestion.id);
            });
            actions.appendChild(applyBtn);
            
            const ignoreBtn = document.createElement('button');
            ignoreBtn.className = 'btn btn-sm btn-outline-secondary';
            ignoreBtn.textContent = '忽略';
            ignoreBtn.addEventListener('click', () => {
                ignoreSuggestion(suggestion.id);
            });
            actions.appendChild(ignoreBtn);
            
            listItem.appendChild(actions);
            suggestionsList.appendChild(listItem);
        });
    });
}

// 查看测试结果
function viewTestResult(testId) {
    // 跳转到测试结果页面
    window.location.href = `test-result.html?test_id=${testId}`;
}

// 应用建议
function applySuggestion(suggestionId) {
    // 调用API应用建议
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const dashboardEndpoint = endpoints.DASHBOARD || {};
    const applyUrl = baseUrl + (dashboardEndpoint.APPLY_SUGGESTION || '/api/dashboard/apply-suggestion');
    
    fetch(applyUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            suggestion_id: suggestionId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Notification.success('建议已应用');
            // 刷新建议列表
            updateHighPrioritySuggestions();
        } else {
            Notification.error('应用建议失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('应用建议失败:', error);
        Notification.error('应用建议失败');
    });
}

// 忽略建议
function ignoreSuggestion(suggestionId) {
    // 调用API忽略建议
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const dashboardEndpoint = endpoints.DASHBOARD || {};
    const ignoreUrl = baseUrl + (dashboardEndpoint.IGNORE_SUGGESTION || '/api/dashboard/ignore-suggestion');
    
    fetch(ignoreUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            suggestion_id: suggestionId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Notification.success('建议已忽略');
            // 刷新建议列表
            updateHighPrioritySuggestions();
        } else {
            Notification.error('忽略建议失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('忽略建议失败:', error);
        Notification.error('忽略建议失败');
    });
}

// 更新实时数据
function updateRealTimeData() {
    // 更新统计数据
    updateStatistics();
    
    // 更新最新测试执行表格
    updateRecentTestsTable();
}