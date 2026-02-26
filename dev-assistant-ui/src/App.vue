<script setup lang="ts">
import { onMounted, ref, useTemplateRef } from 'vue';
import { generateId, processStreamResponse, getDefaultSettings, getOS } from './utils';
import type { ConfirmToolCallRequest, Conversations, Role, SetProjectInfoRequest, Settings } from './types';
// import hljs from 'highlight.js';
import Prompt from './Prompt.vue';
import Messages from './Messages.vue';
import SettingsDialog from './Settings.vue';
import { Message } from './chat';
import { ErrorMessageUpdateEvent, type MessageUpdateEvent } from './events';

interface HistoryListItem {
    id: string;
    active: boolean;
    title: string;
}

const settings = ref(<Settings>JSON.parse(sessionStorage.getItem('settings') ?? 'null') || getDefaultSettings());
const historyList = ref<HistoryListItem[]>([]);
const messages = ref<Message[]>([]);
const sendDisabled = ref(false);

const messagesContainerRef = useTemplateRef('messagesContainer');
const settingsDialogRef = useTemplateRef('settingsDialog');

let isStreaming = false;

let currentConversationId = generateId();
const conversations: Conversations = JSON.parse(sessionStorage.getItem('conversations') ?? 'null') || {};

onMounted(async function () {
    // Initialize the app
    loadConversations();
    await setActiveConversation(currentConversationId);

    // Load default conversation if it exists
    if (conversations[currentConversationId]) {
        displayConversation(currentConversationId);
    } else {
        initializeCopyButtons();
    }

    // Initialize highlight.js
    //hljs.highlightAll();
});

// Load conversations from localStorage
function loadConversations() {
    historyList.value.splice(0, historyList.value.length);

    // Sort conversations by timestamp (newest first)
    const sortedConversations = Object.entries(conversations)
        .sort((a, b) => b[1].timestamp - a[1].timestamp);

    sortedConversations.forEach(([id, conv]) => {
        // Use first user message as title, or default
        const firstUserMessage = conv.messages.find(m => m.role === 'user');
        const title = firstUserMessage
            ? (firstUserMessage.content.length > 30
                ? firstUserMessage.content.substring(0, 30) + '...'
                : firstUserMessage.content)
            : 'New Conversation';

        historyList.value.push({ id, title, active: false });
    });
}

async function setProjectInfo(sessionId: string) {
    if (!sessionId)
        return;

    try {
        const response = await fetch(settings.value.apiUrl + '/set-project-info', {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(<SetProjectInfoRequest>{
                session_id: sessionId,
                work_directory: settings.value.currentDirectory,
                core_info: settings.value.coreInfo,
                os: getOS(),
            }),
        });

        if (!response.ok)
            throw new Error(`Error: ${response.status} ${response.statusText}`);
    } catch (e) {
        console.error(e);
    }
}

// Set active conversation
async function setActiveConversation(id: string) {
    // Update active state in history list
    historyList.value.forEach(item => {
        item.active = item.id === id;
    });

    currentConversationId = id;
    displayConversation(id);
    await setProjectInfo(id);
}

// Display a conversation
function displayConversation(id: string) {
    const conversation = conversations[id];

    if (!conversation) {
        initializeCopyButtons();
        return;
    }

    messages.value.splice(0, messages.value.length);

    conversation.messages.forEach(message => {
        addMessageToUI(message.role, message.content, false);
    });

    // Reinitialize syntax highlighting and copy buttons
    setTimeout(() => {
        //hljs.highlightAll();
        initializeCopyButtons();
    }, 100);

    // Scroll to bottom
    if (messagesContainerRef.value)
        messagesContainerRef.value.scrollTop();
}

// Start a new chat
async function startNewChat() {
    currentConversationId = generateId();
    conversations[currentConversationId] = {
        id: currentConversationId,
        timestamp: Date.now(),
        messages: []
    };
    historyList.value.unshift({ id: currentConversationId, title: 'New Conversation', active: true });
    await setActiveConversation(currentConversationId);
    initializeCopyButtons();
}

// Get conversation history for API request
function getConversationHistory() {
    const conversation = conversations[currentConversationId];
    if (!conversation) {
        return [];
    }

    // Return only the messages (without metadata)
    return conversation.messages.map(msg => ({
        role: msg.role,
        content: msg.content
    }));
}

// Save message to conversation history
function saveMessageToConversation(role: Role, content: string) {
    let conversation = conversations[currentConversationId];
    if (!conversation) {
        conversation = conversations[currentConversationId] = {
            id: currentConversationId,
            timestamp: Date.now(),
            messages: []
        };
    }

    conversation.messages.push({
        role,
        content,
        timestamp: Date.now()
    });

    conversation.timestamp = Date.now();

    // Update localStorage
    sessionStorage.setItem('conversations', JSON.stringify(conversations));

    // Update history list
    loadConversations();
}

// Update message content with markdown support
function updateMessageContent(messageId: string, event: MessageUpdateEvent) {
    const message = messages.value.find(x => x.id === messageId);
    if (message) {
        // Replace typing indicator with markdown content
        message.update(event);

        // Apply syntax highlighting to code blocks
        setTimeout(() => {
            //hljs.highlightAll();
            initializeCopyButtons();
        }, 0);

        // Scroll to bottom
        if (messagesContainerRef.value)
            messagesContainerRef.value.scrollTop();
    }
}

// Initialize copy buttons for code blocks
function initializeCopyButtons() {
    document.querySelectorAll('.copy-code-btn').forEach(button => {
        button.addEventListener('click', function (e) {
            copyCodeToClipboard(e.target as HTMLButtonElement);
        });
    });
}

// Copy code to clipboard
function copyCodeToClipboard(button: HTMLButtonElement) {
    const codeBlock = button.parentElement!.querySelector('code');
    const textToCopy = codeBlock!.textContent;

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

// Add message to UI
function addMessageToUI(role: Role, content: string, scroll = true) {
    const messageId = generateId();

    const message = new Message(messageId, role, content);
    messages.value.push(message);

    if (scroll && messagesContainerRef.value) {
        messagesContainerRef.value.scrollTop();
    }

    return messageId;
}

// Send a message
async function sendMessage(message: string) {
    if (!message || isStreaming) return;

    // Add user message to UI
    addMessageToUI('user', message);
    saveMessageToConversation('user', message);

    // Disable send button while streaming
    isStreaming = true;
    sendDisabled.value = true;

    // Add assistant placeholder message
    const messageId = addMessageToUI('assistant', '');

    // Prepare the request
    const requestBody = {
        user: currentConversationId,
        model: settings.value.model,
        messages: getConversationHistory(),
        stream: true,
    };

    try {
        const response = await fetch(settings.value.apiUrl + '/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        // Process streaming response
        await processStreamResponse(response, messageId, updateMessageContent);

        // Save assistant message to conversation history
        const assistantMessage = messages.value.find(x => x.id === messageId)?.content ?? '';
        saveMessageToConversation('assistant', assistantMessage);

    } catch (error: any) {
        console.error('Error:', error);
        updateMessageContent(messageId, new ErrorMessageUpdateEvent(`Error: ${error.message}. Please check your endpoint URL and network connection.`));
    } finally {
        isStreaming = false;
        sendDisabled.value = false;

        // Reinitialize syntax highlighting and copy buttons
        setTimeout(() => {
            //hljs.highlightAll();
            initializeCopyButtons();
        }, 100);
    }
}

function removeConversation(item: HistoryListItem) {
    const idx = historyList.value.findIndex(x => x.id === item.id);
    if (idx >= 0) {
        historyList.value.splice(idx, 1);
        delete conversations[item.id];
        sessionStorage.setItem('conversations', JSON.stringify(conversations));
        loadConversations();
        if (item.active) {
            messages.value.splice(0, messages.value.length);
        }
    }
}

async function showSettings() {
    try {
        await settingsDialogRef.value?.showModal();
        sessionStorage.setItem('settings', JSON.stringify(settings.value));
        await setProjectInfo(currentConversationId);
    } catch (err: any) {
        if (err)
            console.error(err);
    }
}

function onToolConfirm(isAllowed: boolean) {
    const request: ConfirmToolCallRequest = {
        session_id: currentConversationId,
        call_allowed: isAllowed
    };

    fetch(settings.value.apiUrl + '/confirm-tool-call', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });
}
</script>

<template>
    <header>
        <div class="logo">
            <h1>Developer Assistant</h1>
        </div>
        <div class="api-config">
            <button class="btn" @click="showSettings">Settings</button>
        </div>
    </header>

    <div class="container">
        <div class="sidebar">
            <button class="new-chat-btn" @click="startNewChat">
                <i class="fas fa-plus"></i>
                New chat
            </button>
            <!-- <div class="history-title">Today</div> -->
            <ul class="history-list" v-if="!historyList.length">
                <li class="history-item">No conversations yet</li>
            </ul>
            <ul class="history-list" v-else>
                <li class="history-item" v-for="item of historyList" :key="item.id"
                    @click="() => setActiveConversation(item.id)" :class="{ active: item.active }">
                    <span style="overflow: hidden; flex-grow: 1">{{ item.title }}</span>
                    <span @click="() => removeConversation(item)">
                        <i class="fas fa-xmark" />
                    </span>
                </li>
            </ul>
        </div>

        <div class="chat-container">
            <Messages :messages="messages" ref="messagesContainer" @tool-confirm="onToolConfirm"></Messages>
            <Prompt @send-message="sendMessage" :send-disabled="sendDisabled"></Prompt>
        </div>
    </div>

    <SettingsDialog v-model="settings" ref="settingsDialog"></SettingsDialog>
</template>

<style scoped></style>
