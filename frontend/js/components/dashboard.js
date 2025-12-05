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
    fetch('http://localhost:19028/api/dashboard/refresh', {
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
    fetch('http://localhost:19028/api/dashboard/statistics', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // 更新DOM
        document.getElementById('totalApis').textContent = data.totalApis || 0;
        document.getElementById('totalTestCases').textContent = data.totalTestCases || 0;
        document.getElementById('passRate').textContent = (data.passRate || 0) + '%';
        document.getElementById('coverage').textContent = (data.coverage || 0) + '%';
    })
    .catch(error => {
        console.error('获取统计数据失败:', error);
        
        // 如果API调用失败，使用模拟数据
        const stats = {
            totalApis: 9,
            totalTestCases: 33,
            passRate: 81.8,
            coverage: 0.0
        };
        
        // 更新DOM
        document.getElementById('totalApis').textContent = stats.totalApis;
        document.getElementById('totalTestCases').textContent = stats.totalTestCases;
        document.getElementById('passRate').textContent = stats.passRate + '%';
        document.getElementById('coverage').textContent = stats.coverage + '%';
    });
}

// 更新最新测试执行表格
function updateRecentTestsTable() {
    // 调用API获取数据
    fetch('http://localhost:19028/api/dashboard/recent-tests', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // 构建表格HTML
        let tableHTML = '';
        data.forEach(test => {
            const statusBadge = test.status === 'pass' 
                ? '<span class="badge bg-success">通过</span>' 
                : '<span class="badge bg-danger">失败</span>';
            
            tableHTML += `
                <tr>
                    <td>${test.name}</td>
                    <td>${statusBadge}</td>
                    <td>${test.time}</td>
                </tr>
            `;
        });
        
        // 更新DOM
        document.getElementById('recentTestsTable').innerHTML = tableHTML;
    })
    .catch(error => {
        console.error('获取最新测试执行数据失败:', error);
        
        // 如果API调用失败，使用模拟数据
        const recentTests = [
            { name: '用户注册测试', status: 'pass', time: '2分钟前' },
            { name: '用户登录测试', status: 'pass', time: '5分钟前' },
            { name: '商品浏览测试', status: 'fail', time: '8分钟前' },
            { name: '添加商品到购物车测试', status: 'pass', time: '10分钟前' },
            { name: '创建订单测试', status: 'pass', time: '12分钟前' }
        ];
        
        // 构建表格HTML
        let tableHTML = '';
        recentTests.forEach(test => {
            const statusBadge = test.status === 'pass' 
                ? '<span class="badge bg-success">通过</span>' 
                : '<span class="badge bg-danger">失败</span>';
            
            tableHTML += `
                <tr>
                    <td>${test.name}</td>
                    <td>${statusBadge}</td>
                    <td>${test.time}</td>
                </tr>
            `;
        });
        
        // 更新DOM
        document.getElementById('recentTestsTable').innerHTML = tableHTML;
    });
}

// 更新高优先级建议
function updateHighPrioritySuggestions() {
    // 调用API获取数据
    fetch('http://localhost:19028/api/dashboard/suggestions', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // 构建建议列表HTML
        let suggestionsHTML = '';
        data.forEach((suggestion, index) => {
            const isLast = index === data.length - 1;
            const borderClass = isLast ? '' : 'border-bottom';
            
            const priorityBadge = getPriorityBadge(suggestion.priority);
            
            suggestionsHTML += `
                <div class="suggestion-item p-3 ${borderClass}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${suggestion.title}</h6>
                            <p class="text-muted small mb-2">${suggestion.description}</p>
                            <div>
                                ${priorityBadge}
                                <span class="badge bg-secondary me-1">${suggestion.type}</span>
                                <span class="badge bg-light text-dark">预计工作量: ${suggestion.effort}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        // 更新DOM
        document.getElementById('highPrioritySuggestions').innerHTML = suggestionsHTML;
    })
    .catch(error => {
        console.error('获取高优先级建议数据失败:', error);
        
        // 如果API调用失败，使用模拟数据
        const suggestions = [
            {
                title: '加强认证相关API的安全测试',
                description: '增加对认证相关API的安全测试，包括SQL注入、XSS攻击等常见安全漏洞的测试。',
                priority: 'critical',
                type: '安全测试',
                effort: '4-8小时'
            },
            {
                title: '提高用户注册登录场景功能覆盖度',
                description: '当前功能覆盖度为0.0%，建议增加测试用例以覆盖所有功能点。',
                priority: 'high',
                type: '覆盖度',
                effort: '2-4小时'
            },
            {
                title: '增加商品浏览购买场景的参数覆盖度',
                description: '当前参数覆盖度为0.0%，建议增加不同参数组合的测试用例。',
                priority: 'high',
                type: '覆盖度',
                effort: '3-6小时'
            }
        ];
        
        // 构建建议列表HTML
        let suggestionsHTML = '';
        suggestions.forEach((suggestion, index) => {
            const isLast = index === suggestions.length - 1;
            const borderClass = isLast ? '' : 'border-bottom';
            
            const priorityBadge = getPriorityBadge(suggestion.priority);
            
            suggestionsHTML += `
                <div class="suggestion-item p-3 ${borderClass}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${suggestion.title}</h6>
                            <p class="text-muted small mb-2">${suggestion.description}</p>
                            <div>
                                ${priorityBadge}
                                <span class="badge bg-secondary me-1">${suggestion.type}</span>
                                <span class="badge bg-light text-dark">预计工作量: ${suggestion.effort}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        // 更新DOM
        document.getElementById('highPrioritySuggestions').innerHTML = suggestionsHTML;
    });
}

// 获取优先级徽章HTML
function getPriorityBadge(priority) {
    switch (priority) {
        case 'critical':
            return '<span class="badge bg-danger me-1">关键</span>';
        case 'high':
            return '<span class="badge bg-warning me-1">高</span>';
        case 'medium':
            return '<span class="badge bg-info me-1">中</span>';
        case 'low':
            return '<span class="badge bg-secondary me-1">低</span>';
        default:
            return '<span class="badge bg-secondary me-1">未知</span>';
    }
}

// 更新实时数据
function updateRealTimeData() {
    // 模拟实时数据更新
    // 在实际应用中，这里应该调用API获取最新数据
    
    // 随机更新通过率
    const passRateElement = document.getElementById('passRate');
    const currentPassRate = parseFloat(passRateElement.textContent);
    const newPassRate = Math.max(70, Math.min(95, currentPassRate + (Math.random() - 0.5) * 5));
    passRateElement.textContent = newPassRate.toFixed(1) + '%';
    
    // 随机更新覆盖度
    const coverageElement = document.getElementById('coverage');
    const currentCoverage = parseFloat(coverageElement.textContent);
    const newCoverage = Math.max(0, Math.min(100, currentCoverage + (Math.random() - 0.5) * 2));
    coverageElement.textContent = newCoverage.toFixed(1) + '%';
}