<script setup lang="ts">
import { ref, useTemplateRef, watch } from 'vue';

const emit = defineEmits(['send-message']);
const props = defineProps<{ sendDisabled: boolean }>();

const message = ref('');
const messageHeight = ref('auto');
const messageInputRef = useTemplateRef('messageInput');

function sendMessage() {
    emit('send-message', message.value);

    // Clear input
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
    </div>
</template>

<style scoped>
textarea {
    overflow-y: clip;
}
</style>
