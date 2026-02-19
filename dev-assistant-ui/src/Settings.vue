<script setup lang="ts">
import { useTemplateRef } from 'vue';
import { type Settings } from './types';

let resolve: (value: Settings) => void, reject: (reason?: unknown) => void;
let promise: Promise<Settings>;

const models = ['Coder LLM'];
const settings = defineModel<Settings>({ default: {} });
const dialogRef = useTemplateRef('dialog');

function showModal() {
    dialogRef.value?.showModal();
    promise = new Promise<Settings>((res, rej) => {
        [resolve, reject] = [res, rej];
    });
    return promise;
}

defineExpose({ showModal });

function onClose() {
    dialogRef.value?.close();
    reject();
}

function onOk() {
    dialogRef.value?.close();
    resolve(settings.value);
}
</script>

<template>
    <dialog ref="dialog">
        <div class="logo">
            <h2 style="flex-grow: 1;">Settings</h2>
            <span class="fas fa-xmark close" @click="onClose"></span>
        </div>
        <div class="dialog-main">
            <div class="row">
                <div class="caption">Model:</div>
                <div class="value">
                    <select v-model="settings.model">
                        <option v-for="model in models" :value="model" :key="model">{{ model }}</option>
                    </select>
                </div>
            </div>

            <div class="row">
                <div class="caption">API Endpoint:</div>
                <div class="value">
                    <input type="text" placeholder="API Endpoint" v-model="settings.apiUrl">
                </div>
            </div>

            <div class="row">
                <div class="caption">Working Directory:</div>
                <div class="value">
                    <input type="text" placeholder="Working Directory" v-model="settings.currentDirectory">
                </div>
            </div>
        </div>
        <div class="dialog-footer">
            <button class="btn btn-cancel" @click="onClose">Cancel</button>
            <button class="btn" @click="onOk">OK</button>
        </div>
    </dialog>
</template>

<style scoped>
dialog {
    margin: 100px auto;
    width: 600px;
    background-color: #202123;
    color: #ececf1;
    padding: 0.5rem;
}

.logo {
    align-items: center;
}

.close {
    cursor: pointer;
}

.dialog-footer {
    display: flex;
    flex-direction: row-reverse;
    gap: 5px
}

.btn-cancel {
    background-color: transparent;
}

.dialog-main {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 20px 0;
}

.row {
    display: flex;
    align-items: baseline;
    gap: 10px;
}

.caption {
    width: 40%;
}

.value {
    flex-grow: 1;
}

.value>input,
.value>select {
    width: 100%;
}
</style>
