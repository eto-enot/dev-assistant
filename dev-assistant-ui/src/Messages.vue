<script setup lang="ts">
import { onMounted, useTemplateRef, watch } from 'vue';
import type { Message } from './chat';

const emit = defineEmits(['tool-confirm'])
const props = defineProps<{ messages: Message[] }>();
const messagesContainerRef = useTemplateRef('messagesContainer');
const reasoningRef = useTemplateRef('reasoning');

function scrollTop() {
    if (messagesContainerRef.value)
        messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight;
}

defineExpose({ scrollTop });

onMounted(() => {
    setInterval(() => {
        reasoningRef.value?.forEach(x => {
            x.scrollLeft = x.scrollWidth;
            x.scrollTop = x.scrollHeight;
        });
    }, 100);
});

function onConfirm(message: Message, isAllowed: boolean) {
    message.confirm(isAllowed);
    emit('tool-confirm', isAllowed);
}
</script>

<template>
    <div class="messages" ref="messagesContainer">
        <div class="message" v-for="msg of messages" :key="msg.id" :class="msg.role">
            <div class="avatar">
                <i :class="msg.avatarIcon"></i>
            </div>
            <div class="message-content">
                <div class="reasoning-block" v-if="msg.role !== 'user' && msg.reasoning.startsWith('Thought:')">
                    <span class="reasoning-toggle">
                        <a href="javascript:void(0)" class="reasoning-btn"
                            @click="() => msg.isReasoningCollapsed = !msg.isReasoningCollapsed">Reasoning</a>
                    </span>
                    <div class="reasoning-collapsed" v-if="msg.isReasoningCollapsed" ref="reasoning">{{ msg.reasoning }}
                    </div>
                    <div v-html="msg.reasoningHtml" v-else></div>
                </div>
                <div class="markdown-content">
                    <div class="typing-indicator" v-if="msg.isThinking">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                    <div v-else v-html="msg.contentHtml" :class="{ 'error-message': msg.isError }"></div>
                </div>
                <div class="tool-confirm-content" v-if="msg.toolConfirmRequested">
                    <div class="tool-confirm-message" v-html="msg.toolConfirmMessage"></div>
                    <div class="tool-confirm-buttons">
                        <button class="btn btn-tool-confirm-yes" @click="onConfirm(msg, true)">Yes</button>
                        <button class="btn btn-tool-confirm-no" @click="onConfirm(msg, false)">No</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.reasoning-block {
    font-size: x-small;
    margin-bottom: 0.5rem;
    border: solid 1px lightgray;
    border-radius: 4px;
    padding: 4px;
}

.reasoning-toggle {
    float: right;
    padding: 0 4px;
}

.reasoning-collapsed {
    height: 16px;
    line-height: 16px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: clip;
}

.reasoning-btn {
    color: aquamarine;
}

.tool-confirm-content {
    display: flex;
    border: solid 1px lightgray;
    border-radius: 4px;
    padding: 0 4px;
}

.tool-confirm-message {
    flex-grow: 1;
    white-space: pre-wrap;
    padding: 6px 2px;
}

.btn-tool-confirm-yes {
    padding: 2px 4px;
}

.btn-tool-confirm-no {
    padding: 2px 4px;
    background-color: darkred;
}

.tool-confirm-buttons {
    display: flex;
    gap: 4px;
    align-self: center;
}
</style>
