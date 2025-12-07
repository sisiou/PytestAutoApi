/**
 * API配置文件
 * 统一管理API端点配置
 */

// API基础配置
const API_CONFIG = {
    // API服务器基础URL
    BASE_URL: 'http://127.0.0.1:5000',
    
    // API端点路径
    ENDPOINTS: {
        // 文档相关
        DOCS: {
            UPLOAD: '/api/docs/upload',
            LIST: '/api/docs/list',
            PARSE: '/api/docs/parse',
            PARSE_URL: '/api/docs/parse-url',
            UPLOADED_LIST: '/api/docs/uploaded-list',
            DELETE: '/api/docs/delete',
            GENERATE_TEST_CASES: '/api/docs/generate-test-cases/{doc_task_id}',
            EXECUTE_TESTS: '/api/docs/execute-tests',
            ANALYZE_RESULTS: '/api/docs/analyze-results',
            FULL_WORKFLOW: '/api/docs/full-workflow',
            FETCH_FEISHU: '/api/docs/fetch-feishu'
        },
        
        // 测试用例相关
    TEST_CASES: {
        LIST: '/api/test-cases',
        GENERATE: '/api/test-cases/generate',
        DETAIL: '/api/test-cases/{task_id}',
        RUN: '/api/test-cases/{task_id}/run',
        DELETE: '/api/test-cases/{task_id}'
    },
        
        // 覆盖率相关
        COVERAGE: {
            TRENDS: '/api/coverage/trends',
            HEATMAP: '/api/coverage/heatmap',
            LIST: '/api/coverage',
            REFRESH: '/api/coverage/refresh',
            GENERATE: '/api/coverage/generate',
            EXPORT: '/api/coverage/export',
            GENERATE_TEST: '/api/coverage/generate-test'
        },
        
        // 仪表板相关
        DASHBOARD: {
            REFRESH: '/api/dashboard/refresh',
            STATISTICS: '/api/dashboard/statistics',
            RECENT_TESTS: '/api/dashboard/recent-tests',
            SUGGESTIONS: '/api/dashboard/suggestions'
        },
        
        // 场景和关联关系
        SCENES: {
            LIST: '/api/scenes/list',
            CREATE: '/api/scenes/create',
            DELETE: '/api/scenes/delete'
        },
        
        RELATIONS: {
            LIST: '/api/relations/list',
            CREATE: '/api/relations/create',
            DELETE: '/api/relations/delete'
        },
        
        // 系统相关
        SYSTEM: {
            HEALTH: '/api/health',
            STATUS: '/api/status'
        },
        
        // AI相关
        AI: {
            PARSE: '/api/ai/parse'
        }
    }
};

// 构建完整URL的辅助函数
function buildUrl(endpoint) {
    return API_CONFIG.BASE_URL + endpoint;
}

// 导出配置和辅助函数
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API_CONFIG, buildUrl };
} else {
    window.ApiConfig = { API_CONFIG, buildUrl };
    window.API_CONFIG = API_CONFIG; // 添加这行，确保API_CONFIG也可以通过window访问
}