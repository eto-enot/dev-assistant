<script setup lang="ts">
import { generateId } from './utils';
import type { HistoryListItem } from './types';

const emit = defineEmits(['new-chat', 'item-selected', 'item-removed']);
const historyList = defineModel<HistoryListItem[]>({default: []});

// Start a new chat
async function startNewChat() {
    const id = generateId();
    historyList.value.unshift({ id, title: 'New Conversation', active: true });
    emit('new-chat', id);
}

// Set active conversation
async function setActiveConversation(id: string) {
    // Update active state in history list
    historyList.value.forEach(item => {
        item.active = item.id === id;
    });

    emit('item-selected', id);
}

function removeConversation(item: HistoryListItem) {
    const idx = historyList.value.findIndex(x => x.id === item.id);
    if (idx >= 0) {
        historyList.value.splice(idx, 1);
        emit('item-removed', item);
    }
}
</script>

<template>
    <button class="new-chat-btn" @click="startNewChat">
        <i class="fas fa-plus"></i>
        New chat
    </button>
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
</template>
