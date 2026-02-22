<script setup lang="ts">
import { onMounted, useTemplateRef, watch } from 'vue';
import type { Message } from './chat';

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
</script>

<template>
    <div class="messages" ref="messagesContainer">
        <div class="message" v-for="msg of messages" :key="msg.id" :class="msg.role">
            <div class="avatar">
                <i :class="msg.avatarIcon"></i>
            </div>
            <div class="message-content">
                <div class="reasoning-block" v-if="msg.role !== 'user' && msg.reasoning">
                    <span class="reasoning-toggle">
                        <a href="javascript:void(0)" class="reasoning-btn"
                            @click="() => msg.isReasoningCollapsed = !msg.isReasoningCollapsed">Reasoning</a>
                    </span>
                    <div v-text="msg.reasoning" class="reasoning-collapsed" v-if="msg.isReasoningCollapsed"
                        ref="reasoning"></div>
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
</style>
