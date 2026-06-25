<template>
  <div class="ai-chat-container">
    <van-nav-bar title="AI问答" fixed />
    
    <!-- 角色选择器 -->
    <div class="role-selector">
      <van-dropdown-menu>
        <van-dropdown-item v-model="currentRole" :options="roleOptions" />
      </van-dropdown-menu>
    </div>

    <div class="chat-content">
      <div class="messages-container" ref="messagesContainer">
        <div 
          v-for="(message, index) in messages" 
          :key="index" 
          :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']"
        >
          <div class="message-content" v-html="formatMessage(message.content)"></div>
        </div>
      </div>
      
      <div class="input-container">
        <van-field
          v-model="userInput"
          rows="1"
          autosize
          type="textarea"
          placeholder="请输入问题..."
          class="chat-input"
          @keypress.enter.prevent="sendMessage"
        />
        <van-button 
          type="primary" 
          class="send-button" 
          :disabled="isLoading || !userInput.trim()" 
          @click="sendMessage"
        >
          发送
        </van-button>
      </div>
    </div>
    
    <tab-bar />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import TabBar from '../components/TabBar.vue';
import { showToast } from 'vant';
import * as marked from 'marked';
import DOMPurify from 'dompurify';
import { aiChatConfig } from '../config/api';
import { useUserStore } from '../store/user';
import axios from 'axios';

const userStore = useUserStore();
const messages = ref([]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);

// 角色选项
const roleOptions = [
  { text: '通用助手', value: 'default' },
  { text: '新闻助手', value: 'news' },
  { text: '情感顾问', value: 'emotional' },
  { text: '科技专家', value: 'tech' },
];
const currentRole = ref('default');

const formatMessage = (content) => {
  if (!content) return '';
  return DOMPurify.sanitize(marked.parse(content));
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 加载历史
const loadHistory = async () => {
  if (!userStore.getLoginStatus) return;
  try {
    const response = await axios.get('http://127.0.0.1:8000/api/ai/history', {
      headers: { Authorization: userStore.token }
    });
    if (response.data.code === 200) {
      const history = response.data.data || [];
      if (history.length > 0) {
        messages.value = history;
        await nextTick();
        scrollToBottom();
      }
    }
  } catch (error) {
    console.error('加载历史失败', error);
  }
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;
  if (!userStore.getLoginStatus) {
    showToast('请先登录');
    return;
  }

  const content = userInput.value.trim();
  // 添加用户消息
  messages.value.push({ role: 'user', content });
  userInput.value = '';
  // 添加 AI 占位
  messages.value.push({ role: 'assistant', content: '' });
  const lastIndex = messages.value.length - 1;
  await nextTick();
  scrollToBottom();

  isLoading.value = true;
  try {
    const response = await fetch(aiChatConfig.apiEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': userStore.token
      },
      body: JSON.stringify({
        content: content,
        role: currentRole.value
      })
    });

    if (!response.ok) throw new Error('请求失败');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') continue;
          try {
            const json = JSON.parse(data);
            if (json.error) {
              showToast(json.error);
              break;
            }
            if (json.content) {
              fullContent += json.content;
              messages.value[lastIndex].content = fullContent;
              await nextTick();
              scrollToBottom();
            }
          } catch (e) {}
        }
      }
    }
  } catch (error) {
    console.error('AI 请求失败', error);
    messages.value[lastIndex].content = '抱歉，请求失败，请稍后重试。';
    showToast('请求失败');
  } finally {
    isLoading.value = false;
    await nextTick();
    scrollToBottom();
  }
};

// 清空上下文（可加一个按钮）
const resetContext = async () => {
  if (!userStore.getLoginStatus) return;
  try {
    await axios.delete('http://127.0.0.1:8000/api/ai/context', {
      headers: { Authorization: userStore.token }
    });
    messages.value = [];
    showToast('会话已重置');
  } catch (error) {
    showToast('重置失败');
  }
};

onMounted(() => {
  loadHistory();
});
</script>

<style scoped>
/* ... 原有样式，增加角色选择器样式 */
.role-selector {
  position: fixed;
  top: 46px;
  right: 10px;
  z-index: 10;
  background: white;
  border-radius: 4px;
  padding: 2px 8px;
}
/* 其他原有样式不变 */
</style>