/**
 * API配置文件
 * 包含API基础URL和AI问答功能所需的API参数
 */

// API基础URL配置
export const apiConfig = {
  // 后端API基础URL
  baseURL: 'http://127.0.0.1:8000',
}

export const aiChatConfig = {
 apiEndpoint: 'http://127.0.0.1:8000/api/ai/chat',
  // OpenAI API地址
  apiEndpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
  
  // API Key
  apiKey: 'sk-9c4d89982a6a4bd3b7494d94751fe81c',
  
  // 使用的模型
  model: 'qwen3-max-preview'
}
};