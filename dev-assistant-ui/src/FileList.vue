<script setup lang="ts">
import { computed, inject, onMounted, reactive, ref, watch, type Ref } from 'vue';
import type { ListFilesRequest, ListFilesResponse, ListFilesResponseItem, Settings } from './types';

const emit = defineEmits(['file-selected'])
const model = defineModel<string>();
const files = reactive([] as ListFilesResponseItem[]);
const loading = ref(true);

const settings = inject<Ref<Settings>>('Settings')!;
const curDirectory = computed(() => settings?.value.currentDirectory?.trim() ?? '.');
let curPath = '.';

onMounted(async () => {
    await updateFiles();
    watch(model, updateFiles);
});

async function updateFiles() {
    try {
        loading.value = true;
        let filter = (model.value ?? '').trim();
        if (filter.startsWith('@'))
            filter = filter.substring(1);

        const response = await fetch(settings.value.apiUrl + '/list-files', {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(<ListFilesRequest>{
                filter: filter,
                work_directory: curDirectory.value,
                path: curPath,
            }),
        });

        if (!response.ok)
            throw new Error(`Error: ${response.status} ${response.statusText}`);

        const data: ListFilesResponse = await response.json();
        files.splice(0, files.length);
        files.push(...data.content);

        loading.value = false;
    } catch (e) {
        console.error(e);
    }
}

async function onClick(file: ListFilesResponseItem) {
    if (file.name.endsWith('/')) {
        if (!curPath.endsWith('/'))
            curPath += '/';
        curPath += file.name;
        await updateFiles();
    } else {
        emit('file-selected', file.path);
    }
}
</script>

<template>
    <div class="file-list">
        <div class="file-list-content">
            <div class="typing-indicator" v-if="loading">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <datalist style="display: block;" v-for="item in files" :key="item.name" v-else>
                <option :value="item.path" @click="() => onClick(item)">{{ item.name }}</option>
            </datalist>
        </div>
    </div>
</template>

<style lang="css" scoped>
.file-list {
    position: absolute;
    bottom: 8rem;
    width: 100%;
}

.file-list-content {
    position: relative;
    max-width: 768px;
    margin-left: -408px;
    left: 50%;
    padding: .25rem;
    border: 2px solid whitesmoke;
    max-height: 16rem;
    overflow: auto;
    background-color: #343541;
}

datalist>option {
    cursor: pointer;
}

datalist>option:hover {
    background-color: whitesmoke;
    color: black;
}
</style>
