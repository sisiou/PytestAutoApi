// 覆盖度报告页面JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initCoveragePage();
    
    // 加载数据
    loadCoverageData();
    
    // 绑定事件
    bindEvents();
});

// 页面初始化
function initCoveragePage() {
    // 初始化覆盖度圆形进度条
    initCoverageCircles();
    
    // 初始化趋势图
    initTrendChart();
    
    // 初始化热力图
    initHeatmap();
}

// 初始化覆盖度圆形进度条
function initCoverageCircles() {
    const circles = document.querySelectorAll('.coverage-circle');
    
    circles.forEach(circle => {
        const percent = parseInt(circle.getAttribute('data-percent'));
        const circleElement = circle.querySelector('circle:last-child');
        const textElement = circle.querySelector('.coverage-text');
        
        if (circleElement && textElement) {
            // 设置圆形进度条
            const radius = 50;
            const circumference = 2 * Math.PI * radius;
            const offset = circumference - (percent / 100) * circumference;
            
            circleElement.style.strokeDasharray = circumference;
            circleElement.style.strokeDashoffset = circumference;
            
            // 动画效果
            setTimeout(() => {
                circleElement.style.transition = 'stroke-dashoffset 1.5s ease-in-out';
                circleElement.style.strokeDashoffset = offset;
            }, 100);
            
            // 数字动画
            animateValue(textElement, 0, percent, 1500);
        }
    });
}

// 数字动画效果
function animateValue(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        element.textContent = value + '%';
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// 初始化趋势图
function initTrendChart() {
    const ctx = document.getElementById('coverageTrendChart').getContext('2d');
    
    // 调用API获取趋势数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const trendsUrl = baseUrl + (coverageEndpoint.TRENDS || '/api/coverage/trends') + '?period=week';
    
    fetch(trendsUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取趋势数据失败');
        }
        return response.json();
    })
    .then(data => {
        // 使用API返回的数据初始化图表
        window.coverageTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'API覆盖度',
                        data: data.apiData,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '场景覆盖度',
                        data: data.scenarioData,
                        borderColor: '#198754',
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '参数覆盖度',
                        data: data.parameterData,
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '综合覆盖度',
                        data: data.overallData,
                        borderColor: '#6f42c1',
                        backgroundColor: 'rgba(111, 66, 193, 0.1)',
                        tension: 0.4,
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
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.raw + '%';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    })
    .catch(error => {
        console.error('获取趋势数据失败:', error);
        
        // 如果API调用失败，生成模拟数据作为回退
        const labels = [];
        const apiData = [];
        const scenarioData = [];
        const parameterData = [];
        const overallData = [];
        
        // 生成最近7天的日期
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
            
            // 生成随机但合理的覆盖度数据
            apiData.push(Math.floor(Math.random() * 10) + 80);
            scenarioData.push(Math.floor(Math.random() * 15) + 65);
            parameterData.push(Math.floor(Math.random() * 20) + 60);
            overallData.push(Math.floor(Math.random() * 12) + 70);
        }
        
        window.coverageTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'API覆盖度',
                        data: apiData,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '场景覆盖度',
                        data: scenarioData,
                        borderColor: '#198754',
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '参数覆盖度',
                        data: parameterData,
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '综合覆盖度',
                        data: overallData,
                        borderColor: '#6f42c1',
                        backgroundColor: 'rgba(111, 66, 193, 0.1)',
                        tension: 0.4,
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
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.raw + '%';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        
        // 显示错误提示
        showSmartTestNotification('无法获取最新覆盖度趋势数据，显示模拟数据', 'warning');
    });
}

// 初始化热力图
function initHeatmap() {
    const heatmapContainer = document.getElementById('coverageHeatmap');
    
    // 调用API获取热力图数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const heatmapUrl = baseUrl + (coverageEndpoint.HEATMAP || '/api/coverage/heatmap');
    
    fetch(heatmapUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取热力图数据失败');
        }
        return response.json();
    })
    .then(data => {
        // 使用API返回的数据生成热力图
        let heatmapHTML = '<div class="heatmap-container">';
        
        // 添加表头
        heatmapHTML += '<div class="heatmap-row">';
        heatmapHTML += '<div class="heatmap-label"></div>';
        heatmapHTML += '<div class="heatmap-cells">';
        data.scenarios.forEach(scenario => {
            heatmapHTML += `<div class="heatmap-label text-center">${scenario}</div>`;
        });
        heatmapHTML += '</div></div>';
        
        // 添加数据行
        data.apis.forEach(api => {
            heatmapHTML += '<div class="heatmap-row">';
            heatmapHTML += `<div class="heatmap-label">${api}</div>`;
            heatmapHTML += '<div class="heatmap-cells">';
            
            data.scenarios.forEach(scenario => {
                // 从API数据中获取覆盖度值
                const coverage = data.coverageData[api][scenario];
                const color = getHeatmapColor(coverage);
                
                heatmapHTML += `<div class="heatmap-cell" style="background-color: ${color};" title="${api} - ${scenario}: ${coverage}%">${coverage}</div>`;
            });
            
            heatmapHTML += '</div></div>';
        });
        
        heatmapHTML += '</div>';
        
        // 添加图例
        heatmapHTML += '<div class="heatmap-legend">';
        const legendItems = [
            { color: '#dc3545', label: '0-25%' },
            { color: '#fd7e14', label: '26-50%' },
            { color: '#ffc107', label: '51-75%' },
            { color: '#198754', label: '76-100%' }
        ];
        
        legendItems.forEach(item => {
            heatmapHTML += `<div class="heatmap-legend-item">`;
            heatmapHTML += `<div class="heatmap-legend-color" style="background-color: ${item.color};"></div>`;
            heatmapHTML += `<span>${item.label}</span>`;
            heatmapHTML += `</div>`;
        });
        
        heatmapHTML += '</div>';
        
        heatmapContainer.innerHTML = heatmapHTML;
    })
    .catch(error => {
        console.error('获取热力图数据失败:', error);
        
        // 如果API调用失败，生成模拟数据作为回退
        const apis = ['用户管理', '订单处理', '支付接口', '库存管理', '数据分析', '通知服务'];
        const scenarios = ['正常流程', '异常处理', '边界条件', '并发测试', '性能测试', '安全测试'];
        
        let heatmapHTML = '<div class="heatmap-container">';
        
        // 添加表头
        heatmapHTML += '<div class="heatmap-row">';
        heatmapHTML += '<div class="heatmap-label"></div>';
        heatmapHTML += '<div class="heatmap-cells">';
        scenarios.forEach(scenario => {
            heatmapHTML += `<div class="heatmap-label text-center">${scenario}</div>`;
        });
        heatmapHTML += '</div></div>';
        
        // 添加数据行
        apis.forEach(api => {
            heatmapHTML += '<div class="heatmap-row">';
            heatmapHTML += `<div class="heatmap-label">${api}</div>`;
            heatmapHTML += '<div class="heatmap-cells">';
            
            scenarios.forEach(scenario => {
                // 生成随机覆盖度值
                const coverage = Math.floor(Math.random() * 100);
                const color = getHeatmapColor(coverage);
                
                heatmapHTML += `<div class="heatmap-cell" style="background-color: ${color};" title="${api} - ${scenario}: ${coverage}%">${coverage}</div>`;
            });
            
            heatmapHTML += '</div></div>';
        });
        
        heatmapHTML += '</div>';
        
        // 添加图例
        heatmapHTML += '<div class="heatmap-legend">';
        const legendItems = [
            { color: '#dc3545', label: '0-25%' },
            { color: '#fd7e14', label: '26-50%' },
            { color: '#ffc107', label: '51-75%' },
            { color: '#198754', label: '76-100%' }
        ];
        
        legendItems.forEach(item => {
            heatmapHTML += `<div class="heatmap-legend-item">`;
            heatmapHTML += `<div class="heatmap-legend-color" style="background-color: ${item.color};"></div>`;
            heatmapHTML += `<span>${item.label}</span>`;
            heatmapHTML += `</div>`;
        });
        
        heatmapHTML += '</div>';
        
        heatmapContainer.innerHTML = heatmapHTML;
        
        // 显示错误提示
        showSmartTestNotification('无法获取最新热力图数据，显示模拟数据', 'warning');
    });
}

// 获取热力图颜色
function getHeatmapColor(value) {
    if (value <= 25) return '#dc3545';
    if (value <= 50) return '#fd7e14';
    if (value <= 75) return '#ffc107';
    return '#198754';
}

// 加载覆盖度数据
function loadCoverageData() {
    // 显示加载状态
    showLoading();
    
    // 从API获取覆盖度数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const listUrl = baseUrl + (coverageEndpoint.LIST || '/api/coverage/list');
    
    fetch(listUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取覆盖度数据失败');
        }
        return response.json();
    })
    .then(data => {
        // 加载API覆盖度数据
        loadApiCoverageData(data.apiCoverage);
        
        // 加载场景覆盖度数据
        loadScenarioCoverageData(data.scenarioCoverage);
        
        // 加载未覆盖部分数据
        loadUncoveredData(data.uncovered);
        
        // 隐藏加载状态
        hideLoading();
    })
    .catch(error => {
        console.error('加载覆盖度数据失败:', error);
        
        // 如果API调用失败，使用模拟数据
        // 加载API覆盖度数据
        loadApiCoverageData();
        
        // 加载场景覆盖度数据
        loadScenarioCoverageData();
        
        // 加载未覆盖部分数据
        loadUncoveredData();
        
        // 隐藏加载状态
        hideLoading();
        
        // 显示错误提示
        showSmartTestNotification('无法获取最新覆盖度数据，显示模拟数据', 'warning');
    });
}

// 加载API覆盖度数据
function loadApiCoverageData(apiData) {
    const apiCoverageTable = document.getElementById('apiCoverageTable');
    
    // 如果没有提供数据，使用模拟数据
    if (!apiData) {
        apiData = [
            { name: '用户注册API', coverage: 95, status: 'high' },
            { name: '用户登录API', coverage: 92, status: 'high' },
            { name: '订单创建API', coverage: 88, status: 'high' },
            { name: '订单查询API', coverage: 85, status: 'high' },
            { name: '支付处理API', coverage: 78, status: 'medium' },
            { name: '库存更新API', coverage: 72, status: 'medium' },
            { name: '数据分析API', coverage: 65, status: 'medium' },
            { name: '通知发送API', coverage: 58, status: 'low' },
            { name: '报表生成API', coverage: 45, status: 'low' },
            { name: '系统配置API', coverage: 32, status: 'low' }
        ];
    }
    
    let tableHTML = '';
    
    apiData.forEach(api => {
        const statusClass = api.status === 'high' ? 'coverage-high' : 
                           api.status === 'medium' ? 'coverage-medium' : 'coverage-low';
        const statusText = api.status === 'high' ? '高' : 
                          api.status === 'medium' ? '中' : '低';
        
        tableHTML += `
            <tr>
                <td>${api.name}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress flex-grow-1 me-2" style="height: 8px;">
                            <div class="progress-bar" role="progressbar" style="width: ${api.coverage}%; background-color: ${getProgressBarColor(api.coverage)};"></div>
                        </div>
                        <span class="text-muted small">${api.coverage}%</span>
                    </div>
                </td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
            </tr>
        `;
    });
    
    apiCoverageTable.innerHTML = tableHTML;
}

// 加载场景覆盖度数据
function loadScenarioCoverageData(scenarioData) {
    const scenarioCoverageTable = document.getElementById('scenarioCoverageTable');
    
    // 如果没有提供数据，使用模拟数据
    if (!scenarioData) {
        scenarioData = [
            { name: '用户注册流程', coverage: 90, status: 'high' },
            { name: '用户登录流程', coverage: 88, status: 'high' },
            { name: '订单创建流程', coverage: 85, status: 'high' },
            { name: '支付处理流程', coverage: 80, status: 'high' },
            { name: '库存管理流程', coverage: 75, status: 'medium' },
            { name: '数据分析流程', coverage: 70, status: 'medium' },
            { name: '异常处理流程', coverage: 65, status: 'medium' },
            { name: '并发测试场景', coverage: 55, status: 'low' },
            { name: '性能测试场景', coverage: 45, status: 'low' },
            { name: '安全测试场景', coverage: 35, status: 'low' }
        ];
    }
    
    let tableHTML = '';
    
    scenarioData.forEach(scenario => {
        const statusClass = scenario.status === 'high' ? 'coverage-high' : 
                           scenario.status === 'medium' ? 'coverage-medium' : 'coverage-low';
        const statusText = scenario.status === 'high' ? '高' : 
                          scenario.status === 'medium' ? '中' : '低';
        
        tableHTML += `
            <tr>
                <td>${scenario.name}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress flex-grow-1 me-2" style="height: 8px;">
                            <div class="progress-bar" role="progressbar" style="width: ${scenario.coverage}%; background-color: ${getProgressBarColor(scenario.coverage)};"></div>
                        </div>
                        <span class="text-muted small">${scenario.coverage}%</span>
                    </div>
                </td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
            </tr>
        `;
    });
    
    scenarioCoverageTable.innerHTML = tableHTML;
}

// 加载未覆盖部分数据
function loadUncoveredData(uncoveredData) {
    // 如果没有提供数据，使用模拟数据
    if (!uncoveredData) {
        uncoveredData = {
            apis: [
                { name: '用户注销API', description: '用户注销账户的API接口', priority: 'high' },
                { name: '订单取消API', description: '取消未支付订单的API接口', priority: 'medium' },
                { name: '批量导入API', description: '批量导入数据的API接口', priority: 'low' }
            ],
            scenarios: [
                { name: '用户权限变更场景', description: '用户权限变更的测试场景', priority: 'high' },
                { name: '订单退款场景', description: '订单退款处理的测试场景', priority: 'high' },
                { name: '库存预警场景', description: '库存不足预警的测试场景', priority: 'medium' },
                { name: '数据备份场景', description: '系统数据备份的测试场景', priority: 'medium' },
                { name: '系统升级场景', description: '系统升级过程的测试场景', priority: 'low' }
            ],
            params: [
                { name: '用户注册API - 验证码参数', description: '用户注册时的验证码参数', priority: 'high' },
                { name: '订单创建API - 优惠券参数', description: '订单创建时的优惠券参数', priority: 'high' },
                { name: '支付处理API - 分期付款参数', description: '支付处理时的分期付款参数', priority: 'medium' },
                { name: '库存更新API - 批量操作参数', description: '库存更新时的批量操作参数', priority: 'medium' },
                { name: '数据分析API - 时间范围参数', description: '数据分析时的时间范围参数', priority: 'medium' },
                { name: '通知发送API - 模板参数', description: '通知发送时的模板参数', priority: 'low' },
                { name: '报表生成API - 格式参数', description: '报表生成时的格式参数', priority: 'low' },
                { name: '系统配置API - 安全参数', description: '系统配置时的安全参数', priority: 'low' }
            ]
        };
    }
    
    // 加载未覆盖的API
    const uncoveredApisList = document.getElementById('uncoveredApisList');
    const uncoveredApis = uncoveredData.apis || [];
    
    let apisHTML = '';
    uncoveredApis.forEach(api => {
        const priorityClass = `priority-${api.priority}`;
        const priorityText = api.priority === 'high' ? '高' : 
                            api.priority === 'medium' ? '中' : '低';
        
        apisHTML += `
            <li class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="uncovered-title">
                            ${api.name}
                            <span class="uncovered-priority ${priorityClass}">${priorityText}优先级</span>
                        </div>
                        <div class="uncovered-description">${api.description}</div>
                    </div>
                    <button class="btn btn-sm btn-outline-primary ms-2">生成测试</button>
                </div>
            </li>
        `;
    });
    
    uncoveredApisList.innerHTML = apisHTML;
    
    // 加载未覆盖的场景
    const uncoveredScenariosList = document.getElementById('uncoveredScenariosList');
    const uncoveredScenarios = uncoveredData.scenarios || [];
    
    let scenariosHTML = '';
    uncoveredScenarios.forEach(scenario => {
        const priorityClass = `priority-${scenario.priority}`;
        const priorityText = scenario.priority === 'high' ? '高' : 
                            scenario.priority === 'medium' ? '中' : '低';
        
        scenariosHTML += `
            <li class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="uncovered-title">
                            ${scenario.name}
                            <span class="uncovered-priority ${priorityClass}">${priorityText}优先级</span>
                        </div>
                        <div class="uncovered-description">${scenario.description}</div>
                    </div>
                    <button class="btn btn-sm btn-outline-primary ms-2">生成测试</button>
                </div>
            </li>
        `;
    });
    
    uncoveredScenariosList.innerHTML = scenariosHTML;
    
    // 加载未覆盖的参数
    const uncoveredParamsList = document.getElementById('uncoveredParamsList');
    const uncoveredParams = uncoveredData.params || [];
    
    let paramsHTML = '';
    uncoveredParams.forEach(param => {
        const priorityClass = `priority-${param.priority}`;
        const priorityText = param.priority === 'high' ? '高' : 
                            param.priority === 'medium' ? '中' : '低';
        
        paramsHTML += `
            <li class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="uncovered-title">
                            ${param.name}
                            <span class="uncovered-priority ${priorityClass}">${priorityText}优先级</span>
                        </div>
                        <div class="uncovered-description">${param.description}</div>
                    </div>
                    <button class="btn btn-sm btn-outline-primary ms-2">生成测试</button>
                </div>
            </li>
        `;
    });
    
    uncoveredParamsList.innerHTML = paramsHTML;
}

// 获取进度条颜色
function getProgressBarColor(coverage) {
    if (coverage >= 80) return '#198754';
    if (coverage >= 60) return '#ffc107';
    return '#dc3545';
}

// 绑定事件
function bindEvents() {
    // 刷新按钮
    document.getElementById('refreshBtn').addEventListener('click', function() {
        refreshData();
    });
    
    // 生成报告按钮
    document.getElementById('generateBtn').addEventListener('click', function() {
        showGenerateModal();
    });
    
    // 导出报告按钮
    document.getElementById('exportBtn').addEventListener('click', function() {
        showExportModal();
    });
    
    // 确认生成报告按钮
    document.getElementById('confirmGenerateBtn').addEventListener('click', function() {
        generateReport();
    });
    
    // 确认导出报告按钮
    document.getElementById('confirmExportBtn').addEventListener('click', function() {
        exportReport();
    });
    
    // 趋势图时间范围选择
    document.querySelectorAll('input[name="trendPeriod"]').forEach(radio => {
        radio.addEventListener('change', function() {
            updateTrendChart(this.value);
        });
    });
    
    // 未覆盖部分生成测试按钮
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-outline-primary') && e.target.textContent === '生成测试') {
            generateTestForUncovered(e.target);
        }
    });
}

// 刷新数据
function refreshData() {
    const refreshBtn = document.getElementById('refreshBtn');
    const originalHTML = refreshBtn.innerHTML;
    
    // 设置加载状态
    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>刷新中...';
    refreshBtn.disabled = true;
    
    // 调用API刷新数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const refreshUrl = baseUrl + (coverageEndpoint.REFRESH || '/api/coverage/refresh');
    
    fetch(refreshUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('刷新数据失败');
        }
        return response.json();
    })
    .then(data => {
        // 重新加载数据
        loadCoverageData();
        
        // 恢复按钮状态
        refreshBtn.innerHTML = originalHTML;
        refreshBtn.disabled = false;
        
        // 显示成功提示
        showSmartTestNotification('数据已刷新', 'success');
    })
    .catch(error => {
        console.error('刷新数据失败:', error);
        
        // 即使API调用失败，也重新加载数据
        loadCoverageData();
        
        // 恢复按钮状态
        refreshBtn.innerHTML = originalHTML;
        refreshBtn.disabled = false;
        
        // 显示错误提示
        showSmartTestNotification('刷新数据失败，请稍后再试', 'danger');
    });
}

// 显示生成报告模态框
function showGenerateModal() {
    const modal = new bootstrap.Modal(document.getElementById('generateModal'));
    modal.show();
}

// 显示导出报告模态框
function showExportModal() {
    const modal = new bootstrap.Modal(document.getElementById('exportModal'));
    modal.show();
}

// 生成报告
function generateReport() {
    const generateBtn = document.getElementById('confirmGenerateBtn');
    const originalHTML = generateBtn.innerHTML;
    
    // 设置加载状态
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>生成中...';
    generateBtn.disabled = true;
    
    // 获取表单数据
    const reportType = document.querySelector('input[name="reportType"]:checked').value;
    const dateRange = document.getElementById('dateRange').value;
    
    // 调用API生成报告
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const generateUrl = baseUrl + (coverageEndpoint.GENERATE || '/api/coverage/generate');
    
    fetch(generateUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            reportType: reportType,
            dateRange: dateRange
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('生成报告失败');
        }
        return response.json();
    })
    .then(data => {
        // 恢复按钮状态
        generateBtn.innerHTML = originalHTML;
        generateBtn.disabled = false;
        
        // 关闭模态框
        bootstrap.Modal.getInstance(document.getElementById('generateModal')).hide();
        
        // 显示成功提示
        showSmartTestNotification('报告生成成功', 'success');
        
        // 刷新数据
        loadCoverageData();
    })
    .catch(error => {
        console.error('生成报告失败:', error);
        
        // 恢复按钮状态
        generateBtn.innerHTML = originalHTML;
        generateBtn.disabled = false;
        
        // 显示错误提示
        showSmartTestNotification('生成报告失败，请稍后再试', 'danger');
    });
}

// 导出报告
function exportReport() {
    const exportBtn = document.getElementById('confirmExportBtn');
    const originalHTML = exportBtn.innerHTML;
    
    // 设置加载状态
    exportBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>导出中...';
    exportBtn.disabled = true;
    
    // 获取表单数据
    const format = document.getElementById('exportFormat').value;
    const fileName = document.getElementById('exportFileName').value;
    const includeDetails = document.getElementById('includeDetails').checked;
    const dateRange = document.getElementById('exportDateRange').value;
    
    // 调用API导出报告
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const exportUrl = baseUrl + (coverageEndpoint.EXPORT || '/api/coverage/export');
    
    fetch(exportUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            format: format,
            fileName: fileName,
            includeDetails: includeDetails,
            dateRange: dateRange
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('导出报告失败');
        }
        return response.blob();
    })
    .then(blob => {
        // 恢复按钮状态
        exportBtn.innerHTML = originalHTML;
        exportBtn.disabled = false;
        
        // 关闭模态框
        bootstrap.Modal.getInstance(document.getElementById('exportModal')).hide();
        
        // 创建下载链接
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${fileName}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        // 显示成功提示
        showSmartTestNotification(`报告已导出为 ${format.toUpperCase()} 格式`, 'success');
    })
    .catch(error => {
        console.error('导出报告失败:', error);
        
        // 恢复按钮状态
        exportBtn.innerHTML = originalHTML;
        exportBtn.disabled = false;
        
        // 显示错误提示
        showSmartTestNotification('导出报告失败，请稍后再试', 'danger');
    });
}

// 更新趋势图
function updateTrendChart(period) {
    // 调用API获取趋势数据
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const trendsUrl = baseUrl + (coverageEndpoint.TRENDS || '/api/coverage/trends') + `?period=${period}`;
    
    fetch(trendsUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取趋势数据失败');
        }
        return response.json();
    })
    .then(data => {
        // 使用API返回的数据更新图表
        window.coverageTrendChart.data.labels = data.labels;
        window.coverageTrendChart.data.datasets[0].data = data.apiData;
        window.coverageTrendChart.data.datasets[1].data = data.scenarioData;
        window.coverageTrendChart.data.datasets[2].data = data.parameterData;
        window.coverageTrendChart.data.datasets[3].data = data.overallData;
        
        // 刷新图表
        window.coverageTrendChart.update();
    })
    .catch(error => {
        console.error('获取趋势数据失败:', error);
        
        // 如果API调用失败，生成模拟数据作为回退
        let labels = [];
        let apiData = [];
        let scenarioData = [];
        let parameterData = [];
        let overallData = [];
        
        // 根据时间范围生成数据
        let days = 7; // 默认7天
        if (period === 'monthTrend') days = 30;
        if (period === 'quarterTrend') days = 90;
        
        // 生成日期标签和数据
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            
            // 根据天数调整标签格式
            if (days <= 7) {
                labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
            } else if (days <= 30) {
                // 每5天显示一个标签
                if (i % 5 === 0) {
                    labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
                } else {
                    labels.push('');
                }
            } else {
                // 每15天显示一个标签
                if (i % 15 === 0) {
                    labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
                } else {
                    labels.push('');
                }
            }
            
            // 生成随机但合理的覆盖度数据
            apiData.push(Math.floor(Math.random() * 10) + 80);
            scenarioData.push(Math.floor(Math.random() * 15) + 65);
            parameterData.push(Math.floor(Math.random() * 20) + 60);
            overallData.push(Math.floor(Math.random() * 12) + 70);
        }
        
        // 更新图表数据
        window.coverageTrendChart.data.labels = labels;
        window.coverageTrendChart.data.datasets[0].data = apiData;
        window.coverageTrendChart.data.datasets[1].data = scenarioData;
        window.coverageTrendChart.data.datasets[2].data = parameterData;
        window.coverageTrendChart.data.datasets[3].data = overallData;
        
        // 刷新图表
        window.coverageTrendChart.update();
        
        // 显示错误提示
        showSmartTestNotification('无法获取最新趋势数据，显示模拟数据', 'warning');
    });
}

// 为未覆盖部分生成测试
function generateTestForUncovered(button) {
    const originalHTML = button.innerHTML;
    
    // 设置加载状态
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>生成中';
    button.disabled = true;
    
    // 获取未覆盖项的信息
    const listItem = button.closest('.list-group-item');
    const titleElement = listItem.querySelector('.uncovered-title').textContent.trim();
    const descriptionElement = listItem.querySelector('.uncovered-description').textContent.trim();
    
    // 调用API生成测试
    const baseUrl = window.API_CONFIG ? window.API_CONFIG.BASE_URL || 'http://127.0.0.1:5000' : 'http://127.0.0.1:5000';
    const endpoints = window.API_CONFIG ? window.API_CONFIG.ENDPOINTS || {} : {};
    const coverageEndpoint = endpoints.COVERAGE || {};
    const generateTestUrl = baseUrl + (coverageEndpoint.GENERATE_TEST || '/api/coverage/generate-test');
    
    fetch(generateTestUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: titleElement,
            description: descriptionElement
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('生成测试失败');
        }
        return response.json();
    })
    .then(data => {
        // 恢复按钮状态
        button.innerHTML = '已生成';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-success');
        
        // 显示成功提示
        showSmartTestNotification('测试用例生成成功', 'success');
        
        // 刷新数据
        loadCoverageData();
    })
    .catch(error => {
        console.error('生成测试失败:', error);
        
        // 恢复按钮状态
        button.innerHTML = originalHTML;
        button.disabled = false;
        
        // 显示错误提示
        showSmartTestNotification('生成测试失败，请稍后再试', 'danger');
    });
}

// 显示加载状态
function showLoading() {
    // 这里可以添加全局加载状态的显示逻辑
}

// 隐藏加载状态
function hideLoading() {
    // 这里可以添加全局加载状态的隐藏逻辑
}