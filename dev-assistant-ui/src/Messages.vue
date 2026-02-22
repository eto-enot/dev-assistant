<script setup lang="ts">
import { useTemplateRef } from 'vue';
import type { Message } from './utils';

const props = defineProps<{ messages: Message[] }>();
const messagesContainerRef = useTemplateRef('messagesContainer');

function scrollTop() {
    if (messagesContainerRef.value)
        messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight;
}

defineExpose({ scrollTop });
</script>

<template>
    <div class="messages" ref="messagesContainer">
        <div class="message" v-for="msg of messages" :key="msg.id" :class="msg.role">
            <div class="avatar">
                <i :class="msg.avatarIcon"></i>
            </div>
            <div class="message-content">
                <div class="markdown-content">
                    <div class="typing-indicator" v-if="msg.isThinking">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                    <div v-else v-html="msg.contentHtml" :class="{" error-message": msg.isError }"></div>
                </div>
            </div>
        </div>
    </div>
</template>
