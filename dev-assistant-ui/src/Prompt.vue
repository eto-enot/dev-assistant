<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue';
import FileList from './FileList.vue';
import { refDebounced } from './debounce';

const emit = defineEmits(['send-message']);
const props = defineProps<{ sendDisabled: boolean }>();

const message = ref('');
const messageHeight = ref('auto');
const debouncedMessage = refDebounced(message, 400);
const context = computed(() => {
    const match= /(?:\s|^)@[^\s]*$/.exec(debouncedMessage.value);
    return match ? match[0] : '';
});
const messageInputRef = useTemplateRef('messageInput');

function sendMessage() {
    emit('send-message', message.value.trim());
    message.value = '';
}

// Send message on enter
function onMessageKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

watch(message, function (newValue) {
    // prompt field auto sizing
    messageHeight.value = newValue
        ? messageInputRef.value?.scrollHeight + 'px'
        : 'auto';
});

function onFileSelected(file: string) {
    const idx = message.value.lastIndexOf('@');
    if (idx >= 0) {
        message.value = message.value.substring(0, idx+1) + file + ' ';
        messageInputRef.value?.focus();
    }
}
</script>

<template>
    <div class="input-container">
        <div class="input-area">
            <textarea placeholder="Ask something..." rows="1" :style="{ height: messageHeight }" v-model="message"
                @keydown="onMessageKeydown" ref="messageInput"></textarea>
            <button class="send-button" @click="sendMessage" :disabled="props.sendDisabled">
                <i class="fas fa-paper-plane"></i>
            </button>
        </div>
        <FileList v-if="!!context" v-model="context" @file-selected="onFileSelected"></FileList>
    </div>
</template>

<style scoped>
textarea {
    overflow-y: clip;
}
</style>
