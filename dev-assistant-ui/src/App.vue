<script setup lang="js">
import { onMounted } from 'vue';
import hljs from 'highlight.js';

onMounted(function () {
  // DOM Elements
  const messagesContainer = document.getElementById('messages');
  const messageInput = document.getElementById('message-input');
  const sendButton = document.getElementById('send-button');
  //const newChatButton = document.getElementById('new-chat');
  const historyList = document.getElementById('history-list');
  const apiKeyInput = document.getElementById('api-key');
  const apiEndpointInput = document.getElementById('api-endpoint');
  const modelSelect = document.getElementById('model-select');
  const modelTag = document.getElementById('model-tag');

  // State management
  let currentConversationId = generateId();
  let conversations = JSON.parse(sessionStorage.getItem('conversations')) || {};
  let isStreaming = false;

  // Initialize the app
  function init() {
    //loadConversations();
    setActiveConversation(currentConversationId);

    // Set up event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    //newChatButton.addEventListener('click', startNewChat);

    messageInput.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = (this.scrollHeight) + 'px';
    });

    modelSelect.addEventListener('change', function () {
      modelTag.textContent = this.value;
      if (this.value === 'custom') {
        apiEndpointInput.style.display = 'inline-block';
      } else {
        apiEndpointInput.style.display = 'inline-block';
      }
    });

    // Load default conversation if it exists
    if (conversations[currentConversationId]) {
      displayConversation(currentConversationId);
    } else {
      // Display welcome message
      displayWelcomeMessage();
    }

    // Initialize highlight.js
    hljs.highlightAll();
  }

  // Generate a unique ID for conversations
  function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  // Display welcome message
  function displayWelcomeMessage() {
    const welcomeMessage = `
                <div class="message assistant">
                    <div class="avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="markdown-content">
                            <h2>Welcome to OpenAI API Chat with Markdown!</h2>
                            <p>I'm an AI assistant powered by the OpenAI API. I can display formatted content including:</p>
                            <ul>
                                <li><strong>Code blocks</strong> with syntax highlighting</li>
                                <li><strong>Headers</strong> (like this one!)</li>
                                <li><strong>Lists</strong> (both ordered and unordered)</li>
                                <li><strong>Tables</strong> with proper formatting</li>
                                <li><strong>Bold and italic</strong> text</li>
                                <li><strong>Quotes</strong> and blockquotes</li>
                                <li><strong>Links</strong> that you can click</li>
                            </ul>
                            <p>Try asking me to:</p>
                        <div class="message-controls">
                                <button class="control-btn" onclick="suggestPrompt('Write a Python function to calculate factorial with a docstring')">
                                    <i class="fas fa-code"></i> Python example
                            </button>
                                <button class="control-btn" onclick="suggestPrompt('Create a comparison table of programming languages')">
                                    <i class="fas fa-table"></i> Create a table
                            </button>
                                <button class="control-btn" onclick="suggestPrompt('Explain the concept of recursion with examples')">
                                    <i class="fas fa-sitemap"></i> Explain recursion
                            </button>
                        </div>
                            <p>To get started, enter your API key in the header above.</p>
                        </div>
                    </div>
                </div>
            `;

    //messagesContainer.innerHTML = welcomeMessage;
    initializeCopyButtons();
  }

  // Suggest a prompt
  function suggestPrompt(prompt) {
    messageInput.value = prompt;
    messageInput.style.height = 'auto';
    messageInput.style.height = (messageInput.scrollHeight) + 'px';
    messageInput.focus();
  }

  // Load conversations from localStorage
  function loadConversations() {
    historyList.innerHTML = '';

    if (Object.keys(conversations).length === 0) {
      const emptyItem = document.createElement('li');
      emptyItem.className = 'history-item';
      emptyItem.textContent = 'No conversations yet';
      historyList.appendChild(emptyItem);
      return;
    }

    // Sort conversations by timestamp (newest first)
    const sortedConversations = Object.entries(conversations)
      .sort((a, b) => b[1].timestamp - a[1].timestamp);

    sortedConversations.forEach(([id, conv]) => {
      const historyItem = document.createElement('li');
      historyItem.className = 'history-item';
      historyItem.dataset.id = id;

      // Use first user message as title, or default
      const firstUserMessage = conv.messages.find(m => m.role === 'user');
      const title = firstUserMessage
        ? (firstUserMessage.content.length > 30
          ? firstUserMessage.content.substring(0, 30) + '...'
          : firstUserMessage.content)
        : 'New Conversation';

      historyItem.textContent = title;
      historyItem.addEventListener('click', () => setActiveConversation(id));

      historyList.appendChild(historyItem);
    });
  }

  // Set active conversation
  function setActiveConversation(id) {
    // Update active state in history list
    document.querySelectorAll('.history-item').forEach(item => {
      item.classList.remove('active');
      if (item.dataset.id === id) {
        item.classList.add('active');
      }
    });

    currentConversationId = id;
    displayConversation(id);
  }

  // Display a conversation
  function displayConversation(id) {
    const conversation = conversations[id];

    if (!conversation) {
      displayWelcomeMessage();
      return;
    }

    messagesContainer.innerHTML = '';

    conversation.messages.forEach(message => {
      addMessageToUI(message.role, message.content, false);
    });

    // Reinitialize syntax highlighting and copy buttons
    setTimeout(() => {
      hljs.highlightAll();
      initializeCopyButtons();
    }, 100);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Start a new chat
  function startNewChat() {
    currentConversationId = generateId();
    setActiveConversation(currentConversationId);
    displayWelcomeMessage();
  }

  // Send a message
  async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isStreaming) return;

    // Add user message to UI
    addMessageToUI('user', message);

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Disable send button while streaming
    isStreaming = true;
    sendButton.disabled = true;

    // Add assistant placeholder message
    const messageId = addMessageToUI('assistant', '');

    // Get API configuration
    const apiKey = '';// apiKeyInput.value.trim();
    const endpoint = apiEndpointInput.value.trim();
    const model = modelSelect.value;

    // Validate API key
    /*if (!apiKey) {
        showError('Please enter a valid API key');
        updateMessageContent(messageId, 'Error: Please enter a valid API key in the header.');
        isStreaming = false;
        sendButton.disabled = false;
        return;
    }*/

    // Save user message to conversation history
    saveMessageToConversation('user', message);

    // Prepare the request
    const requestBody = {
      model: model,
      messages: getConversationHistory(),
      stream: true
    };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      // Process streaming response
      await processStreamResponse(response, messageId);

      // Save assistant message to conversation history
      const assistantMessage = document.getElementById(`content-${messageId}`).innerText;
      saveMessageToConversation('assistant', assistantMessage);

    } catch (error) {
      console.error('Error:', error);
      updateMessageContent(messageId, `Error: ${error.message}. Please check your API key, endpoint, and network connection.`);
    } finally {
      isStreaming = false;
      sendButton.disabled = false;

      // Reinitialize syntax highlighting and copy buttons
      setTimeout(() => {
        hljs.highlightAll();
        initializeCopyButtons();
      }, 100);
    }
  }

  // Process streaming response
  async function processStreamResponse(response, messageId) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(line => line.trim() !== '');

      for (const line of lines) {
        // Skip non-data lines
        if (!line.startsWith('data: ')) continue;

        const data = line.substring(6);

        // Skip [DONE] message
        if (data === '[DONE]') {
          continue;
        }

        try {
          const parsed = JSON.parse(data);
          const content = parsed.choices[0]?.delta?.content || '';

          if (content) {
            accumulatedText += content;
            updateMessageContent(messageId, accumulatedText);
          }
        } catch (e) {
          console.error('Error parsing stream data:', e);
        }
      }
    }
  }

  // Get conversation history for API request
  function getConversationHistory() {
    if (!conversations[currentConversationId]) {
      return [];
    }

    // Return only the messages (without metadata)
    return conversations[currentConversationId].messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));
  }

  // Save message to conversation history
  function saveMessageToConversation(role, content) {
    if (!conversations[currentConversationId]) {
      conversations[currentConversationId] = {
        id: currentConversationId,
        timestamp: Date.now(),
        messages: []
      };
    }

    conversations[currentConversationId].messages.push({
      role,
      content,
      timestamp: Date.now()
    });

    conversations[currentConversationId].timestamp = Date.now();

    // Update localStorage
    sessionStorage.setItem('conversations', JSON.stringify(conversations));

    // Update history list
    //loadConversations();
  }

  // Add message to UI
  function addMessageToUI(role, content, scroll = true) {
    const messageId = generateId();

    const messageElement = document.createElement('div');
    messageElement.className = `message ${role}`;
    messageElement.id = `msg-${messageId}`;

    const avatarIcon = role === 'user' ? 'fas fa-user' : 'fas fa-robot';

    messageElement.innerHTML = `
                <div class="avatar">
                    <i class="${avatarIcon}"></i>
                </div>
                <div class="message-content">
                    <div id="content-${messageId}" class="markdown-content">
                        ${role === 'assistant' && !content ? '<div class="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>' : ''}
                        ${content ? renderMarkdown(content) : (role === 'user' ? escapeHtml(content) : '')}
                    </div>
                </div>
            `;

    messagesContainer.appendChild(messageElement);

    if (scroll) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    return messageId;
  }

  // Update message content with markdown support
  function updateMessageContent(messageId, content) {
    const contentElement = document.getElementById(`content-${messageId}`);
    if (contentElement) {
      // Replace typing indicator with markdown content
      contentElement.innerHTML = renderMarkdown(content);

      // Apply syntax highlighting to code blocks
      setTimeout(() => {
        hljs.highlightAll();
        initializeCopyButtons();
      }, 0);

      // Scroll to bottom
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  // Render markdown to HTML
  function renderMarkdown(text) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');

    // Code blocks with language detection
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, function (match, lang, code) {
      const language = lang || 'plaintext';
      const escapedCode = escapeHtml(code.trim());
      return `<div class="code-block-wrapper"><button class="copy-code-btn" onclick="copyCodeToClipboard(this)">Copy</button><pre><code class="language-${language}">${escapedCode}</code></pre></div>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Blockquotes
    html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');

    // Lists (unordered)
    html = html.replace(/^\s*[-*+] (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/g, '<ul>$1</ul>');

    // Lists (ordered)
    html = html.replace(/^\s*\d+\. (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/g, '<ol>$1</ol>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // Horizontal rule
    html = html.replace(/^---$/gim, '<hr>');

    // Tables (simple support)
    html = html.replace(/\|(.+)\|/g, function (match, row) {
      const cells = row.split('|').map(cell => cell.trim());
      if (cells.some(cell => cell.includes('---'))) {
        return ''; // Skip separator rows for now
      }
      const cellTags = cells.map(cell => `<td>${cell}</td>`).join('');
      return `<tr>${cellTags}</tr>`;
    });

    // Wrap table rows in table tags
    const tableRows = html.match(/<tr>.*?<\/tr>/g);
    if (tableRows && tableRows.length > 0) {
      const tableHeader = '<table><thead><tr><th>Column 1</th><th>Column 2</th></tr></thead><tbody>';
      const tableFooter = '</tbody></table>';
      html = html.replace(/(<tr>.*?<\/tr>)/g, tableHeader + tableRows.join('') + tableFooter);
    }

    // Paragraphs (ensure proper wrapping)
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/<p><\/p>/g, '');

    // Handle line breaks
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph tags if not already wrapped
    if (!html.startsWith('<') || html.startsWith('<br>')) {
      html = '<p>' + html + '</p>';
    }

    return html;
  }

  // Escape HTML special characters
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize copy buttons for code blocks
  function initializeCopyButtons() {
    document.querySelectorAll('.copy-code-btn').forEach(button => {
      button.addEventListener('click', function () {
        copyCodeToClipboard(this);
      });
    });
  }

  // Copy code to clipboard
  function copyCodeToClipboard(button) {
    const codeBlock = button.parentElement.querySelector('code');
    const textToCopy = codeBlock.textContent;

    navigator.clipboard.writeText(textToCopy).then(() => {
      const originalText = button.textContent;
      button.textContent = 'Copied!';
      button.classList.add('copied');

      setTimeout(() => {
        button.textContent = originalText;
        button.classList.remove('copied');
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy: ', err);
      button.textContent = 'Failed!';
      setTimeout(() => {
        button.textContent = 'Copy';
      }, 2000);
    });
  }

  // Show error message
  function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
                <i class="fas fa-exclamation-circle"></i>
                <span>${message}</span>
            `;

    messagesContainer.appendChild(errorDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Remove error after 5 seconds
    setTimeout(() => {
      errorDiv.remove();
    }, 5000);

  }

  // Initialize the app when DOM is loaded
  document.addEventListener('DOMContentLoaded', init);
});
</script>

<template>
  <header>
    <div class="logo">
      <h1>Developer Assistant</h1>
    </div>
    <div class="api-config">
      <select id="model-select">
        <option value="Coder LLM">Coder LLM</option>
      </select>
      <!-- <input type="text" id="api-key" placeholder="API Key" value="sk-..."> -->
      <input type="text" id="api-endpoint" placeholder="API Endpoint" value="http://localhost:8000/v1/chat/completions">
    </div>
  </header>

  <div class="container">
    <!--<div class="sidebar">
            <button class="new-chat-btn" id="new-chat">
                <i class="fas fa-plus"></i>
                New chat
            </button>
            <div class="history-title">Today</div>
            <ul class="history-list" id="history-list">
            </ul>
        </div>-->

    <div class="chat-container">
      <div class="messages" id="messages">
        <!-- Messages will be added here -->
      </div>

      <div class="input-container">
        <div class="input-area">
          <textarea id="message-input" placeholder="Ask something..." rows="1"></textarea>
          <button class="send-button" id="send-button">
            <i class="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
